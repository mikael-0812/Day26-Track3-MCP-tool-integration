from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from db import SQLiteAdapter, ValidationError
from init_db import DB_PATH, create_database


if not Path(DB_PATH).exists():
    create_database()

adapter = SQLiteAdapter(DB_PATH)
mcp = FastMCP("SQLite Lab MCP Server")


@mcp.tool(name="search")
def search(
    table: str,
    filters: list[dict[str, Any]] | None = None,
    columns: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str | None = None,
    descending: bool = False,
) -> dict[str, Any]:
    """Search rows in a validated SQLite table with optional filters and pagination."""
    try:
        return adapter.search(table, columns, filters, limit, offset, order_by, descending)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


@mcp.tool(name="insert")
def insert(table: str, values: dict[str, Any]) -> dict[str, Any]:
    """Insert one row into a validated SQLite table."""
    try:
        return adapter.insert(table, values)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: str | None = None,
    filters: list[dict[str, Any]] | None = None,
    group_by: str | None = None,
) -> dict[str, Any]:
    """Run count, avg, sum, min, or max over a validated SQLite table."""
    try:
        return adapter.aggregate(table, metric, column, filters, group_by)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


@mcp.resource("schema://database")
def database_schema() -> str:
    """Return the full database schema as JSON text."""
    return json.dumps(adapter.get_database_schema(), indent=2)


@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """Return one table schema as JSON text."""
    try:
        return json.dumps(adapter.get_table_schema(table_name), indent=2)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


if __name__ == "__main__":
    mcp.run()
