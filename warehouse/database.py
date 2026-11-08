"""Warehouse connection helpers (SQLite; schema is plain SQL and portable - see schema.sql)."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from warehouse.dimensions import dim_student, dim_academic, dim_lifestyle, dim_mentalhealth, dim_time
from warehouse import fact_depression as fact

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "mental_health_dw.db"

ALL_TABLES = ["dim_student", "dim_academic", "dim_lifestyle", "dim_mentalhealth",
              "dim_time", "fact_depression"]
ALLOWED_OBJECTS = ALL_TABLES + [fact.VIEW_NAME]


@contextmanager
def get_connection(readonly=False):
    if readonly:
        conn = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    else:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_warehouse(reset=False):
    with get_connection() as conn:
        if reset:
            conn.execute(f"DROP VIEW IF EXISTS {fact.VIEW_NAME}")
            for table in reversed(ALL_TABLES):
                conn.execute(f"DROP TABLE IF EXISTS {table}")
        for module in (dim_student, dim_academic, dim_lifestyle, dim_mentalhealth, dim_time):
            conn.execute(module.CREATE_SQL)
        conn.execute(fact.CREATE_SQL)
        for stmt in fact.INDEX_SQL:
            conn.execute(stmt)
        conn.execute(fact.CREATE_VIEW_SQL)


def table_counts():
    counts = {}
    with get_connection() as conn:
        for table in ALL_TABLES:
            try:
                counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except sqlite3.OperationalError:
                counts[table] = 0
    return counts


def warehouse_is_loaded():
    return DB_PATH.exists() and table_counts().get("fact_depression", 0) > 0
