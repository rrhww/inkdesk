from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


F01_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts" / "f01"
sys.path.insert(0, str(F01_SCRIPTS))

from export_openapi import (  # noqa: E402
    OpenAPIContractMismatch,
    canonicalize_openapi,
    compare_openapi,
    ensure_sanitized_contract,
    write_openapi_snapshot,
)
from export_postgres_schema import (  # noqa: E402
    _postgres_string_list,
    canonicalize_schema,
    normalize_representative_records,
)
from export_representative_records import capture_representative_records  # noqa: E402
from baseline_contracts import canonical_json  # noqa: E402


def _current_openapi() -> dict:
    from inkdesk_server.main import create_app

    with TestClient(create_app()) as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    return response.json()


def test_openapi_export_is_stable_for_the_isolated_app(temp_app_env: Path, tmp_path: Path) -> None:
    snapshot = tmp_path / "openapi.json"
    openapi = _current_openapi()

    write_openapi_snapshot(openapi, snapshot)

    compare_openapi(canonicalize_openapi(openapi), snapshot)
    assert snapshot.read_bytes().endswith(b"\n")


def test_openapi_comparison_detects_removed_response_status(temp_app_env: Path, tmp_path: Path) -> None:
    snapshot = tmp_path / "openapi.json"
    openapi = canonicalize_openapi(_current_openapi())
    write_openapi_snapshot(openapi, snapshot)
    mutated = copy.deepcopy(openapi)
    operation = next(
        definition
        for path in mutated["paths"].values()
        for method, definition in path.items()
        if method in {"get", "post", "put", "patch", "delete"} and definition.get("responses")
    )
    operation["responses"].pop(next(iter(operation["responses"])))

    with pytest.raises(OpenAPIContractMismatch, match="OpenAPI contract differs"):
        compare_openapi(mutated, snapshot)


@pytest.mark.parametrize(
    "forbidden_value",
    ["Bearer secret-token", "session_cookie=secret", "C:/Users/example/private", "https://localhost:8080/private"],
)
def test_openapi_contract_rejects_sensitive_or_machine_specific_values(forbidden_value: str) -> None:
    with pytest.raises(ValueError, match="unsafe"):
        ensure_sanitized_contract({"example": forbidden_value})


def _schema_catalog() -> dict:
    return {
        "postgres": {"version": "16.4", "extensions": [{"name": "vector", "version": "0.8.0"}]},
        "tables": [
            {
                "name": "topics",
                "columns": [
                    {"name": "title", "type": "character varying", "nullable": False, "default": None},
                    {"name": "workspace_id", "type": "character varying", "nullable": False, "default": None},
                    {"name": "id", "type": "character varying", "nullable": False, "default": None},
                ],
                "primaryKey": {"name": "topics_pkey", "columns": ["id"]},
                "unique": [{"name": "topics_workspace_title_key", "columns": ["workspace_id", "title"]}],
                "foreignKeys": [
                    {
                        "name": "topics_workspace_id_fkey",
                        "columns": ["workspace_id"],
                        "referencedTable": "workspaces",
                        "referencedColumns": ["id"],
                        "onDelete": "CASCADE",
                    }
                ],
                "indexes": [
                    {
                        "name": "topics_embedding_idx",
                        "elements": ["embedding vector_cosine_ops"],
                        "method": "ivfflat",
                        "unique": False,
                    }
                ],
            },
            {
                "name": "workspaces",
                "columns": [{"name": "id", "type": "character varying", "nullable": False, "default": None}],
                "primaryKey": {"name": "workspaces_pkey", "columns": ["id"]},
                "unique": [],
                "foreignKeys": [],
                "indexes": [],
            },
        ],
    }


def test_schema_canonicalizer_is_stable_across_catalog_ordering() -> None:
    catalog = _schema_catalog()
    shuffled = copy.deepcopy(catalog)
    shuffled["tables"].reverse()
    shuffled["tables"][1]["columns"].reverse()
    shuffled["postgres"]["extensions"].reverse()

    assert canonicalize_schema(catalog) == canonicalize_schema(shuffled)


def test_schema_compatibility_digest_changes_for_type_or_on_delete_change() -> None:
    baseline = canonicalize_schema(_schema_catalog())
    type_changed = _schema_catalog()
    type_changed["tables"][0]["columns"][0]["type"] = "text"
    delete_changed = _schema_catalog()
    delete_changed["tables"][0]["foreignKeys"][0]["onDelete"] = "RESTRICT"

    assert baseline["compatibilityDigest"] != canonicalize_schema(type_changed)["compatibilityDigest"]
    assert baseline["compatibilityDigest"] != canonicalize_schema(delete_changed)["compatibilityDigest"]


def test_schema_physical_names_only_change_diagnostic_digest() -> None:
    baseline = canonicalize_schema(_schema_catalog())
    renamed = _schema_catalog()
    renamed["tables"][0]["primaryKey"]["name"] = "topics_pk_v2"
    renamed["tables"][0]["unique"][0]["name"] = "topics_unique_v2"
    renamed["tables"][0]["foreignKeys"][0]["name"] = "topics_fk_v2"
    renamed["tables"][0]["indexes"][0]["name"] = "topics_vector_v2"
    renamed_schema = canonicalize_schema(renamed)

    assert baseline["compatibilityDigest"] == renamed_schema["compatibilityDigest"]
    assert baseline["diagnosticDigest"] != renamed_schema["diagnosticDigest"]


@pytest.mark.parametrize("value", [["topic_id", "source_id"], '["topic_id", "source_id"]'])
def test_postgres_json_aggregate_preserves_column_names(value: object) -> None:
    assert _postgres_string_list(value) == ["topic_id", "source_id"]


def test_representative_records_replace_sensitive_values_but_keep_relationships() -> None:
    records = {
        "sources": [{
            "id": "2d7d13c4-2bc6-4d4e-9853-0df66c12b81f",
            "title": "Private source title",
            "createdAt": "2026-07-11T12:00:00Z",
            "vaultPath": "C:/Users/example/private/raw/source.md",
        }],
        "reviews": [{
            "id": "becf8d96-3730-4d2a-a4f4-69831e1b3d7d",
            "sourceId": "2d7d13c4-2bc6-4d4e-9853-0df66c12b81f",
            "summary": "Private free-text evidence.",
        }],
    }

    normalized = normalize_representative_records(records)

    source = normalized["sources"][0]
    review = normalized["reviews"][0]
    assert source["id"] == review["sourceId"]
    assert source["id"] != records["sources"][0]["id"]
    assert source["title"] == "<text>"
    assert review["summary"] == "<text>"
    assert source["createdAt"] == "<timestamp>"
    assert source["vaultPath"] == "<absolute-path>"


def test_representative_records_replace_relative_vault_paths() -> None:
    normalized = normalize_representative_records({"sources": [{"id": "source-1", "vaultPath": "raw/source-1.md"}]})

    assert normalized["sources"][0]["vaultPath"] == "<relative-path>"


def test_representative_record_capture_uses_synthetic_api_data_only() -> None:
    records = capture_representative_records()

    assert records["sources"]
    assert records["reviews"]
    assert records["topics"]
    assert records["run"]["status"] == "completed"
    assert records["compileQueue"]
    serialized = canonical_json(records)
    assert "Synthetic source body" not in serialized
    assert "F01 synthetic Dev Run" not in serialized
    assert "C:/" not in serialized
