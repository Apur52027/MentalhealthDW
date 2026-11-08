"""Groq LLM factory (key from Streamlit secrets or .env)."""
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


def _secret(name):
    try:
        import streamlit as st
        value = st.secrets.get(name)
        if value:
            return value
    except Exception:
        pass
    return None


def get_api_key():
    return _secret("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")


def get_model_name():
    return _secret("GROQ_MODEL") or os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def get_llm(temperature=0.2):
    key = get_api_key()
    if not key:
        raise ValueError("GROQ_API_KEY missing. Add it to .env or Streamlit secrets.")
    return ChatGroq(model=get_model_name(), api_key=key, temperature=temperature,
                    timeout=40, max_retries=2)
