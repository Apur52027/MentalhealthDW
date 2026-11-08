"""Student Mental Health Data Warehouse for Depression Risk Analysis and Business Intelligence.
Run:  streamlit run app.py"""
import streamlit as st

from dashboard.assistant import render_assistant
from dashboard.dashboard import render_dashboard, render_warehouse
from dashboard.mining_views import render_mining, render_prediction

st.set_page_config(page_title="Student Mental Health DW", page_icon="🧠", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #F6FAF8; }
.hero { background: linear-gradient(120deg, #1B3A8A 0%, #5B2A9B 100%); color: #fff; padding: 28px 32px;
        border-radius: 16px; margin-bottom: 18px; }
.hero h1 { color: #fff !important; font-size: 30px; margin: 0 0 6px 0; }
.hero p { color: #E8E6F8 !important; margin: 0; font-size: 16px; }
.card { background: #fff; border-radius: 12px; padding: 16px 18px; border: 1px solid #E3E8E6; height: 100%; }
</style>
""", unsafe_allow_html=True)

PAGES = ["Home", "BI Dashboard", "Risk Prediction", "Data Mining", "Data Assistant", "Warehouse & ETL"]
st.sidebar.title("🧠 Mental Health DW")
page = st.sidebar.radio("Navigate", PAGES)
st.sidebar.divider()
st.sidebar.caption("**Student:** Sweety Akter Sima (2002008)\n\n**Course:** CSE 525\n\n"
                   "**Submitted to:** Dr. Md. Delowar Hossain, Professor, Dept. of CSE, HSTU")
st.sidebar.warning("Demo uses **synthetic data**. Scores are screening results, not diagnoses. "
                   "Emergency in Bangladesh: **999**.")

ARCHITECTURE_DOT = """
digraph G {
  rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#EAF4EE", fontname="Helvetica", fontsize=11];
  src [label="Data Sources\\n- Student Information\\n- Academic Records\\n- Attendance\\n- Lifestyle Survey\\n- Mental Health Survey\\n- Counseling Records"];
  etl [label="ETL\\nExtract -> Transform -> Load"];
  dw [shape=cylinder, fillcolor="#FFE9CC", label="Student Mental Health\\nData Warehouse"];
  dm [label="Data Mining\\nClassification\\nClustering\\nAssociation Rules"];
  bi [label="BI Dashboard\\nTrends - Reports - Visuals"];
  bot [fillcolor="#E4E0FA", label="LLM Data Assistant\\n(text-to-SQL)"];
  dss [fillcolor="#DDE8FA", label="Decision Support\\nRisk Identification\\nUniversity Management"];
  src -> etl -> dw; dw -> dm; dw -> bi; dw -> bot; dm -> dss; bi -> dss; bot -> dss;
}
"""

if page == "Home":
    st.markdown("""
    <div class="hero">
      <h1>Student Mental Health Data Warehouse</h1>
      <p>Depression Risk Analysis and Business Intelligence - integrating academic, lifestyle and mental-health
      data to identify students who may need support early.</p>
    </div>""", unsafe_allow_html=True)

    a, b, c = st.columns(3)
    a.markdown("<div class='card'><b>🎯 Objectives</b><ul>"
               "<li>Design a Student Mental Health Data Warehouse</li>"
               "<li>Integrate academic, lifestyle and mental-health data using ETL</li>"
               "<li>Analyze factors associated with student depression</li>"
               "<li>Predict depression risk with data mining</li>"
               "<li>Provide a BI dashboard for decision support</li></ul></div>", unsafe_allow_html=True)
    b.markdown("<div class='card'><b>✅ What you can do here</b><ul>"
               "<li><b>BI Dashboard</b> - trends, factors, at-risk students, reports</li>"
               "<li><b>Risk Prediction</b> - Low / Medium / High for a profile</li>"
               "<li><b>Data Mining</b> - classification, clustering, association rules</li>"
               "<li><b>Data Assistant</b> - ask questions to an LLM chatbot</li>"
               "<li><b>Warehouse &amp; ETL</b> - star schema, row counts, re-run ETL</li></ul></div>",
               unsafe_allow_html=True)
    c.markdown("<div class='card'><b>🛠️ Tools</b><ul>"
               "<li>Database: SQLite (schema.sql for PostgreSQL / MySQL)</li>"
               "<li>ETL: SQL + Python (Pandas)</li>"
               "<li>Data mining: Python (scikit-learn)</li>"
               "<li>Visualization: Streamlit + Plotly</li>"
               "<li>Modeling: Star schema</li>"
               "<li>Chatbot: Groq LLM (read-only text-to-SQL)</li></ul></div>", unsafe_allow_html=True)

    st.subheader("System architecture")
    try:
        st.graphviz_chart(ARCHITECTURE_DOT)
    except Exception:
        st.code(ARCHITECTURE_DOT, language="text")

elif page == "BI Dashboard":
    render_dashboard()
elif page == "Risk Prediction":
    render_prediction()
elif page == "Data Mining":
    render_mining()
elif page == "Data Assistant":
    render_assistant()
else:
    render_warehouse()
