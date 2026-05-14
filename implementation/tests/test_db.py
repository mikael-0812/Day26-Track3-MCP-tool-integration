from __future__ import annotations

import pytest

from db import SQLiteAdapter, ValidationError
from init_db import create_database


@pytest.fixture()
def adapter(tmp_path):
    db_path = create_database(tmp_path / "test.db")
    return SQLiteAdapter(db_path)


def test_search_filters_order_and_pagination(adapter):
    result = adapter.search(
        "students",
        filters=[{"column": "cohort", "op": "=", "value": "A1"}],
        order_by="score",
        descending=True,
        limit=1,
    )

    assert result["count"] == 1
    assert result["rows"][0]["name"] == "Bao Tran"


def test_insert_returns_inserted_payload(adapter):
    result = adapter.insert("students", {"name": "Minh", "cohort": "A1", "score": 90})

    assert result["inserted"]["name"] == "Minh"
    assert result["inserted"]["id"] > 0


def test_aggregate_average_by_group(adapter):
    result = adapter.aggregate("students", "avg", column="score", group_by="cohort")

    assert {row["cohort"] for row in result["rows"]} == {"A1", "B1", "C1"}


def test_rejects_unknown_table(adapter):
    with pytest.raises(ValidationError, match="unknown table"):
        adapter.search("missing_table")


def test_rejects_unknown_column(adapter):
    with pytest.raises(ValidationError, match="unknown column"):
        adapter.search("students", columns=["password"])


def test_rejects_bad_operator(adapter):
    with pytest.raises(ValidationError, match="unsupported filter operator"):
        adapter.search("students", filters=[{"column": "score", "op": "contains", "value": 90}])


def test_rejects_empty_insert(adapter):
    with pytest.raises(ValidationError, match="must not be empty"):
        adapter.insert("students", {})
