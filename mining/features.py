"""Shared dataset access for the data-mining modules."""
import pandas as pd

from warehouse.database import get_connection

NUMERIC_FEATURES = ["age", "student_semester", "gpa", "attendance_pct", "study_hours",
                    "sleep_hours", "exercise_days", "social_media_hours"]
CATEGORICAL_FEATURES = ["gender", "department"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET = "risk_level"
CLASSES = ["Low", "Medium", "High"]

# Scores and counseling are NOT features: they are the outcome (or a consequence of it),
# using them would leak the answer into the prediction model.
FEATURE_LABELS = {
    "age": "Age", "student_semester": "Semester", "gpa": "GPA", "attendance_pct": "Attendance %",
    "study_hours": "Study hours", "sleep_hours": "Sleep hours", "exercise_days": "Exercise days",
    "social_media_hours": "Social media hours", "gender": "Gender", "department": "Department",
}


def load_dataset():
    with get_connection(readonly=True) as conn:
        return pd.read_sql_query("SELECT * FROM vw_depression_flat", conn)
