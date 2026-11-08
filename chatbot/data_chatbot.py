"""Decision-support chatbot for the Student Mental Health Data Warehouse.

Ask in English / Bangla / Banglish:
    "Which department has the highest high-risk percentage?"
    "ঘুম কম হলে ঝুঁকি কতটা বাড়ে?"
    "Show high-risk students who never got counseling"

Pipeline
  1. Safety check (a person in distress gets a supportive message first).
  2. LLM writes ONE read-only SQL query for the warehouse; it is validated, run on a
     read-only connection with a SQLite authorizer, and capped at 200 rows.
  3. LLM explains the result in the user's language, with data-mining insights
     (key factors, association rules) as extra context. Never invents numbers.
  4. Conceptual questions (PHQ-9, risk levels, what the model does) get a grounded answer.
  5. No API key / offline? A rule-based fallback runs the built-in BI queries.
Privacy: the warehouse holds anonymised student IDs only (no names or contact details).
"""
import json
import re
import sqlite3
from functools import lru_cache

import pandas as pd

from analytics.analytics import run_query
from warehouse.database import ALLOWED_OBJECTS, get_connection

MAX_ROWS = 200

SCHEMA_DESCRIPTION = """
SQLite star schema. PREFER the flat VIEW vw_depression_flat (one row = one student at one assessment):

vw_depression_flat(
  fact_id, student_id (anonymised, e.g. 'S2001'), gender ('Male'|'Female'|'Other'), age,
  department ('CSE','EEE','BBA','English','Agriculture','Law'), student_semester (1-12),
  assessment_date (YYYY-MM-DD), month, month_name, term ('Spring'|'Fall'), year,
  gpa (0-4), attendance_pct (0-100), study_hours (per day), gpa_band ('Below 2.5','2.5-3.19','3.2+'),
  attendance_band ('<60%','60-79%','80%+'),
  sleep_hours, exercise_days (0-7 per week), social_media_hours (per day),
  sleep_band ('Short (<6h)','Normal (6-8h)','Long (>8h)'),
  exercise_band ('None','Occasional (1-2 days)','Regular (3+ days)'),
  social_media_band ('<3h','3-5h','>5h'),
  counseling_status ('None','Occasional','Regular'),
  anxiety_level ('Minimal','Mild','Moderate','Severe'), stress_level ('Low','Moderate','High'),
  depression_score (PHQ-9, 0-27), stress_score (PSS-10, 0-40), anxiety_score (GAD-7, 0-21),
  risk_level ('Low' PHQ-9<10, 'Medium' 10-14, 'High' >=15)
)
Underlying tables: fact_depression, dim_student, dim_academic, dim_lifestyle, dim_mentalhealth, dim_time.

Notes: High-risk % = 100.0*SUM(CASE WHEN risk_level='High' THEN 1 ELSE 0 END)/COUNT(*).
"At the latest assessment" means assessment_date = (SELECT MAX(assessment_date) FROM vw_depression_flat v2 WHERE v2.student_id = v.student_id).
Scores are screening scores, not diagnoses.
"""

SQL_SYSTEM_PROMPT = f"""You are a careful SQL analyst for a university mental-health data warehouse.
{SCHEMA_DESCRIPTION}
RULES:
- Write ONE read-only SQLite SELECT (or WITH ... SELECT). Never modify data.
- Use only the objects above; do not invent columns.
- Use ROUND(..., 2) for averages/percentages. Add ORDER BY and LIMIT (max {MAX_ROWS}) where sensible.
- For group comparisons include the number of assessments in the output.
- If the question is conceptual (definitions, how the model works, advice) or cannot be answered
  from this data, return {{"sql": "", "reason": "conceptual"}}.
Return ONLY JSON: {{"sql": "SELECT ...", "reason": ""}}"""

ANSWER_SYSTEM_PROMPT = """You are a decision-support assistant for university management, helping them
understand student mental-health patterns from a data warehouse.
You get the question, the SQL that was run, its result and (optionally) data-mining insights.
- Reply in the SAME language/script as the question (Bangla script -> Bangla, Banglish -> Banglish, English -> English).
- Be concise (3-6 sentences): state the key numbers, the main pattern, and one practical implication
  for management when natural. Never invent numbers that are not in the result or insights.
- Patterns are statistical associations, NOT proof of cause. Scores are screening tools, not diagnoses.
- Never try to identify individual students; IDs are anonymised.
- If the result is empty, say no matching data was found."""

GENERAL_SYSTEM_PROMPT = """You are a decision-support assistant for a Student Mental Health Data Warehouse project
(PHQ-9 depression, PSS-10 stress, GAD-7 anxiety screening; star schema; classification, clustering and
association-rule mining; BI dashboard). Answer the conceptual question clearly in the user's language/script.
Use the project context below when relevant. Risk levels: Low = PHQ-9 0-9, Medium = 10-14, High = 15-27.
Scores are screening tools, not diagnoses. Do not give medical treatment advice; for support, recommend the
university counseling service or a qualified professional. Keep it concise (3-6 sentences).

PROJECT CONTEXT:
{context}"""

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|reindex|"
    r"truncate|grant|revoke|load_extension)\b", re.I)

