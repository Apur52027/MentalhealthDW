"""DIM_ACADEMIC (Academic_ID PK, GPA, Attendance, Study Hours) + analysis bands.
Junk-dimension style: one row per distinct combination of values."""
import pandas as pd

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS dim_academic (
    academic_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    gpa             REAL NOT NULL,
    attendance_pct  REAL NOT NULL,
    study_hours     REAL NOT NULL,
    gpa_band        TEXT NOT NULL,
    attendance_band TEXT NOT NULL,
    UNIQUE (gpa, attendance_pct, study_hours)
)
"""
KEY = ["gpa", "attendance_pct", "study_hours"]


def load(conn, df):
    uniq = df[KEY + ["gpa_band", "attendance_band"]].drop_duplicates(KEY)
    conn.executemany(
        "INSERT OR IGNORE INTO dim_academic (gpa, attendance_pct, study_hours, gpa_band, attendance_band) "
        "VALUES (?, ?, ?, ?, ?)",
        [(r.gpa, r.attendance_pct, r.study_hours, r.gpa_band, r.attendance_band)
         for r in uniq.itertuples()])
    ids = pd.read_sql_query("SELECT academic_id, gpa, attendance_pct, study_hours FROM dim_academic", conn)
    return df.merge(ids, on=KEY, how="left")["academic_id"].to_numpy()
