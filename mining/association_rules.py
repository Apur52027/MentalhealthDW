"""ASSOCIATION RULE MINING - pure-Python Apriori (no extra dependency).

Finds combinations of habits that frequently go together with a risk level, e.g.
{Sleep: Short (<6h), Social media: >5h}  ->  {Risk: High}
"""
from itertools import combinations

import pandas as pd

from mining.features import load_dataset

ITEM_COLUMNS = {
    "Sleep": "sleep_band", "Social media": "social_media_band", "Exercise": "exercise_band",
    "GPA": "gpa_band", "Attendance": "attendance_band", "Counseling": "counseling_status",
    "Department": "department", "Gender": "gender", "Risk": "risk_level",
}


def build_transactions(df):
    return [frozenset(f"{label}: {row[col]}" for label, col in ITEM_COLUMNS.items())
            for _, row in df.iterrows()]


def apriori(transactions, min_support=0.05, max_len=4):
    n = len(transactions)
    min_count = min_support * n
    counts = {}
    for t in transactions:
        for item in t:
            counts[frozenset([item])] = counts.get(frozenset([item]), 0) + 1
    frequent = {s: c for s, c in counts.items() if c >= min_count}
    all_frequent = dict(frequent)

    size = 1
    while frequent and size < max_len:
        size += 1
        items = sorted({i for s in frequent for i in s})
        prev = set(frequent)
        candidates = set()
        for s in frequent:
            for item in items:
                if item in s:
                    continue
                cand = s | {item}
                # prune: every (size-1)-subset must be frequent
                if len(cand) == size and all(frozenset(sub) in prev for sub in combinations(cand, size - 1)):
                    candidates.add(cand)
        counts = {c: 0 for c in candidates}
        for t in transactions:
            for c in candidates:
                if c <= t:
                    counts[c] += 1
        frequent = {s: c for s, c in counts.items() if c >= min_count}
        all_frequent.update(frequent)
    return {s: c / n for s, c in all_frequent.items()}


def mine_rules(min_support=0.03, min_confidence=0.4, min_lift=1.2, max_len=4,
               target_prefix="Risk: High", df=None):
    """Rules whose consequent is a single item starting with `target_prefix`."""
    df = load_dataset() if df is None else df
    tx = build_transactions(df)
    support = apriori(tx, min_support, max_len)

    rows = []
    for itemset, sup in support.items():
        if len(itemset) < 2:
            continue
        for cons in itemset:
            if not cons.startswith(target_prefix):
                continue
            ante = itemset - {cons}
            if any(a.startswith("Risk:") for a in ante):
                continue
            conf = sup / support[ante]
            lift = conf / support[frozenset([cons])]
            if conf >= min_confidence and lift >= min_lift:
                rows.append({"if (antecedent)": " AND ".join(sorted(ante)), "then (consequent)": cons,
                             "support": round(sup, 3), "confidence": round(conf, 3), "lift": round(lift, 2),
                             "students": int(round(sup * len(tx)))})
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=["if (antecedent)", "then (consequent)", "support",
                                     "confidence", "lift", "students"])
    return out.sort_values(["lift", "confidence"], ascending=False).reset_index(drop=True)