# ---------------------------------------------------------------- safety
_CRISIS_EN = re.compile(
    r"\b(i|i'm|im|i am)\b[^.?!]{0,40}\b(want to die|wanna die|kill myself|end my life|hurt myself|"
    r"suicidal|suicide|don't want to live|do not want to live)\b", re.I)
_CRISIS_BN = re.compile(r"(মরে যেতে চাই|আত্মহত্যা করতে চাই|আত্মহত্যা করব|বাঁচতে চাই না|নিজেকে শেষ করে|নিজের ক্ষতি করতে চাই)")

CRISIS_EN = ("I'm really sorry you're going through this, and I'm glad you said it. Your safety matters most "
             "right now. Please don't stay alone - reach out to someone you trust, or your university counseling "
             "service. If you might act on these thoughts or are in immediate danger, call Bangladesh emergency "
             "services at 999 or go to the nearest hospital emergency department. Are you safe right now?")
CRISIS_BN = ("তুমি যে কষ্টের মধ্য দিয়ে যাচ্ছ, সেটা আমাকে বলেছ বলে ধন্যবাদ। তোমার নিরাপত্তা এখন সবচেয়ে গুরুত্বপূর্ণ। "
             "দয়া করে একা থেকো না - বিশ্বাসযোগ্য কোনো মানুষ বা বিশ্ববিদ্যালয়ের কাউন্সেলিং সেবার সঙ্গে এখনই কথা বলো। "
             "যদি মনে হয় তুমি এখনই নিজেকে আঘাত করতে পারো, বাংলাদেশে ৯৯৯-এ কল করো অথবা নিকটস্থ হাসপাতালের "
             "জরুরি বিভাগে যাও। তুমি কি এই মুহূর্তে নিরাপদে আছ?")


def crisis_response(text):
    """Return a supportive message if the person talks about harming themselves, else None."""
    if _CRISIS_BN.search(text):
        return CRISIS_BN
    if _CRISIS_EN.search(text):
        return CRISIS_BN if re.search(r"[\u0980-\u09FF]", text) else CRISIS_EN
    return None


# ---------------------------------------------------------------- SQL safety
def validate_sql(sql):
    sql = (sql or "").strip().rstrip(";").strip()
    if not sql:
        raise ValueError("Empty SQL.")
    if ";" in sql:
        raise ValueError("Only a single statement is allowed.")
    if "--" in sql or "/*" in sql:
        raise ValueError("SQL comments are not allowed.")
    if not re.match(r"^(select|with)\b", sql, re.I):
        raise ValueError("Only SELECT queries are allowed.")
    if FORBIDDEN.search(sql):
        raise ValueError("Query contains a forbidden keyword.")
    return sql


def _authorizer(action, arg1, arg2, dbname, source):
    ok_actions = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_FUNCTION, getattr(sqlite3, "SQLITE_RECURSIVE", 33)}
    if action in ok_actions:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ and arg1 in ALLOWED_OBJECTS:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def execute_readonly(sql):
    sql = validate_sql(sql)
    wrapped = f"SELECT * FROM ({sql}) LIMIT {MAX_ROWS}"
    with get_connection(readonly=True) as conn:
        conn.set_authorizer(_authorizer)
        try:
            return sql, pd.read_sql_query(wrapped, conn)
        finally:
            conn.set_authorizer(None)


# ---------------------------------------------------------------- mining context
@lru_cache(maxsize=1)
def mining_context():
    """Short text with the model's key factors and top association rules."""
    parts = []
    try:
        from mining.classification import METRICS_PATH
        if METRICS_PATH.exists():
            m = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
            top = ", ".join(f"{f['feature']} ({f['importance']})" for f in m["feature_importance"][:5])
            parts.append(f"Risk model: {m['best_model']}, test accuracy {m['test_accuracy']}, macro-F1 "
                         f"{m['test_f1_macro']}. Most influential factors (permutation importance): {top}.")
    except Exception:
        pass
    try:
        from mining.association_rules import mine_rules
        rules = mine_rules().head(3)
        for r in rules.itertuples(index=False):
            parts.append(f"Association rule: IF {r[0]} THEN {r[1]} (confidence {r[3]}, lift {r[4]}, {r[5]} assessments).")
    except Exception:
        pass
    return "\n".join(parts) or "No data-mining results available yet."


# ---------------------------------------------------------------- LLM helpers (lazy import)
def _llm_text(system, human, temperature=0.1):
    from langchain_core.messages import SystemMessage, HumanMessage
    from chatbot.llm import get_llm
    resp = get_llm(temperature=temperature).invoke([SystemMessage(content=system), HumanMessage(content=human)])
    content = resp.content
    if isinstance(content, list):
        content = "".join(i.get("text", "") if isinstance(i, dict) else str(i) for i in content)
    return str(content).strip()


def _parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    a, b = text.find("{"), text.rfind("}")
    if a == -1 or b == -1:
        raise ValueError("LLM did not return JSON.")
    return json.loads(text[a:b + 1])


