"""Generate SYNTHETIC source files that mimic the six data sources in the proposal:

  student_info.csv        <- Student Information System
  academic_records.csv    <- Academic Records
  attendance.csv          <- Attendance System
  lifestyle_survey.csv    <- Lifestyle Survey
  mental_health_survey.csv<- Mental Health Survey (PHQ-9, PSS-10, GAD-7 totals)
  counseling_records.csv  <- Counseling Records

All data is artificial (no real students). Some rows are deliberately dirty
(missing values, duplicates, bad labels, out-of-range values, mixed date formats)
so the ETL cleaning step has real work to do.

Run:  python data/generate_data.py
"""
import random
from datetime import datetime
from pathlib import Path

import pandas as pd

RAW = Path(__file__).with_name("raw")
N_STUDENTS = 450
PERIODS = ["2024-03-15", "2024-09-15", "2025-03-15"]
DEPARTMENTS = {"CSE": 0.24, "EEE": 0.14, "BBA": 0.20, "English": 0.14,
               "Agriculture": 0.18, "Law": 0.10}


def clip(x, lo, hi):
    return max(lo, min(hi, x))


def build(seed=2002):
    rng = random.Random(seed)
    info, acad, att, life, mh, couns = [], [], [], [], [], []
    dept_names, dept_w = list(DEPARTMENTS), list(DEPARTMENTS.values())

    for i in range(N_STUDENTS):
        sid = f"S{2001 + i}"
        gender = rng.choices(["Male", "Female"], weights=[0.55, 0.45])[0]
        dept = rng.choices(dept_names, weights=dept_w)[0]
        vuln = rng.gauss(0, 1)                       # hidden vulnerability
        n_periods = rng.choices([1, 2, 3], weights=[0.25, 0.35, 0.40])[0]
        first = rng.randint(0, 3 - n_periods)
        base_sem = rng.randint(1, 6)
        info.append({"student_id": sid, "gender": gender, "age": 18 + base_sem // 2 + rng.randint(0, 2),
                     "department": dept, "semester": base_sem + first})

        for k in range(n_periods):
            date = PERIODS[first + k]
            v = vuln + rng.gauss(0, 0.35)
            sleep = clip(rng.gauss(7.0 - 0.55 * v, 0.95), 3.5, 10.0)
            exercise = int(clip(round(rng.gauss(2.6 - 0.6 * v, 1.5)), 0, 7))
            social = clip(rng.gauss(4.0 + 1.2 * v, 1.7), 0.5, 12.0)
            study = clip(rng.gauss(3.2 + 0.2 * v, 1.3), 0.0, 10.0)
            gpa = clip(rng.gauss(3.1 - 0.30 * v + 0.05 * (sleep - 7), 0.38), 1.5, 4.0)
            attendance = clip(rng.gauss(82 - 6 * v, 9), 30, 100)

            dep = (7.0 + 3.0 * v + 0.9 * (7 - sleep) + 0.5 * (social - 4) - 0.45 * (exercise - 2.6)
                   - 2.2 * (gpa - 3.1) + rng.gauss(0, 2.4))
            dep = int(clip(round(dep), 0, 27))
            stress = int(clip(round(17 + 4.0 * v + 0.9 * (study - 3.2) + 0.25 * dep + rng.gauss(0, 3.2)), 0, 40))
            anxiety = int(clip(round(5 + 2.2 * v + 0.3 * dep + rng.gauss(0, 2.0)), 0, 21))

            p_couns = 0.45 if dep >= 15 else 0.22 if dep >= 10 else 0.04
            sessions = rng.randint(1, 6) if rng.random() < p_couns else 0

            acad.append({"student_id": sid, "assessment_date": date,
                         "gpa": round(gpa, 2), "study_hours": round(study, 1)})
            att.append({"student_id": sid, "assessment_date": date, "attendance_pct": round(attendance, 1)})
            life.append({"student_id": sid, "assessment_date": date, "sleep_hours": round(sleep, 1),
                         "exercise_days": exercise, "social_media_hours": round(social, 1)})
            mh.append({"student_id": sid, "assessment_date": date, "depression_score": dep,
                       "stress_score": stress, "anxiety_score": anxiety})
            couns.append({"student_id": sid, "assessment_date": date, "sessions_attended": sessions})
    return rng, info, acad, att, life, mh, couns


def make_dirty(rng, info, acad, att, life, mh, couns):
    for r in info:
        if rng.random() < 0.05:
            r["gender"] = {"Male": rng.choice(["M", "male"]), "Female": rng.choice(["F", "female"])}[r["gender"]]
        if rng.random() < 0.05:
            r["department"] = rng.choice([f" {r['department'].lower()}", r["department"].upper() + " "])
        if rng.random() < 0.03:
            r["student_id"] = r["student_id"].lower()
    for r in rng.sample(acad, 8):
        r["gpa"] = rng.choice([None, 4.7, -1])
    for r in rng.sample(att, 8):
        r["attendance_pct"] = rng.choice([None, 105.0])
    for r in rng.sample(life, 10):
        r["sleep_hours"] = rng.choice([None, 25.0])
    for r in rng.sample(life, 6):
        r["social_media_hours"] = None
    for r in rng.sample(mh, 4):
        r["depression_score"] = None                       # unusable outcome -> dropped
    for r in att:                                          # mixed date formats
        if rng.random() < 0.08:
            r["assessment_date"] = datetime.strptime(r["assessment_date"], "%Y-%m-%d").strftime("%d/%m/%Y")
    for r in rng.sample(couns, 25):
        couns.remove(r)                                    # missing counseling rows -> "None"
    acad += [dict(r) for r in rng.sample(acad, 6)]         # duplicates
    mh += [dict(r) for r in rng.sample(mh, 4)]
    info += [dict(r) for r in rng.sample(info, 3)]
    return info, acad, att, life, mh, couns


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rng, *tables = build()
    tables = make_dirty(rng, *tables)
    names = ["student_info", "academic_records", "attendance",
             "lifestyle_survey", "mental_health_survey", "counseling_records"]
    for name, rows in zip(names, tables):
        pd.DataFrame(rows).to_csv(RAW / f"{name}.csv", index=False, encoding="utf-8")
        print(f"{name + '.csv':28} {len(rows):5} rows")


if __name__ == "__main__":
    main()
