"""Export PostgreSQL catalog structure and sanitize representative test records."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from baseline_contracts import canonical_json, canonical_sha256


class PostgresSchemaMismatch(AssertionError):
    """The live catalog is incompatible with the checked-in F01 schema snapshot."""


_IDENTIFIER_KEYS = {"id", "sourceid", "topicid", "reviewid", "askturnid", "runid", "workspaceid", "taskid", "claimid"}
_TEXT_KEYS = {
    "title",
    "summary",
    "understanding",
    "body",
    "excerpt",
    "question",
    "answer",
    "goal",
    "repocontext",
    "locator",
    "statement",
    "message",
    "vaultpath",
    "proposedvaultpath",
    "snippet",
    "sourcetitle",
    "targettopictitle",
    "citationlabel",
    "explanation",
    "openquestions",
    "summarychanges",
    "followupquestions",
    "knowledgegaps",
}
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}[T ][0-2]\d:[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)?$")


def canonicalize_schema(catalog: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a raw PostgreSQL catalog while separating semantic and diagnostic names."""

    if not isinstance(catalog, Mapping):
        raise ValueError("PostgreSQL catalog must be an object")
    postgres = catalog.get("postgres")
    tables = catalog.get("tables")
    if not isinstance(postgres, Mapping) or not isinstance(tables, list):
        raise ValueError("PostgreSQL catalog requires postgres and tables")

    canonical_postgres = {
        "majorVersion": _major_version(postgres.get("version")),
        "extensions": sorted(
            [{"name": _string(extension, "name")} for extension in postgres.get("extensions", [])],
            key=lambda extension: extension["name"],
        ),
    }
    canonical_tables = sorted((_canonicalize_table(table) for table in tables), key=lambda table: table["name"])
    diagnostic = {"postgres": canonical_postgres, "tables": canonical_tables}
    compatibility = {
        "postgres": canonical_postgres,
        "tables": [_compatibility_table(table) for table in canonical_tables],
    }
    result = copy.deepcopy(diagnostic)
    result["compatibilityDigest"] = canonical_sha256(compatibility)
    result["diagnosticDigest"] = canonical_sha256(diagnostic)
    return result


def normalize_representative_records(records: Any) -> Any:
    """Replace IDs, times, local paths, and unrestricted text while preserving references."""

    identifier_tokens: dict[str, str] = {}

    def normalize(value: Any, key: str | None = None) -> Any:
        normalized_key = _normalized_key(key)
        if isinstance(value, Mapping):
            return {str(child_key): normalize(child_value, str(child_key)) for child_key, child_value in value.items()}
        if isinstance(value, list):
            return [normalize(item, key) for item in value]
        if not isinstance(value, str):
            return value
        if value in identifier_tokens:
            return identifier_tokens[value]
        if normalized_key in _IDENTIFIER_KEYS or normalized_key.endswith("id") or normalized_key.endswith("ids"):
            token = f"<id:{len(identifier_tokens) + 1}>"
            identifier_tokens[value] = token
            return token
        if _TIMESTAMP.fullmatch(value):
            return "<timestamp>"
        if _is_absolute_path(value):
            return "<absolute-path>"
        if normalized_key.endswith("path"):
            return "<relative-path>"
        if normalized_key in _TEXT_KEYS or _is_free_text_key(normalized_key):
            return "<text>"
        return value

    return normalize(records)


