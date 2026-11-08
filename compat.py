"""Streamlit version compatibility: `use_container_width=True` became `width="stretch"`.
Usage:  st.button("x", **stretch())"""
import streamlit as st
from packaging.version import InvalidVersion, Version


def stretch():
    try:
        new_api = Version(st.__version__) >= Version("1.50.0")
    except InvalidVersion:
        new_api = True
    return {"width": "stretch"} if new_api else {"use_container_width": True}
