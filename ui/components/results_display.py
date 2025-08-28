import streamlit as st
from typing import Dict, Any, Optional, List

LABEL_COLORS = {
    "Green": "🟢",
    "Amber": "🟠",
    "Ineligible": "🔴",
    "Red": "🔴", # TODO: Remove one depending on what backend sets it as
}

def _render_rule_path(rule_path: List[Dict[str, Any]]):
    for step in rule_path:
        status = "✅" if step.get("passed") else "❌"
        st.write(f"- {status} **{step.get('clause_id', 'N/A')}** — `{step.get('test','')}`")

def _render_evidence(evidence: List[Dict[str, Any]]):
    for ev in evidence:
        src = ev.get("source", "Source")
        url = ev.get("url")
        if url:
            st.write(f"- {src}: {url}")
        else:
            st.write(f"- {src}")

def show_results(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Renders results and returns a dict of answers if missing fields exist and are submitted.
    """
    decision = result.get("decision", {})
    label = decision.get("label", "Unknown")
    chip = LABEL_COLORS.get(label, "ℹ️")

    st.subheader("Classification Result")
    st.markdown(f"### {chip} **{label}**")

    st.markdown("**Explanation**")
    st.write(result.get("explanation", ""))

    with st.expander("Rule Path & Evidence", expanded=False):
        rule_path = decision.get("rule_path", [])
        if rule_path:
            st.markdown("**Applied Criteria**")
            _render_rule_path(rule_path)
        evidence = result.get("evidence", [])
        if evidence:
            st.markdown("**Evidence / Citations**")
            _render_evidence(evidence)

    missing = result.get("missing_fields") or []
    if missing:
        st.warning("More information is needed to finalize classification.")
        with st.form("missing_form", clear_on_submit=False):
            answers = {}
            for f in missing:
                # try to guess numeric vs string
                val = st.text_input(f"Provide value for `{f}`")
                answers[f] = _coerce(val)
            submitted = st.form_submit_button("Submit missing info", use_container_width=True)
        if submitted:
            return answers

    return None

def _coerce(val: str):
    try:
        if "." in val:
            return float(val)
        return int(val)
    except Exception:
        if val.lower() in ("true", "false"):
            return val.lower() == "true"
        return val