def _history_text(history, limit=4):
    return "\n".join(f"User: {m.get('content', '')}" for m in (history or [])[-limit * 2:]
                     if m.get("role") == "user")


def generate_sql(question, history=None, error_hint=""):
    prompt = f"Earlier user questions (context):\n{_history_text(history)}\n\nQuestion: {question}"
    if error_hint:
        prompt += f"\n\nYour previous SQL failed with: {error_hint}\nFix it."
    data = _parse_json(_llm_text(SQL_SYSTEM_PROMPT, prompt))
    return (data.get("sql") or "").strip(), data.get("reason", "")


def explain_result(question, sql, df):
    return _llm_text(
        ANSWER_SYSTEM_PROMPT,
        f"Question: {question}\n\nSQL:\n{sql}\n\nResult ({len(df)} rows, first 25):\n{df.head(25).to_csv(index=False)}"
        f"\n\nData-mining insights:\n{mining_context()}", temperature=0.3)


def answer_general(question, history=None):
    return _llm_text(GENERAL_SYSTEM_PROMPT.format(context=mining_context()),
                     f"Earlier user questions:\n{_history_text(history)}\n\nQuestion: {question}", temperature=0.3)


# ---------------------------------------------------------------- rule-based fallback
INTENTS = [
    ("at_risk_students", ["at risk", "at-risk", "high risk student", "high-risk student", "ঝুঁকিতে", "ঝুঁকিপূর্ণ"]),
    ("counseling_coverage", ["counsel", "কাউন্সেলিং"]),
    ("key_factors", ["factor", "cause", "why", "reason", "important", "কারণ", "ফ্যাক্টর"]),
    ("factor_sleep", ["sleep", "ঘুম"]),
    ("factor_social_media", ["social media", "facebook", "screen", "ফেসবুক", "সোশ্যাল"]),
    ("factor_exercise", ["exercise", "workout", "ব্যায়াম"]),
    ("factor_gpa", ["gpa", "cgpa", "result", "grade", "রেজাল্ট"]),
    ("factor_attendance", ["attendance", "উপস্থিতি"]),
    ("gender_comparison", ["gender", "male", "female", "boys", "girls", "ছেলে", "মেয়ে"]),
    ("risk_by_department", ["department", "dept", "বিভাগ", "cse", "eee", "bba", "english", "agriculture", "law"]),
    ("semester_level_risk", ["semester", "year of study", "সেমিস্টার"]),
    ("trend_by_period", ["trend", "over time", "period", "change", "ট্রেন্ড"]),
    ("risk_distribution", ["distribution", "how many", "count", "কতজন", "risk level"]),
]


def rule_based_answer(question):
    q = question.lower()
    name = next((n for n, words in INTENTS if any(w in q for w in words)), "kpi_summary")
    is_bn = bool(re.search(r"[\u0980-\u09FF]", question))

    if name == "key_factors":
        from mining.classification import load_metrics
        df = pd.DataFrame(load_metrics()["feature_importance"])
        sql = "-- model feature importance (permutation importance)"
    else:
        dept = next((d for d in ("CSE", "EEE", "BBA", "English", "Agriculture", "Law")
                     if re.search(rf"\b{d.lower()}\b", q)), None)
        year = next((int(y) for y in ("2024", "2025") if y in q), None)
        df = run_query(name, dept=dept, year=year)
        sql = f"-- predefined query: {name}"

    text = (f"'{name}' বিশ্লেষণের ফলাফল ({len(df)}টি সারি)। (AI মডেল বন্ধ থাকায় নিয়মভিত্তিক উত্তর দেওয়া হয়েছে।)"
            if is_bn else f"Here is the '{name}' result ({len(df)} rows). "
                          "(Rule-based answer - the AI model is not available right now.)")
    return text, sql, df


# ---------------------------------------------------------------- public API
def _result(answer, sql="", data=None, method="llm", error=None):
    return {"answer": answer, "sql": sql, "data": data, "method": method, "error": error}


def ask_assistant(question, history=None):
    """Return dict(answer, sql, data, method, error)."""
    question = (question or "").strip()
    if not question:
        return _result("Please ask a question.", method="none")

    safe = crisis_response(question)
    if safe:
        return _result(safe, method="safety")

    error_hint, last_error = "", None
    for _ in range(2):
        try:
            sql, reason = generate_sql(question, history, error_hint)
            if not sql:                                   # conceptual question
                return _result(answer_general(question, history))
            sql, df = execute_readonly(sql)
            try:
                answer = explain_result(question, sql, df)
            except Exception:
                answer = f"The query returned {len(df)} rows."
            return _result(answer, sql, df)
        except (ValueError, sqlite3.Error, pd.errors.DatabaseError) as err:
            error_hint, last_error = str(err), str(err)   # let the LLM fix its SQL once
        except Exception as err:                          # no key / offline / import error
            last_error = str(err)
            break

    try:
        answer, sql, df = rule_based_answer(question)
        return _result(answer, sql, df, "rule-based", last_error)
    except Exception as err:
        return _result("Sorry, I could not answer that right now.", method="none", error=str(err))
