"""DIM_MENTALHEALTH (MentalHealth_ID PK, Anxiety Score, Stress Score, Counseling Status)
+ readable severity levels."""
import pandas as pd

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS dim_mentalhealth (
    mentalhealth_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    anxiety_score     INTEGER NOT NULL,
    stress_score      INTEGER NOT NULL,
    counseling_status TEXT NOT NULL,
    anxiety_level     TEXT NOT NULL,
    stress_level      TEXT NOT NULL,
    UNIQUE (anxiety_score, stress_score, counseling_status)
)
"""
KEY = ["anxiety_score", "stress_score", "counseling_status"]


def load(conn, df):
    uniq = df[KEY + ["anxiety_level", "stress_level"]].drop_duplicates(KEY)
    conn.executemany(
        "INSERT OR IGNORE INTO dim_mentalhealth (anxiety_score, stress_score, counseling_status, "
        "anxiety_level, stress_level) VALUES (?, ?, ?, ?, ?)",
        [(int(r.anxiety_score), int(r.stress_score), r.counseling_status,
          r.anxiety_level, r.stress_level) for r in uniq.itertuples()])
    ids = pd.read_sql_query(
        "SELECT mentalhealth_id, anxiety_score, stress_score, counseling_status FROM dim_mentalhealth", conn)
    return df.merge(ids, on=KEY, how="left")["mentalhealth_id"].to_numpy()
