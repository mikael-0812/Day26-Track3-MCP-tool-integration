from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class ValidationError(Exception):
    """Raised when a request cannot be safely executed."""


class SQLiteAdapter:
    ALLOWED_OPERATORS = {
        "=": "=",
        "!=": "!=",
        ">": ">",
        ">=": ">=",
        "<": "<",
        "<=": "<=",
        "like": "LIKE",
    }
    ALLOWED_METRICS = {"count", "avg", "sum", "min", "max"}

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def list_tables(self) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [row["name"] for row in rows]

    def get_table_schema(self, table: str) -> dict[str, Any]:
        self.validate_table(table)
        with self.connect() as conn:
            rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        return {
            "table": table,
            "columns": [
                {
                    "name": row["name"],
                    "type": row["type"],
                    "not_null": bool(row["notnull"]),
                    "default": row["dflt_value"],
                    "primary_key": bool(row["pk"]),
                }
                for row in rows
            ],
        }

    def get_database_schema(self) -> dict[str, Any]:
        return {
            "tables": {
                table: self.get_table_schema(table)["columns"]
                for table in self.list_tables()
            }
        }

    def search(
        self,
        table: str,
        columns: list[str] | None = None,
        filters: list[dict[str, Any]] | None = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        self.validate_table(table)
        selected_columns = columns or self.column_names(table)
        self.validate_columns(table, selected_columns)
        self.validate_pagination(limit, offset)

        where_sql, params = self.build_where_clause(table, filters)
        order_sql = ""
        if order_by:
            self.validate_column(table, order_by)
            direction = "DESC" if descending else "ASC"
            order_sql = f' ORDER BY "{order_by}" {direction}'

        column_sql = ", ".join(f'"{column}"' for column in selected_columns)
        sql = f'SELECT {column_sql} FROM "{table}"{where_sql}{order_sql} LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return {
            "table": table,
            "columns": selected_columns,
            "limit": limit,
            "offset": offset,
            "count": len(rows),
            "rows": [dict(row) for row in rows],
        }

    def insert(self, table: str, values: dict[str, Any]) -> dict[str, Any]:
        self.validate_table(table)
        if not values:
            raise ValidationError("insert values must not be empty")
        self.validate_columns(table, list(values.keys()))

        columns = list(values.keys())
        column_sql = ", ".join(f'"{column}"' for column in columns)
        placeholders = ", ".join("?" for _ in columns)
        sql = f'INSERT INTO "{table}" ({column_sql}) VALUES ({placeholders})'

        with self.connect() as conn:
            cursor = conn.execute(sql, [values[column] for column in columns])
            conn.commit()
            inserted_id = cursor.lastrowid

        payload = dict(values)
        if "id" in self.column_names(table) and "id" not in payload:
            payload["id"] = inserted_id
        return {"table": table, "inserted": payload}

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: list[dict[str, Any]] | None = None,
        group_by: str | None = None,
    ) -> dict[str, Any]:
        self.validate_table(table)
        metric_name = metric.lower()
        if metric_name not in self.ALLOWED_METRICS:
            raise ValidationError(f"unsupported aggregate metric: {metric}")
        if metric_name != "count" and not column:
            raise ValidationError(f"{metric_name} requires a column")
        if column:
            self.validate_column(table, column)
        if group_by:
            self.validate_column(table, group_by)

        target = "*" if metric_name == "count" and column is None else f'"{column}"'
        group_select = f'"{group_by}", ' if group_by else ""
        group_sql = f' GROUP BY "{group_by}"' if group_by else ""
        where_sql, params = self.build_where_clause(table, filters)
        sql = (
            f'SELECT {group_select}{metric_name.upper()}({target}) AS value '
            f'FROM "{table}"{where_sql}{group_sql}'
        )

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return {
            "table": table,
            "metric": metric_name,
            "column": column,
            "group_by": group_by,
            "rows": [dict(row) for row in rows],
        }

    def build_where_clause(
        self,
        table: str,
        filters: list[dict[str, Any]] | None,
    ) -> tuple[str, list[Any]]:
        if not filters:
            return "", []
        clauses: list[str] = []
        params: list[Any] = []
        for item in filters:
            column = item.get("column")
            op = str(item.get("op", "=")).lower()
            if column is None:
                raise ValidationError("filter is missing column")
            self.validate_column(table, column)
            if op not in self.ALLOWED_OPERATORS:
                raise ValidationError(f"unsupported filter operator: {op}")
            clauses.append(f'"{column}" {self.ALLOWED_OPERATORS[op]} ?')
            params.append(item.get("value"))
        return " WHERE " + " AND ".join(clauses), params

    def validate_table(self, table: str) -> None:
        if table not in self.list_tables():
            raise ValidationError(f"unknown table: {table}")

    def validate_column(self, table: str, column: str) -> None:
        if column not in self.column_names(table):
            raise ValidationError(f"unknown column for {table}: {column}")

    def validate_columns(self, table: str, columns: list[str]) -> None:
        if not columns:
            raise ValidationError("columns must not be empty")
        for column in columns:
            self.validate_column(table, column)

    def validate_pagination(self, limit: int, offset: int) -> None:
        if limit < 1 or limit > 100:
            raise ValidationError("limit must be between 1 and 100")
        if offset < 0:
            raise ValidationError("offset must be greater than or equal to 0")

    def column_names(self, table: str) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(f'PRAGMA table_info("{table}")').fetchall()
        if not rows:
            raise ValidationError(f"unknown table: {table}")
        return [row["name"] for row in rows]
