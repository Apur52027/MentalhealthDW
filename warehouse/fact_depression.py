"""FACT_DEPRESSION - grain: one student x one assessment date."""

VIEW_NAME = "vw_depression_flat"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS fact_depression (
    fact_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id       TEXT    NOT NULL REFERENCES dim_student(student_id),
    academic_id      INTEGER NOT NULL REFERENCES dim_academic(academic_id),
    lifestyle_id     INTEGER NOT NULL REFERENCES dim_lifestyle(lifestyle_id),
    mentalhealth_id  INTEGER NOT NULL REFERENCES dim_mentalhealth(mentalhealth_id),
    time_id          INTEGER NOT NULL REFERENCES dim_time(time_id),
    depression_score INTEGER NOT NULL CHECK (depression_score BETWEEN 0 AND 27),
    stress_score     INTEGER NOT NULL CHECK (stress_score BETWEEN 0 AND 40),
    anxiety_score    INTEGER NOT NULL CHECK (anxiety_score BETWEEN 0 AND 21),
    risk_level       TEXT    NOT NULL CHECK (risk_level IN ('Low', 'Medium', 'High')),
    UNIQUE (student_id, time_id)
)
"""

INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_fact_student ON fact_depression(student_id)",
    "CREATE INDEX IF NOT EXISTS idx_fact_time    ON fact_depression(time_id)",
    "CREATE INDEX IF NOT EXISTS idx_fact_risk    ON fact_depression(risk_level)",
]

CREATE_VIEW_SQL = f"""
CREATE VIEW IF NOT EXISTS {VIEW_NAME} AS
SELECT f.fact_id, f.student_id, s.gender, s.age, s.department, s.semester AS student_semester,
       t.date AS assessment_date, t.month, t.month_name, t.semester AS term, t.year,
       a.gpa, a.attendance_pct, a.study_hours, a.gpa_band, a.attendance_band,
       l.sleep_hours, l.exercise_days, l.social_media_hours,
       l.sleep_band, l.exercise_band, l.social_media_band,
       m.counseling_status, m.anxiety_level, m.stress_level,
       f.depression_score, f.stress_score, f.anxiety_score, f.risk_level
FROM fact_depression f
JOIN dim_student      s ON s.student_id      = f.student_id
JOIN dim_academic     a ON a.academic_id     = f.academic_id
JOIN dim_lifestyle    l ON l.lifestyle_id    = f.lifestyle_id
JOIN dim_mentalhealth m ON m.mentalhealth_id = f.mentalhealth_id
JOIN dim_time         t ON t.time_id         = f.time_id
"""

_COLS = ["student_id", "academic_id", "lifestyle_id", "mentalhealth_id", "time_id",
         "depression_score", "stress_score", "anxiety_score", "risk_level"]


def load(conn, df, time_map):
    df = df.copy()
    df["time_id"] = df["assessment_date"].dt.strftime("%Y-%m-%d").map(time_map)
    if df[_COLS].isna().any().any():
        raise ValueError("Missing surrogate keys - check dimension loading.")
    rows = [(r.student_id, int(r.academic_id), int(r.lifestyle_id), int(r.mentalhealth_id),
             int(r.time_id), int(r.depression_score), int(r.stress_score),
             int(r.anxiety_score), r.risk_level) for r in df.itertuples()]
    conn.executemany(
        f"INSERT INTO fact_depression ({', '.join(_COLS)}) VALUES ({', '.join('?' * len(_COLS))})", rows)
    return len(rows)
