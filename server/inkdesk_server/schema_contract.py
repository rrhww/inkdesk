from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import Engine, text


F01_COMPATIBILITY_DIGEST = "4c7413a2ef0b1c571513bbeb672c9f18dc8afd9cf0a64e1fa7533c4a9c6ba519"
F04_COMPATIBILITY_DIGEST = "dc3924443c15c37e017e54494b2d6f4b75846595bb7a5ce05eb0cdef7947407d"
F05_COMPATIBILITY_DIGEST = "c00454f2920fb537c950589dca368631a97f69ea5c2c8702d4a1f2992cb1b029"
REVISION_SCHEMA_DIGESTS = {
    "f02_0001": F01_COMPATIBILITY_DIGEST,
    "f04_0002": F04_COMPATIBILITY_DIGEST,
    "f05_0003": F05_COMPATIBILITY_DIGEST,
}


def schema_digest_for_revision(revision: str) -> str:
    return REVISION_SCHEMA_DIGESTS[revision]


def application_schema_digest(engine: Engine, *, exclude_tables: Iterable[str] = ()) -> str:
    if engine.dialect.name != "postgresql":
        raise ValueError("F01 compatibility digest is only defined for PostgreSQL")
    excluded = set(exclude_tables)
    with engine.connect() as connection:
        version = connection.execute(text("SHOW server_version")).scalar_one()
        extensions = [
            {"name": row.name, "version": row.version}
            for row in connection.execute(text("SELECT extname AS name, extversion AS version FROM pg_extension"))
            if row.name == "vector"
        ]
        table_names = [
            row.name
            for row in connection.execute(
                text(
                    """
                    SELECT table_name AS name
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                    """
                )
            )
            if row.name not in excluded
        ]
        tables = [_fetch_table(connection, table_name) for table_name in table_names]
    return _compatibility_digest({"postgres": {"version": version, "extensions": extensions}, "tables": tables})


def table_data_fingerprints(engine: Engine, *, exclude_tables: Iterable[str] = ()) -> dict[str, dict[str, int | str]]:
    if engine.dialect.name != "postgresql":
        raise ValueError("Canonical row fingerprints are only defined for PostgreSQL")
    excluded = set(exclude_tables)
    with engine.connect() as connection:
        table_names = [
            row.name
            for row in connection.execute(
                text(
                    """
                    SELECT table_name AS name
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                    """
                )
            )
            if row.name not in excluded
        ]
        result: dict[str, dict[str, int | str]] = {}
        for table_name in table_names:
            quoted_table = '"' + table_name.replace('"', '""') + '"'
            rows = [
                row.payload
                for row in connection.execute(
                    text(
                        f"SELECT row_to_json(row_data)::text AS payload "
                        f"FROM public.{quoted_table} AS row_data "
                        f"ORDER BY row_to_json(row_data)::text"
                    )
                )
            ]
            result[table_name] = {
                "rowCount": len(rows),
                "fingerprint": hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest(),
            }
    return result


