from __future__ import annotations

from init_db import create_database
from db import SQLiteAdapter, ValidationError


def main() -> None:
    db_path = create_database()
    adapter = SQLiteAdapter(db_path)

    print("Tables:", ", ".join(adapter.list_tables()))
    print("Search A1:", adapter.search("students", filters=[{"column": "cohort", "op": "=", "value": "A1"}]))
    print("Insert:", adapter.insert("students", {"name": "Minh Demo", "cohort": "A1", "score": 89}))
    print("Average by cohort:", adapter.aggregate("students", "avg", column="score", group_by="cohort"))
    print("Database schema tables:", list(adapter.get_database_schema()["tables"].keys()))

    try:
        adapter.search("missing_table")
    except ValidationError as exc:
        print("Expected error:", exc)


if __name__ == "__main__":
    main()
