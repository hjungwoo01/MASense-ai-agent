import streamlit as st
from typing import List, Dict, Any

def init_state():
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []  # type: List[Dict[str, Any]]
    if "docs" not in st.session_state:
        st.session_state.docs = []  # type: List[Dict[str, str]]
    if "intro_dismissed" not in st.session_state:
        st.session_state.intro_dismissed = False
    if "company_profile" not in st.session_state:
        st.session_state.company_profile = {}
    if "pending_missing_fields" not in st.session_state:
        st.session_state.pending_missing_fields = []
    return st.session_state