def _fetch_table(connection: Any, table_name: str) -> dict[str, Any]:
    columns = [
        {
            "name": row.name,
            "type": row.udt_name if row.data_type == "USER-DEFINED" else row.data_type,
            "nullable": row.is_nullable == "YES",
            "default": row.default,
        }
        for row in connection.execute(
            text(
                """
                SELECT column_name AS name,
                       data_type,
                       udt_name,
                       is_nullable,
                       column_default AS default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :table_name
                ORDER BY ordinal_position
                """
            ),
            {"table_name": table_name},
        )
    ]
    primary_key: dict[str, Any] | None = None
    unique: list[dict[str, Any]] = []
    for row in connection.execute(
        text(
            """
            SELECT tc.constraint_name AS name,
                   tc.constraint_type AS kind,
                   array_to_json(array_agg(kcu.column_name ORDER BY kcu.ordinal_position)) AS columns
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_catalog = kcu.constraint_catalog
             AND tc.constraint_schema = kcu.constraint_schema
             AND tc.constraint_name = kcu.constraint_name
            WHERE tc.table_schema = 'public'
              AND tc.table_name = :table_name
              AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
            GROUP BY tc.constraint_name, tc.constraint_type
            """
        ),
        {"table_name": table_name},
    ):
        item = {"name": row.name, "columns": _string_list(row.columns)}
        if row.kind == "PRIMARY KEY":
            primary_key = item
        else:
            unique.append(item)
    foreign_keys = [
        {
            "name": row.name,
            "columns": _string_list(row.local_columns),
            "referencedTable": row.referenced_table,
            "referencedColumns": _string_list(row.referenced_columns),
            "onDelete": row.delete_rule,
        }
        for row in connection.execute(
            text(
                """
                SELECT tc.constraint_name AS name,
                       array_to_json(array_agg(kcu.column_name ORDER BY kcu.ordinal_position)) AS local_columns,
                       ccu.table_name AS referenced_table,
                       array_to_json(array_agg(ccu.column_name ORDER BY kcu.ordinal_position)) AS referenced_columns,
                       rc.delete_rule AS delete_rule
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
                WHERE tc.table_schema = 'public'
                  AND tc.table_name = :table_name
                  AND tc.constraint_type = 'FOREIGN KEY'
                GROUP BY tc.constraint_name, ccu.table_name, rc.delete_rule
                """
            ),
            {"table_name": table_name},
        )
    ]
    indexes = [
        _parse_index(row.name, row.definition)
        for row in connection.execute(
            text(
                """
                SELECT indexname AS name, indexdef AS definition
                FROM pg_indexes
                WHERE schemaname = 'public' AND tablename = :table_name
                ORDER BY indexname
                """
            ),
            {"table_name": table_name},
        )
    ]
    return {
        "name": table_name,
        "columns": columns,
        "primaryKey": primary_key,
        "unique": unique,
        "foreignKeys": foreign_keys,
        "indexes": indexes,
    }


def _compatibility_digest(catalog: Mapping[str, Any]) -> str:
    postgres = catalog["postgres"]
    canonical_postgres = {
        "majorVersion": _major_version(postgres["version"]),
        "extensions": sorted([{"name": extension["name"]} for extension in postgres["extensions"]], key=lambda item: item["name"]),
    }
    tables = sorted((_canonicalize_table(table) for table in catalog["tables"]), key=lambda item: item["name"])
    compatibility = {"postgres": canonical_postgres, "tables": [_compatibility_table(table) for table in tables]}
    encoded = json.dumps(compatibility, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _canonicalize_table(table: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": str(table["name"]),
        "columns": sorted(
            [
                {
                    "name": str(column["name"]),
                    "type": str(column["type"]),
                    "nullable": bool(column["nullable"]),
                    "default": column["default"],
                }
                for column in table["columns"]
            ],
            key=lambda column: column["name"],
        ),
        "primaryKey": _canonicalize_key(table["primaryKey"]),
        "unique": sorted([_canonicalize_key(key) for key in table["unique"]], key=lambda key: (key["columns"], key["name"])),
        "foreignKeys": sorted(
            [
                {
                    "name": str(key["name"]),
                    "columns": sorted(_string_list(key["columns"])),
                    "referencedTable": str(key["referencedTable"]),
                    "referencedColumns": sorted(_string_list(key["referencedColumns"])),
                    "onDelete": str(key["onDelete"]).upper(),
                }
                for key in table["foreignKeys"]
            ],
            key=lambda key: (key["referencedTable"], key["columns"], key["referencedColumns"], key["name"]),
        ),
        "indexes": sorted(
            [
                {
                    "name": str(index["name"]),
                    "elements": _string_list(index["elements"]),
                    "method": str(index["method"]).lower(),
                    "unique": bool(index["unique"]),
                }
                for index in table["indexes"]
            ],
            key=lambda index: (index["method"], index["unique"], index["elements"], index["name"]),
        ),
    }


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


def _canonicalize_key(key: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if key is None:
        return None
    return {"name": str(key["name"]), "columns": sorted(_string_list(key["columns"]))}


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError("PostgreSQL catalog returned an invalid string list")
    return list(value)


def _parse_index(name: str, definition: str) -> dict[str, Any]:
    method_match = re.search(r"\bUSING\s+(\w+)", definition, re.IGNORECASE)
    element_match = re.search(r"\((.*)\)", definition)
    return {
        "name": name,
        "elements": [item.strip() for item in element_match.group(1).split(",")] if element_match else [],
        "method": method_match.group(1).lower() if method_match else "btree",
        "unique": "CREATE UNIQUE INDEX" in definition.upper(),
    }


def _major_version(version: str) -> str:
    match = re.match(r"(\d+)", version)
    if not match:
        raise ValueError("PostgreSQL version must begin with its major version")
    return match.group(1)
