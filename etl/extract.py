"""EXTRACT - read the six source files (one per data source in the proposal)."""
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

SOURCES = {
    "student_info": "Student Information System",
    "academic_records": "Academic Records",
    "attendance": "Attendance System",
    "lifestyle_survey": "Lifestyle Survey",
    "mental_health_survey": "Mental Health Survey",
    "counseling_records": "Counseling Records",
}


def extract_all(raw_dir=RAW_DIR):
    raw_dir = Path(raw_dir)
    frames = {}
    for name in SOURCES:
        path = raw_dir / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. Run `python data/generate_data.py` or add your own source files.")
        frames[name] = pd.read_csv(path, encoding="utf-8-sig", skipinitialspace=True)
    return frames
