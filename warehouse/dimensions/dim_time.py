"""DIM_TIME (Time_ID PK, Date, Month, Semester, Year). Semester = Spring (Jan-Jun) / Fall (Jul-Dec)."""
import calendar

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS dim_time (
    time_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    date       TEXT NOT NULL UNIQUE,
    month      INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    semester   TEXT NOT NULL,
    year       INTEGER NOT NULL
)
"""


def load(conn, df):
    """Dates are inserted in sorted order so time_id grows with the date."""
    rows = []
    for d in sorted(df["assessment_date"].dt.strftime("%Y-%m-%d").unique()):
        year, month = int(d[:4]), int(d[5:7])
        rows.append((d, month, calendar.month_name[month],
                     "Spring" if month <= 6 else "Fall", year))
    conn.executemany(
        "INSERT OR IGNORE INTO dim_time (date, month, month_name, semester, year) VALUES (?, ?, ?, ?, ?)",
        rows)
    res = conn.execute("SELECT date, time_id FROM dim_time").fetchall()
    return {r[0]: r[1] for r in res}
