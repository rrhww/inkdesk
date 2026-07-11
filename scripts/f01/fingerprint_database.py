"""Create a content-free PostgreSQL fingerprint for F01 backup and restore evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from psycopg import connect
from psycopg.rows import dict_row
from psycopg.sql import Identifier, SQL

from baseline_contracts import canonical_sha256, fingerprint_table_rows


def fingerprint_database(database_url: str) -> dict[str, Any]:
    if not database_url or not database_url.strip():
        raise ValueError("An explicit PostgreSQL database URL is required")
    connection_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    tables: list[dict[str, Any]] = []
    with connect(connection_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
            for row in cursor.fetchall():
                table_name = row["table_name"]
                primary_key = _primary_key(cursor, table_name)
                if not primary_key:
                    raise ValueError(f"table {table_name} has no primary key; F01 will not silently skip it")
                order_by = SQL(", ").join(Identifier(column) for column in primary_key)
                cursor.execute(SQL("SELECT * FROM {}.{} ORDER BY {}").format(Identifier("public"), Identifier(table_name), order_by))
                tables.append(fingerprint_table_rows(table_name, cursor.fetchall(), primary_key=primary_key))
    return {"tables": tables, "sha256": canonical_sha256(tables)}


def _primary_key(cursor: Any, table_name: str) -> list[str]:
    cursor.execute(
        """
        SELECT attribute.attname
        FROM pg_index index_definition
        JOIN pg_class table_definition ON table_definition.oid = index_definition.indrelid
        JOIN pg_namespace schema_definition ON schema_definition.oid = table_definition.relnamespace
        JOIN pg_attribute attribute ON attribute.attrelid = table_definition.oid AND attribute.attnum = ANY(index_definition.indkey)
        WHERE schema_definition.nspname = 'public' AND table_definition.relname = %s AND index_definition.indisprimary
        ORDER BY array_position(index_definition.indkey, attribute.attnum)
        """,
        (table_name,),
    )
    return [row["attname"] for row in cursor.fetchall()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    fingerprint = fingerprint_database(arguments.database_url)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(fingerprint, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