def fetch_postgres_catalog(database_url: str) -> dict[str, Any]:
    """Read the public schema from PostgreSQL system catalogs, never ORM metadata."""

    if not database_url or not database_url.strip():
        raise ValueError("An explicit PostgreSQL database URL is required")
    try:
        import psycopg
    except ImportError as error:  # pragma: no cover - setup failure is reported to the operator.
        raise RuntimeError("psycopg is required to export PostgreSQL schema") from error

    connection_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(connection_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SHOW server_version")
            version = cursor.fetchone()[0]
            cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'")
            extensions = [{"name": name, "version": extension_version} for name, extension_version in cursor.fetchall()]
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
            table_names = [row[0] for row in cursor.fetchall()]
            tables = [_fetch_table(cursor, table_name) for table_name in table_names]
    return {"postgres": {"version": version, "extensions": extensions}, "tables": tables}


def write_schema_snapshot(catalog: Mapping[str, Any], snapshot: Path) -> None:
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(canonical_json(canonicalize_schema(catalog)) + "\n", encoding="utf-8", newline="\n")


def compare_schema(catalog: Mapping[str, Any], snapshot: Path) -> None:
    try:
        expected = json.loads(snapshot.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise PostgresSchemaMismatch(f"PostgreSQL schema snapshot does not exist: {snapshot}") from error
    actual = canonicalize_schema(catalog)
    if actual.get("compatibilityDigest") != expected.get("compatibilityDigest"):
        raise PostgresSchemaMismatch("PostgreSQL compatibility schema digest differs from the checked-in snapshot")


def _fetch_table(cursor: Any, table_name: str) -> dict[str, Any]:
    cursor.execute(
        """
        SELECT column_name, data_type, udt_name, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table_name,),
    )
    columns = [
        {
            "name": name,
            "type": udt_name if data_type == "USER-DEFINED" else data_type,
            "nullable": nullable == "YES",
            "default": default,
        }
        for name, data_type, udt_name, nullable, default in cursor.fetchall()
    ]
    cursor.execute(
        """
        SELECT tc.constraint_name, tc.constraint_type, array_to_json(array_agg(kcu.column_name ORDER BY kcu.ordinal_position))
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_catalog = kcu.constraint_catalog
         AND tc.constraint_schema = kcu.constraint_schema
         AND tc.constraint_name = kcu.constraint_name
        WHERE tc.table_schema = 'public'
          AND tc.table_name = %s
          AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
        GROUP BY tc.constraint_name, tc.constraint_type
        """,
        (table_name,),
    )
    primary_key: dict[str, Any] | None = None
    unique: list[dict[str, Any]] = []
    for name, constraint_type, columns_for_constraint in cursor.fetchall():
        item = {"name": name, "columns": _postgres_string_list(columns_for_constraint)}
        if constraint_type == "PRIMARY KEY":
            primary_key = item
        else:
            unique.append(item)
    cursor.execute(
        """
        SELECT tc.constraint_name,
               array_to_json(array_agg(kcu.column_name ORDER BY kcu.ordinal_position)),
               ccu.table_name,
               array_to_json(array_agg(ccu.column_name ORDER BY kcu.ordinal_position)),
               rc.delete_rule
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_catalog = kcu.constraint_catalog
         AND tc.constraint_schema = kcu.constraint_schema
         AND tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_catalog = tc.constraint_catalog
         AND ccu.constraint_schema = tc.constraint_schema
         AND ccu.constraint_name = tc.constraint_name
        JOIN information_schema.referential_constraints rc
          ON rc.constraint_catalog = tc.constraint_catalog
         AND rc.constraint_schema = tc.constraint_schema
         AND rc.constraint_name = tc.constraint_name
        WHERE tc.table_schema = 'public' AND tc.table_name = %s AND tc.constraint_type = 'FOREIGN KEY'
        GROUP BY tc.constraint_name, ccu.table_name, rc.delete_rule
        """,
        (table_name,),
    )
    foreign_keys = [
        {
            "name": name,
            "columns": _postgres_string_list(local_columns),
            "referencedTable": referenced_table,
            "referencedColumns": _postgres_string_list(referenced_columns),
            "onDelete": delete_rule,
        }
        for name, local_columns, referenced_table, referenced_columns, delete_rule in cursor.fetchall()
    ]
    cursor.execute(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = %s
        ORDER BY indexname
        """,
        (table_name,),
    )
    indexes = [_parse_index_definition(name, definition) for name, definition in cursor.fetchall()]
    return {
        "name": table_name,
        "columns": columns,
        "primaryKey": primary_key,
        "unique": unique,
        "foreignKeys": foreign_keys,
        "indexes": indexes,
    }


def _canonicalize_table(raw_table: Any) -> dict[str, Any]:
    if not isinstance(raw_table, Mapping):
        raise ValueError("schema tables must be objects")
    table = {
        "name": _string(raw_table, "name"),
        "columns": sorted(
            [
                {
                    "name": _string(column, "name"),
                    "type": _string(column, "type"),
                    "nullable": bool(column.get("nullable")),
                    "default": column.get("default"),
                }
                for column in raw_table.get("columns", [])
            ],
            key=lambda column: column["name"],
        ),
        "primaryKey": _canonicalize_key(raw_table.get("primaryKey")),
        "unique": sorted([_canonicalize_key(key) for key in raw_table.get("unique", [])], key=_key_sort_key),
        "foreignKeys": sorted(
            [
                {
                    "name": _string(key, "name"),
                    "columns": sorted(_string_list(key, "columns")),
                    "referencedTable": _string(key, "referencedTable"),
                    "referencedColumns": sorted(_string_list(key, "referencedColumns")),
                    "onDelete": _string(key, "onDelete").upper(),
                }
                for key in raw_table.get("foreignKeys", [])
            ],
            key=lambda key: (key["referencedTable"], key["columns"], key["referencedColumns"], key["name"]),
        ),
        "indexes": sorted(
            [
                {
                    "name": _string(index, "name"),
                    "elements": _string_list(index, "elements"),
                    "method": _string(index, "method").lower(),
                    "unique": bool(index.get("unique")),
                }
                for index in raw_table.get("indexes", [])
            ],
            key=lambda index: (index["method"], index["unique"], index["elements"], index["name"]),
        ),
    }
    return table


def _compatibility_table(table: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": table["name"],
        "columns": table["columns"],
        "primaryKey": None if table["primaryKey"] is None else {"columns": table["primaryKey"]["columns"]},
        "unique": [{"columns": key["columns"]} for key in table["unique"]],
        "foreignKeys": [
            {
                "columns": key["columns"],
                "referencedTable": key["referencedTable"],
                "referencedColumns": key["referencedColumns"],
                "onDelete": key["onDelete"],
            }
            for key in table["foreignKeys"]
        ],
        "indexes": [
            {"elements": index["elements"], "method": index["method"], "unique": index["unique"]}
            for index in table["indexes"]
        ],
    }


def _canonicalize_key(raw_key: Any) -> dict[str, Any] | None:
    if raw_key is None:
        return None
    return {"name": _string(raw_key, "name"), "columns": sorted(_string_list(raw_key, "columns"))}


def _key_sort_key(key: Mapping[str, Any]) -> tuple[list[str], str]:
    return key["columns"], key["name"]


def _parse_index_definition(name: str, definition: str) -> dict[str, Any]:
    method_match = re.search(r"\bUSING\s+(\w+)", definition, re.IGNORECASE)
    method = method_match.group(1).lower() if method_match else "btree"
    element_match = re.search(r"\((.*)\)", definition)
    elements = [element.strip() for element in element_match.group(1).split(",")] if element_match else []
    return {"name": name, "elements": elements, "method": method, "unique": "CREATE UNIQUE INDEX" in definition.upper()}


def _string(mapping: Any, field: str) -> str:
    if not isinstance(mapping, Mapping) or not isinstance(mapping.get(field), str) or not mapping[field]:
        raise ValueError(f"schema field {field} must be a non-empty string")
    return mapping[field]


def _string_list(mapping: Any, field: str) -> list[str]:
    value = mapping.get(field) if isinstance(mapping, Mapping) else None
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"schema field {field} must be a list of strings")
    return list(value)


def _postgres_string_list(value: Any) -> list[str]:
    """Normalize JSON aggregate values returned by psycopg across adapters."""

    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError("PostgreSQL aggregate must be a JSON string array") from error
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError("PostgreSQL aggregate must be a list of non-empty strings")
    return list(value)


def _major_version(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("PostgreSQL version must be a non-empty string")
    match = re.match(r"(\d+)", value)
    if not match:
        raise ValueError("PostgreSQL version must start with its major number")
    return match.group(1)


def _normalized_key(key: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (key or "").casefold())


def _is_absolute_path(value: str) -> bool:
    return PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute() or bool(PureWindowsPath(value).drive)


def _is_free_text_key(key: str) -> bool:
    return any(
        key.endswith(suffix)
        for suffix in ("title", "summary", "excerpt", "snippet", "question", "answer", "understanding", "statement", "claim", "locator", "message")
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("capture", "compare"):
        command = subparsers.add_parser(name)
        command.add_argument("--database-url", required=True, help="Explicit PostgreSQL source URL")
        command.add_argument("--snapshot", type=Path, required=True, help="Schema snapshot path")
    arguments = parser.parse_args(argv)
    catalog = fetch_postgres_catalog(arguments.database_url)
    if arguments.command == "capture":
        write_schema_snapshot(catalog, arguments.snapshot)
        return 0
    try:
        compare_schema(catalog, arguments.snapshot)
    except PostgresSchemaMismatch as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
