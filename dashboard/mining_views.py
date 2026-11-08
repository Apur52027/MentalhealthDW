"""Risk prediction form + data-mining pages (classification, clustering, association rules)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics.analytics import get_filter_options
from compat import stretch
from dashboard.dashboard import RISK_COLORS, ensure_ready
from mining.association_rules import mine_rules
from mining.classification import load_metrics, predict_risk, risk_advice, train_model
from mining.clustering import run_clustering
from mining.features import CLASSES

DISCLAIMER = ("This is a statistical screening aid built from synthetic demo data. It is NOT a medical "
              "diagnosis. If you or someone you know is struggling, please contact the university "
              "counseling service or a qualified professional. In an emergency in Bangladesh call 999.")


def _fig(fig, height=330):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=45, b=10))
    st.plotly_chart(fig, **stretch())


def _table(df):
    st.dataframe(df, hide_index=True, **stretch())


@st.cache_data(show_spinner=False)
def _clusters(k):
    return run_clustering(k=k)


# =================================================================== prediction
def render_prediction():
    st.header("🔮 Depression Risk Prediction")
    st.write("Enter a student's profile to estimate the risk level (Low / Medium / High).")
    try:
        ensure_ready()
        depts, _ = get_filter_options()
    except Exception as err:
        st.error(f"Could not prepare data: {err}")
        return

    a, b, c = st.columns(3)
    gender = a.selectbox("Gender", ["Male", "Female"])
    age = a.slider("Age", 17, 30, 21)
    department = a.selectbox("Department", depts)
    semester = b.slider("Semester", 1, 12, 4)
    gpa = b.slider("GPA", 0.0, 4.0, 3.0, 0.01)
    attendance = b.slider("Attendance %", 0, 100, 80)
    study = c.slider("Study hours / day", 0.0, 12.0, 3.0, 0.5)
    sleep = c.slider("Sleep hours / night", 3.0, 12.0, 7.0, 0.5)
    exercise = c.slider("Exercise days / week", 0, 7, 2)
    social = c.slider("Social media hours / day", 0.0, 14.0, 4.0, 0.5)

    if st.button("Predict risk", type="primary"):
        inputs = {"gender": gender, "age": age, "department": department, "student_semester": semester,
                  "gpa": gpa, "attendance_pct": attendance, "study_hours": study, "sleep_hours": sleep,
                  "exercise_days": exercise, "social_media_hours": social}
        with st.spinner("Predicting..."):
            res = predict_risk(inputs)
        color = RISK_COLORS[res["label"]]
        st.markdown(f"<h2 style='color:{color}'>Predicted risk: {res['label']}</h2>", unsafe_allow_html=True)
        probs = pd.DataFrame({"Risk": CLASSES, "Probability": [res["probabilities"][c] * 100 for c in CLASSES]})
        _fig(px.bar(probs, x="Risk", y="Probability", text=probs["Probability"].round(1), range_y=[0, 100],
                    color="Risk", color_discrete_map=RISK_COLORS, title="Class probabilities (%)"), 280)
        st.subheader("Suggestions based on the entered habits")
        for tip in risk_advice(inputs):
            st.write(f"- {tip}")
        st.info(DISCLAIMER)


# =================================================================== data mining
def render_mining():
    st.header("⛏️ Data Mining")
    try:
        ensure_ready()
        with st.spinner("Preparing the risk model (first run takes a few seconds)..."):
            metrics = load_metrics()
    except Exception as err:
        st.error(f"Could not prepare mining results: {err}")
        return

    t_cls, t_clu, t_rules = st.tabs(["Classification", "Clustering", "Association Rules"])

    with t_cls:
        st.subheader("Risk-level classification")
        c = st.columns(4)
        c[0].metric("Best model", metrics["best_model"])
        c[1].metric("Test accuracy", metrics["test_accuracy"])
        c[2].metric("Test macro-F1", metrics["test_f1_macro"])
        c[3].metric("Train / test rows", f"{metrics['n_train']} / {metrics['n_test']}")
        st.caption("Split by student (no student appears in both train and test). Scores and counseling are "
                   "excluded from the features to avoid leaking the answer.")
        comp = pd.DataFrame(metrics["comparison"]).T.reset_index().rename(columns={"index": "model"})
        _table(comp)
        a, b = st.columns(2)
        with a:
            cm = pd.DataFrame(metrics["confusion_matrix"], index=metrics["classes"], columns=metrics["classes"])
            _fig(px.imshow(cm, text_auto=True, color_continuous_scale="Greens",
                           labels=dict(x="Predicted", y="Actual"), title="Confusion matrix (test set)"))
        with b:
            fi = pd.DataFrame(metrics["feature_importance"])
            _fig(px.bar(fi.sort_values("importance"), x="importance", y="feature", orientation="h",
                        title="Key factors (permutation importance)", color_discrete_sequence=["#267653"]))
        per = pd.DataFrame(metrics["per_class"]).T.reset_index().rename(columns={"index": "risk level"})
        _table(per)
        if st.button("Retrain model"):
            with st.spinner("Training..."):
                train_model()
            st.rerun()

    with t_clu:
        st.subheader("Student segments (K-Means)")
        auto = st.checkbox("Choose k automatically (best silhouette)", value=False)
        k = None if auto else st.slider("Number of clusters (k)", 2, 6, 3)
        res = _clusters(k)
        st.caption(f"k = {res['k']}. Silhouette score by k: {res['silhouette_by_k']}")
        a, b = st.columns([3, 2])
        with a:
            _fig(px.scatter(res["data"], x="pc1", y="pc2", color="cluster_name", opacity=0.7,
                            title="Clusters (PCA projection)"), 420)
        with b:
            st.write("**Cluster profiles** (averages)")
            prof = res["profile"].drop(columns=["cluster"])
            _table(prof[["cluster_name", "students", "share_pct", "depression_score", "stress_score",
                         "sleep_hours", "social_media_hours", "gpa", "high_risk_pct"]])

    with t_rules:
        st.subheader("Association rules")
        c1, c2, c3, c4 = st.columns(4)
        target = c1.selectbox("Outcome", ["Risk: High", "Risk: Medium", "Risk: Low"])
        sup = c2.slider("Min support", 0.01, 0.20, 0.03, 0.01)
        conf = c3.slider("Min confidence", 0.30, 0.95, 0.40, 0.05)
        lift = c4.slider("Min lift", 1.0, 5.0, 1.2, 0.1)
        rules = mine_rules(min_support=sup, min_confidence=conf, min_lift=lift, target_prefix=target)
        st.caption("support = share of all assessments with the pattern; confidence = share of those with the "
                   "outcome; lift > 1 means the pattern raises the outcome's likelihood.")
        if rules.empty:
            st.info("No rules found - try lowering the thresholds.")
        else:
            _table(rules)
