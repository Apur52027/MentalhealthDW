"""TRANSFORM - clean each source, integrate them on (student_id, assessment_date),
derive analysis bands and the Low / Medium / High risk level."""
import pandas as pd

KEYS = ["student_id", "assessment_date"]

# ------------------------------------------------------------------ business rules
def risk_level(phq9):
    """PHQ-9 total: 0-9 Low, 10-14 Medium (moderate), 15-27 High. Screening cut-offs, NOT a diagnosis."""
    return "Low" if phq9 < 10 else "Medium" if phq9 < 15 else "High"


def gpa_band(v):
    return "Below 2.5" if v < 2.5 else "2.5-3.19" if v < 3.2 else "3.2+"


def attendance_band(v):
    return "<60%" if v < 60 else "60-79%" if v < 80 else "80%+"


def sleep_band(v):
    return "Short (<6h)" if v < 6 else "Normal (6-8h)" if v <= 8 else "Long (>8h)"


def exercise_band(v):
    return "None" if v == 0 else "Occasional (1-2 days)" if v <= 2 else "Regular (3+ days)"


def social_media_band(v):
    return "<3h" if v < 3 else "3-5h" if v <= 5 else ">5h"


def anxiety_level(v):          # GAD-7
    return "Minimal" if v < 5 else "Mild" if v < 10 else "Moderate" if v < 15 else "Severe"


def stress_level(v):           # PSS-10
    return "Low" if v < 14 else "Moderate" if v < 27 else "High"


def counseling_status(sessions):
    return "None" if sessions <= 0 else "Occasional" if sessions <= 2 else "Regular"


GENDER_MAP = {"m": "Male", "male": "Male", "f": "Female", "female": "Female"}

# ------------------------------------------------------------------ helpers
def _ids(s):
    return s.astype("string").str.strip().str.upper()


def _dates(s):
    s = s.astype("string").str.strip()
    iso = pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")
    dmy = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    return iso.fillna(dmy)


def _valid(series, lo, hi):
    """Numeric column where values outside [lo, hi] become NaN."""
    s = pd.to_numeric(series, errors="coerce")
    return s.where(s.between(lo, hi))


def _keyed(df, report, name):
    df = df.copy()
    df["student_id"] = _ids(df["student_id"])
    df["assessment_date"] = _dates(df["assessment_date"])
    before = len(df)
    df = df.dropna(subset=KEYS)
    df = df[df["student_id"] != ""]
    n_dup = len(df) - len(df.drop_duplicates(KEYS))
    df = df.drop_duplicates(KEYS, keep="first")
    report[f"{name}_dropped_bad_keys"] = int(before - len(df) - n_dup)
    report[f"{name}_duplicates_removed"] = int(n_dup)
    return df


ACRONYMS = {"CSE", "EEE", "BBA", "MBA", "ICT", "CE", "ME", "IPE", "ETE"}


def _std_department(v):
    v = " ".join(str(v).split())
    return v.upper() if v.upper() in ACRONYMS else v.title()


# ------------------------------------------------------------------ main transform
def transform(src):
    report = {"rows_in": {k: int(len(v)) for k, v in src.items()}}

    # ---- student dimension source
    st = src["student_info"].copy()
    st["student_id"] = _ids(st["student_id"])
    st = st.dropna(subset=["student_id"]).drop_duplicates("student_id", keep="first")
    st["gender"] = st["gender"].astype("string").str.strip().str.lower().map(GENDER_MAP).fillna("Other")
    st["department"] = st["department"].map(_std_department)
    st["age"] = _valid(st["age"], 16, 45)
    st["age"] = st["age"].fillna(st["age"].median()).round().astype(int)
    st["semester"] = _valid(st["semester"], 1, 12)
    st["semester"] = st["semester"].fillna(st["semester"].median()).round().astype(int)
    st = st[["student_id", "gender", "age", "department", "semester"]]

    # ---- measurement sources
    mh = _keyed(src["mental_health_survey"], report, "mental_health")
    for col, hi in (("depression_score", 27), ("stress_score", 40), ("anxiety_score", 21)):
        mh[col] = _valid(mh[col], 0, hi)
    before = len(mh)
    mh = mh.dropna(subset=["depression_score", "stress_score", "anxiety_score"])
    report["mental_health_dropped_missing_scores"] = int(before - len(mh))

    ac = _keyed(src["academic_records"], report, "academic")
    ac["gpa"] = _valid(ac["gpa"], 0, 4)
    ac["study_hours"] = _valid(ac["study_hours"], 0, 16)

    at = _keyed(src["attendance"], report, "attendance")
    at["attendance_pct"] = _valid(at["attendance_pct"], 0, 100)

    li = _keyed(src["lifestyle_survey"], report, "lifestyle")
    li["sleep_hours"] = _valid(li["sleep_hours"], 0, 16)
    li["exercise_days"] = _valid(li["exercise_days"], 0, 7)
    li["social_media_hours"] = _valid(li["social_media_hours"], 0, 24)

    co = _keyed(src["counseling_records"], report, "counseling")
    co["sessions_attended"] = pd.to_numeric(co["sessions_attended"], errors="coerce").fillna(0)

    # ---- integration
    df = mh[KEYS + ["depression_score", "stress_score", "anxiety_score"]]
    before = len(df)
    df = df.merge(st, on="student_id", how="inner")
    report["dropped_unknown_student"] = int(before - len(df))
    df = (df.merge(ac[KEYS + ["gpa", "study_hours"]], on=KEYS, how="left")
            .merge(at[KEYS + ["attendance_pct"]], on=KEYS, how="left")
            .merge(li[KEYS + ["sleep_hours", "exercise_days", "social_media_hours"]], on=KEYS, how="left")
            .merge(co[KEYS + ["sessions_attended"]], on=KEYS, how="left"))
    df["sessions_attended"] = df["sessions_attended"].fillna(0)      # no record = no counseling

    # ---- impute missing measurements with the department median
    imputed = {}
    for col in ["gpa", "study_hours", "attendance_pct", "sleep_hours", "exercise_days", "social_media_hours"]:
        imputed[col] = int(df[col].isna().sum())
        df[col] = df[col].fillna(df.groupby("department")[col].transform("median"))
        df[col] = df[col].fillna(df[col].median())
    report["imputed_values"] = imputed

    df["gpa"] = df["gpa"].round(2)
    for col in ["study_hours", "attendance_pct", "sleep_hours", "social_media_hours"]:
        df[col] = df[col].round(1)
    df["exercise_days"] = df["exercise_days"].round().astype(int)
    for col in ["depression_score", "stress_score", "anxiety_score"]:
        df[col] = df[col].round().astype(int)

    # ---- derived attributes
    df["risk_level"] = df["depression_score"].map(risk_level)
    df["gpa_band"] = df["gpa"].map(gpa_band)
    df["attendance_band"] = df["attendance_pct"].map(attendance_band)
    df["sleep_band"] = df["sleep_hours"].map(sleep_band)
    df["exercise_band"] = df["exercise_days"].map(exercise_band)
    df["social_media_band"] = df["social_media_hours"].map(social_media_band)
    df["anxiety_level"] = df["anxiety_score"].map(anxiety_level)
    df["stress_level"] = df["stress_score"].map(stress_level)
    df["counseling_status"] = df["sessions_attended"].map(counseling_status)

    df = df.sort_values(["assessment_date", "student_id"]).reset_index(drop=True)
    report["rows_out"] = int(len(df))
    report["students"] = int(df["student_id"].nunique())
    return df, report
