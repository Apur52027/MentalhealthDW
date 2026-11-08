"""LLM Data Assistant page."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from chatbot.data_chatbot import ask_assistant
from compat import stretch
from dashboard.dashboard import ensure_ready

EXAMPLES = [
    "Which department has the highest high-risk percentage?",
    "How does sleep duration affect risk?",
    "Show high-risk students with no counseling",
    "ঘুম কম হলে ঝুঁকি কতটা বাড়ে?",
]


def _show_data(df):
    st.dataframe(df, hide_index=True, **stretch())
    if df is not None and 2 <= df.shape[1] and 0 < len(df) <= 30:
        cols = list(df.columns)
        if not pd.api.types.is_numeric_dtype(df[cols[0]]) and pd.api.types.is_numeric_dtype(df[cols[1]]):
            fig = px.bar(df, x=cols[0], y=cols[1], color_discrete_sequence=["#267653"])
            fig.update_layout(height=300, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, **stretch())


def render_assistant():
    st.header("🤖 Data Assistant (LLM)")
    st.caption("Ask about the mental-health data in English, Bangla or Banglish. The assistant writes a safe "
               "read-only SQL query, runs it on the warehouse and explains the result. "
               "Student IDs are anonymised; patterns are associations, not causes.")
    try:
        ensure_ready()
    except Exception as err:
        st.error(f"Could not build the warehouse: {err}")
        return

    st.session_state.setdefault("mh_chat", [])

    cols = st.columns(len(EXAMPLES))
    for col, example in zip(cols, EXAMPLES):
        if col.button(example, key=f"ex_{example}", **stretch()):
            st.session_state.pending_q = example
    if st.button("Clear chat", key="mh_clear"):
        st.session_state.mh_chat = []
        st.rerun()

    for msg in st.session_state.mh_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sql"):
                with st.expander("SQL used"):
                    st.code(msg["sql"], language="sql")
            if msg.get("data") is not None:
                _show_data(msg["data"])

    question = st.chat_input("Ask a question about student mental health data...")
    if not question:
        question = st.session_state.pop("pending_q", None)
    if question:
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                res = ask_assistant(question, st.session_state.mh_chat)
            st.markdown(res["answer"])
            if res["sql"]:
                with st.expander("SQL used"):
                    st.code(res["sql"], language="sql")
            if res["data"] is not None:
                _show_data(res["data"])
            if res["method"] == "rule-based" and res["error"]:
                st.caption(f"AI model unavailable ({res['error'][:80]}). Using built-in answers.")
        st.session_state.mh_chat.append({"role": "user", "content": question})
        st.session_state.mh_chat.append({"role": "assistant", "content": res["answer"],
                                         "sql": res["sql"], "data": res["data"]})
