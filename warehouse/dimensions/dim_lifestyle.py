"""DIM_LIFESTYLE (Lifestyle_ID PK, Sleep Hours, Exercise, Social Media Usage) + bands."""
import pandas as pd

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS dim_lifestyle (
    lifestyle_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    sleep_hours         REAL NOT NULL,
    exercise_days       INTEGER NOT NULL,
    social_media_hours  REAL NOT NULL,
    sleep_band          TEXT NOT NULL,
    exercise_band       TEXT NOT NULL,
    social_media_band   TEXT NOT NULL,
    UNIQUE (sleep_hours, exercise_days, social_media_hours)
)
"""
KEY = ["sleep_hours", "exercise_days", "social_media_hours"]


def load(conn, df):
    uniq = df[KEY + ["sleep_band", "exercise_band", "social_media_band"]].drop_duplicates(KEY)
    conn.executemany(
        "INSERT OR IGNORE INTO dim_lifestyle (sleep_hours, exercise_days, social_media_hours, "
        "sleep_band, exercise_band, social_media_band) VALUES (?, ?, ?, ?, ?, ?)",
        [(r.sleep_hours, int(r.exercise_days), r.social_media_hours,
          r.sleep_band, r.exercise_band, r.social_media_band) for r in uniq.itertuples()])
    ids = pd.read_sql_query(
        "SELECT lifestyle_id, sleep_hours, exercise_days, social_media_hours FROM dim_lifestyle", conn)
    return df.merge(ids, on=KEY, how="left")["lifestyle_id"].to_numpy()
