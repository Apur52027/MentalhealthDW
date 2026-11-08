"""Run the named SQL queries from bi_queries.sql."""
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd

from warehouse.database import get_connection

SQL_FILE = Path(__file__).with_name("bi_queries.sql")
CORR_COLUMNS = ["depression_score", "stress_score", "anxiety_score", "gpa", "attendance_pct",
                "study_hours", "sleep_hours", "exercise_days", "social_media_hours"]


@lru_cache(maxsize=1)
def load_queries():
    text = SQL_FILE.read_text(encoding="utf-8")
    parts = re.split(r"^--\s*name:\s*(\w+)\s*$", text, flags=re.M)
    queries = {}
    for name, body in zip(parts[1::2], parts[2::2]):
        sql = "\n".join(l for l in body.splitlines() if not l.strip().startswith("--"))
        queries[name] = sql.strip().rstrip(";")
    return queries


def _norm(value):
    return None if value in (None, "", "All") else value


def run_query(name, dept=None, year=None):
    queries = load_queries()
    if name not in queries:
        raise KeyError(f"Unknown query '{name}'. Available: {sorted(queries)}")
    year = _norm(year)
    params = {"dept": _norm(dept), "year": int(year) if year is not None else None}
    with get_connection(readonly=True) as conn:
        return pd.read_sql_query(queries[name], conn, params=params)


def get_kpis(dept=None, year=None):
    df = run_query("kpi_summary", dept, year)
    if df.empty or pd.isna(df.iloc[0]["assessments"]) or df.iloc[0]["assessments"] == 0:
        return {}
    row = df.iloc[0].to_dict()
    row["students_assessed"] = int(row["students_assessed"])
    row["assessments"] = int(row["assessments"])
    return row


def get_filter_options():
    with get_connection(readonly=True) as conn:
        depts = [r[0] for r in conn.execute("SELECT DISTINCT department FROM dim_student ORDER BY 1")]
        years = [r[0] for r in conn.execute("SELECT DISTINCT year FROM dim_time ORDER BY 1")]
    return depts, years


def get_flat_dataframe(dept=None, year=None):
    sql = ("SELECT * FROM vw_depression_flat WHERE (:dept IS NULL OR department = :dept) "
           "AND (:year IS NULL OR year = :year)")
    year = _norm(year)
    with get_connection(readonly=True) as conn:
        return pd.read_sql_query(sql, conn, params={"dept": _norm(dept),
                                                    "year": int(year) if year is not None else None})


def correlation_matrix(dept=None, year=None):
    df = get_flat_dataframe(dept, year)
    return df[CORR_COLUMNS].corr().round(2) if len(df) > 2 else pd.DataFrame()
