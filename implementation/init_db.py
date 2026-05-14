from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "school.db"


SCHEMA_SQL = """
DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS students;

CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cohort TEXT NOT NULL,
    score REAL NOT NULL CHECK (score >= 0 AND score <= 100)
);

CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    level TEXT NOT NULL
);

CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    FOREIGN KEY (student_id) REFERENCES students(id),
    FOREIGN KEY (course_id) REFERENCES courses(id)
);
"""


SEED_SQL = """
INSERT INTO students (name, cohort, score) VALUES
    ('An Nguyen', 'A1', 88.5),
    ('Bao Tran', 'A1', 91.0),
    ('Chi Le', 'B1', 76.0),
    ('Dung Pham', 'B1', 84.5),
    ('Ha Vo', 'C1', 93.0);

INSERT INTO courses (title, level) VALUES
    ('MCP Foundations', 'beginner'),
    ('SQLite for Agents', 'beginner'),
    ('Tool Safety', 'intermediate');

INSERT INTO enrollments (student_id, course_id, status) VALUES
    (1, 1, 'active'),
    (1, 2, 'active'),
    (2, 1, 'active'),
    (3, 2, 'completed'),
    (4, 3, 'active'),
    (5, 3, 'completed');
"""


def create_database(db_path: Path = DB_PATH) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA_SQL)
        conn.executescript(SEED_SQL)
        conn.commit()
    return db_path


if __name__ == "__main__":
    path = create_database()
    print(f"Created database at {path}")
