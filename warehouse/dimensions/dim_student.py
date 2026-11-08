"""DIM_STUDENT (Student_ID PK, Gender, Age, Department, Semester)."""

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS dim_student (
    student_id TEXT PRIMARY KEY,
    gender     TEXT NOT NULL,
    age        INTEGER,
    department TEXT NOT NULL,
    semester   INTEGER
)
"""


def load(conn, df):
    uniq = df.drop_duplicates("student_id", keep="last")[
        ["student_id", "gender", "age", "department", "semester"]]
    conn.executemany(
        "INSERT OR REPLACE INTO dim_student (student_id, gender, age, department, semester) "
        "VALUES (?, ?, ?, ?, ?)",
        [(r.student_id, r.gender, int(r.age), r.department, int(r.semester))
         for r in uniq.itertuples()])
    return len(uniq)
