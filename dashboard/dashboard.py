"""BI dashboard (trends, reports, visual analytics) + warehouse / ETL page."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics.analytics import (correlation_matrix, get_filter_options, get_flat_dataframe,
                                 get_kpis, load_queries, run_query)
from compat import stretch
from etl.load import run_etl
from warehouse.database import DB_PATH, get_connection, table_counts, warehouse_is_loaded

RISK_COLORS = {"Low": "#2E8B57", "Medium": "#F0A500", "High": "#D64545"}
GREEN = ["#267653", "#4B9873", "#174B36", "#8CC9A8"]

STAR_SCHEMA_DOT = """
digraph G {
  rankdir=LR; node [shape=record, style=filled, fillcolor="#EAF4EE", fontname="Helvetica", fontsize=11];
  fact [fillcolor="#FBE3E3", label="{FACT_DEPRESSION|fact_id (PK)\\lstudent_id (FK)\\lacademic_id (FK)\\llifestyle_id (FK)\\lmentalhealth_id (FK)\\ltime_id (FK)\\l|depression_score\\lstress_score\\lanxiety_score\\lrisk_level\\l}"];
  student [label="{DIM_STUDENT|student_id (PK)\\lgender\\lage\\ldepartment\\lsemester\\l}"];
  academic [label="{DIM_ACADEMIC|academic_id (PK)\\lgpa\\lattendance_pct\\lstudy_hours\\l}"];
  lifestyle [label="{DIM_LIFESTYLE|lifestyle_id (PK)\\lsleep_hours\\lexercise_days\\lsocial_media_hours\\l}"];
  mental [label="{DIM_MENTALHEALTH|mentalhealth_id (PK)\\lanxiety_score\\lstress_score\\lcounseling_status\\l}"];
  time [label="{DIM_TIME|time_id (PK)\\ldate\\lmonth\\lsemester\\lyear\\l}"];
  student -> fact; academic -> fact; lifestyle -> fact; mental -> fact; time -> fact;
}
"""


def ensure_ready():
    """Build the warehouse automatically on first use."""
    if not warehouse_is_loaded():
        with st.spinner("Building the data warehouse (first run)..."):
            run_etl()


def _fig(fig, height=330):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=45, b=10))
    st.plotly_chart(fig, **stretch())


def _table(df):
    st.dataframe(df, hide_index=True, **stretch())


def _csv_button(df, label, filename):
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), filename, "text/csv")


def _factor_chart(query, title, dept, year):
    df = run_query(query, dept, year)
    if df.empty:
        return
    _fig(px.bar(df, x="band", y="high_risk_pct", text="high_risk_pct", hover_data=["assessments", "avg_depression"],
                title=title, color_discrete_sequence=["#D64545"]), 300)


# =================================================================== BI dashboard
def render_dashboard():
    st.header("📊 BI Dashboard - Depression Risk Analysis")
    try:
        ensure_ready()
    except Exception as err:
        st.error(f"Could not build the warehouse: {err}")
        return

    depts, years = get_filter_options()
    f1, f2 = st.columns(2)
    dept = f1.selectbox("Department", ["All"] + depts)
    year = f2.selectbox("Year", ["All"] + years)

    k = get_kpis(dept, year)
    if not k:
        st.warning("No data for the selected filters.")
        return
    c = st.columns(6)
    c[0].metric("Students", f"{k['students_assessed']:,}")
    c[1].metric("Assessments", f"{k['assessments']:,}")
    c[2].metric("Avg PHQ-9", k["avg_depression"])
    c[3].metric("Avg Stress (PSS)", k["avg_stress"])
    c[4].metric("High risk", f"{k['high_risk_pct']}%")
    c[5].metric("High-risk w/o counseling", f"{k['high_risk_without_counseling_pct'] or 0}%")
    st.caption("Scores are screening results (PHQ-9 / PSS-10 / GAD-7), not clinical diagnoses.")

    t_over, t_factors, t_students, t_reports = st.tabs(
        ["Trends & Overview", "Risk Factors", "Students & Counseling", "Reports"])

    with t_over:
        a, b = st.columns(2)
        with a:
            df = run_query("risk_distribution", dept, year)
            _fig(px.pie(df, names="risk_level", values="assessments", hole=0.45, title="Risk level distribution",
                        color="risk_level", color_discrete_map=RISK_COLORS))
        with b:
            df = run_query("risk_by_department", dept, year)
            _fig(px.bar(df, x="department", y="high_risk_pct", text="high_risk_pct",
                        hover_data=["assessments", "avg_depression", "avg_stress", "avg_anxiety"],
                        title="High-risk % by department", color_discrete_sequence=["#D64545"]))
        a, b = st.columns(2)
        with a:
            df = run_query("trend_by_period", dept, year)
            _fig(px.line(df, x="assessment_date", y=["avg_depression", "avg_stress", "avg_anxiety"], markers=True,
                         title="Average scores over time", color_discrete_sequence=GREEN))
        with b:
            _fig(px.line(df, x="assessment_date", y="high_risk_pct", markers=True,
                         title="High-risk % over time", color_discrete_sequence=["#D64545"]))
        a, b = st.columns(2)
        with a:
            df = run_query("gender_comparison", dept, year)
            _fig(px.bar(df, x="gender", y=["avg_depression", "avg_stress", "avg_anxiety"], barmode="group",
                        title="Average scores by gender", color_discrete_sequence=GREEN))
        with b:
            df = run_query("semester_level_risk", dept, year)
            _fig(px.bar(df, x="student_semester", y="high_risk_pct", text="high_risk_pct",
                        title="High-risk % by student semester", color_discrete_sequence=["#D64545"]))

    with t_factors:
        st.caption("Share of assessments at HIGH risk within each band. Associations, not proof of cause.")
        a, b = st.columns(2)
        with a:
            _factor_chart("factor_sleep", "Sleep duration", dept, year)
            _factor_chart("factor_exercise", "Exercise frequency", dept, year)
            _factor_chart("factor_attendance", "Attendance", dept, year)
        with b:
            _factor_chart("factor_social_media", "Daily social media use", dept, year)
            _factor_chart("factor_gpa", "GPA", dept, year)
        corr = correlation_matrix(dept, year)
        if not corr.empty:
            _fig(px.imshow(corr, text_auto=True, zmin=-1, zmax=1, color_continuous_scale="RdBu_r",
                           title="Correlation matrix (scores vs. habits)"), 520)

    with t_students:
        st.subheader("Counseling coverage by risk level")
        cov = run_query("counseling_coverage", dept, year)
        _fig(px.bar(cov, x="risk_level", y="assessments", color="counseling_status", barmode="stack",
                    color_discrete_sequence=["#BBBBBB", "#8CC9A8", "#267653"]))
        st.subheader("⚠️ High-risk students (latest assessment, anonymised IDs)")
        st.caption("Sorted so that students WITHOUT counseling appear first - candidates for early outreach.")
        risk = run_query("at_risk_students", dept, year)
        _table(risk)
        if not risk.empty:
            _csv_button(risk, "Download list (CSV / Excel)", "high_risk_students.csv")

    with t_reports:
        st.subheader("Summary reports")
        names = [n for n in load_queries() if n != "at_risk_students"]
        choice = st.selectbox("Report", names)
        rep = run_query(choice, dept, year)
        _table(rep)
        _csv_button(rep, "Download this report (CSV)", f"{choice}.csv")
        st.subheader("Full flat dataset")
        flat = get_flat_dataframe(dept, year)
        st.caption(f"{len(flat):,} rows from vw_depression_flat")
        _csv_button(flat, "Download full dataset (CSV)", "depression_flat.csv")


# =================================================================== warehouse page
def render_warehouse():
    st.header("🏛️ Data Warehouse & ETL")
    st.subheader("Star schema")
    try:
        st.graphviz_chart(STAR_SCHEMA_DOT)
    except Exception:
        st.code(STAR_SCHEMA_DOT, language="text")
    st.caption("Grain: one row in FACT_DEPRESSION = one student at one assessment date.")

    try:
        ensure_ready()
    except Exception as err:
        st.error(f"Could not build the warehouse: {err}")
        return

    st.subheader("Row counts")
    counts = table_counts()
    _table(pd.DataFrame({"table": list(counts), "rows": list(counts.values())}))

    st.subheader("Preview a table")
    table = st.selectbox("Table / view", list(counts) + ["vw_depression_flat"])
    with get_connection(readonly=True) as conn:
        _table(pd.read_sql_query(f"SELECT * FROM {table} LIMIT 20", conn))

    st.subheader("ETL")
    st.write("Sources → **Extract** (6 CSV files) → **Transform** (clean, integrate, derive bands & risk level) "
             "→ **Load** (dimensions, then fact).")
    if st.button("🔄 Re-run ETL and retrain model"):
        try:
            with st.spinner("Running ETL..."):
                st.session_state.etl_report = run_etl()
            with st.spinner("Retraining risk model..."):
                from mining.classification import train_model
                train_model()
            st.cache_data.clear()
            st.success("Done.")
        except Exception as err:
            st.error(f"ETL failed: {err}")
    if st.session_state.get("etl_report"):
        st.json({k: v for k, v in st.session_state.etl_report.items() if k != "table_counts"})
    st.caption(f"Database file: {DB_PATH.name} (SQLite). `warehouse/schema.sql` has the PostgreSQL/MySQL DDL.")
