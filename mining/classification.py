"""CLASSIFICATION - predict the depression risk level (Low / Medium / High).

Compares Logistic Regression, Decision Tree and Random Forest with grouped
cross-validation (all rows of one student stay in the same fold - no leakage),
reports held-out test metrics, and ranks the factors with permutation importance.
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from mining.features import (CATEGORICAL_FEATURES, CLASSES, FEATURE_LABELS, FEATURES,
                             NUMERIC_FEATURES, TARGET, load_dataset)

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_PATH = MODEL_DIR / "risk_model.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"
SEED = 42


def _pipeline(estimator):
    pre = ColumnTransformer([
        ("num", StandardScaler(), NUMERIC_FEATURES),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
    ])
    return Pipeline([("pre", pre), ("clf", estimator)])


def _candidates():
    return {
        "Logistic Regression": LogisticRegression(max_iter=2000, class_weight="balanced"),
        "Decision Tree": DecisionTreeClassifier(max_depth=5, min_samples_leaf=8,
                                                class_weight="balanced", random_state=SEED),
        "Random Forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=3,
                                                class_weight="balanced_subsample",
                                                random_state=SEED, n_jobs=-1),
    }


def train_model(save=True):
    df = load_dataset()
    X, y, groups = df[FEATURES], df[TARGET], df["student_id"]

    # held-out test set, split by STUDENT
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=SEED)
    train_idx, test_idx = next(splitter.split(X, y, groups))
    X_tr, X_te, y_tr, y_te = X.iloc[train_idx], X.iloc[test_idx], y.iloc[train_idx], y.iloc[test_idx]

    # model comparison with grouped CV on the training part
    cv = GroupKFold(n_splits=5)
    comparison = {}
    for name, est in _candidates().items():
        scores = cross_val_score(_pipeline(est), X_tr, y_tr, groups=groups.iloc[train_idx],
                                 cv=cv, scoring="f1_macro")
        comparison[name] = {"cv_f1_macro": round(float(scores.mean()), 3),
                            "cv_std": round(float(scores.std()), 3)}
    best_name = max(comparison, key=lambda n: comparison[n]["cv_f1_macro"])

    # evaluate the winner on the untouched test set
    model = _pipeline(_candidates()[best_name]).fit(X_tr, y_tr)
    pred = model.predict(X_te)
    report = classification_report(y_te, pred, labels=CLASSES, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_te, pred, labels=CLASSES)

    # factor ranking (permutation importance on the raw columns)
    perm = permutation_importance(model, X_te, y_te, n_repeats=15, random_state=SEED,
                                  scoring="f1_macro", n_jobs=-1)
    importance = sorted(
        ({"feature": FEATURE_LABELS[f], "importance": round(float(m), 4)}
         for f, m in zip(FEATURES, perm.importances_mean)),
        key=lambda d: d["importance"], reverse=True)

    metrics = {
        "best_model": best_name,
        "comparison": comparison,
        "test_accuracy": round(float(accuracy_score(y_te, pred)), 3),
        "test_f1_macro": round(float(f1_score(y_te, pred, average="macro")), 3),
        "per_class": {c: {k: round(float(report[c][k]), 3) for k in ("precision", "recall", "f1-score")}
                      | {"support": int(report[c]["support"])} for c in CLASSES},
        "confusion_matrix": cm.tolist(),
        "classes": CLASSES,
        "feature_importance": importance,
        "n_train": int(len(train_idx)), "n_test": int(len(test_idx)),
    }

    final = _pipeline(_candidates()[best_name]).fit(X, y)       # deploy on all data
    if save:
        MODEL_DIR.mkdir(exist_ok=True)
        joblib.dump(final, MODEL_PATH)
        METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return final, metrics


def load_model():
    if MODEL_PATH.exists():
        try:
            return joblib.load(MODEL_PATH)
        except Exception:
            pass                                    # corrupt / version mismatch -> retrain
    return train_model()[0]


def load_metrics():
    if METRICS_PATH.exists():
        return json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    return train_model()[1]


def predict_risk(inputs):
    """inputs: dict with the keys in mining.features.FEATURES -> label + class probabilities."""
    model = load_model()
    row = pd.DataFrame([{f: inputs[f] for f in FEATURES}])
    proba = model.predict_proba(row)[0]
    probs = {c: float(p) for c, p in zip(model.classes_, proba)}
    probs = {c: probs.get(c, 0.0) for c in CLASSES}
    return {"label": max(probs, key=probs.get), "probabilities": probs}


def risk_advice(inputs):
    """Simple, explainable suggestions based on the entered habits (not medical advice)."""
    tips = []
    if inputs["sleep_hours"] < 6:
        tips.append("Sleep is below 6 hours - a regular 7-8 hour sleep routine is strongly linked to better mood.")
    if inputs["social_media_hours"] > 5:
        tips.append("Social media use is above 5 hours/day - try screen-free periods, especially before bed.")
    if inputs["exercise_days"] == 0:
        tips.append("No exercise - even 20-30 minutes of walking on 3 days a week can help.")
    if inputs["attendance_pct"] < 70:
        tips.append("Attendance is low - talk to a teacher or advisor early about any difficulties.")
    if inputs["gpa"] < 2.5:
        tips.append("GPA is low - academic support or peer study groups may reduce pressure.")
    if not tips:
        tips.append("Habits look balanced. Keep up the routine and check in with someone you trust if things change.")
    return tips
