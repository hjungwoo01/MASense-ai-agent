import streamlit as st
from typing import Dict, Any, List, Optional

INTRO_MD = """
### 👋 Welcome to the Sustainability Compliance Assistant

This agent helps you classify your financial actions and disclosures under the **MAS Singapore-Asia Taxonomy**  
using the **traffic-light system**: **Green / Amber / Ineligible**. It also explains the rationale with citations and suggests next steps.

#### What you can do here
1. **Upload a PDF** (start with your latest **Sustainability/ESG Report**).  
   You can also add: project memos, green loan frameworks, term sheets, or portfolio holdings.
2. **Chat in plain English** to tell us your goals and context (e.g., *"We plan to refinance a 50MW solar farm in SG"*).
3. The agent classifies the activity and explains **why** (with taxonomy clause references),  
   and tells you what **data is missing** if any.

#### If you're unsure what to upload
- Start with your **Sustainability Report (PDF)** or **project/loan document** that covers:  
  - Sector & activity (e.g., Energy → Solar PV; Buildings → New Construction)  
  - Key metrics (e.g., **gCO₂e/kWh**, capture rate %, EPC certifications, timelines)  
  - Any **transition plan** details (targets, 2030 deadlines)
"""

TIPS_MD = """
**Good to have:**  
- Emissions intensity (Scope 1/2 relevant metrics), commissioning / retirement years  
- Evidence of DNSH (e.g., flood risk adaptation) and Minimum Social Safeguards (e.g., labor policies)  
- For loans: KPI/SPT details (for SLL) or Use-of-Proceeds (for Green Loans)
"""

def sidebar_docs(docs: List[Dict[str, str]]):
    st.sidebar.subheader("📎 Uploaded Documents")
    if not docs:
        st.sidebar.info("No documents uploaded yet.")
    else:
        for d in docs:
            st.sidebar.write(f"• {d.get('name','(unnamed)')} — `{d.get('doc_id','')}`")

def intro_block(show_tips: bool = True):
    with st.container(border=True):
        st.markdown(INTRO_MD)
        if show_tips:
            st.markdown(TIPS_MD)
        st.caption("We’ll only use uploaded files for this session to help classify and explain your case.")

def render_missing_fields(missing_fields: List[str]) -> Optional[Dict[str, Any]]:
    if not missing_fields:
        return None
    st.warning("To proceed, please provide the following:")
    with st.form("missing_fields_form"):
        answers = {}
        for f in missing_fields:
            val = st.text_input(f"**{f}**")
            answers[f] = _coerce(val)
        submitted = st.form_submit_button("Submit details")
        if submitted:
            return answers
    return None

def _coerce(val: str):
    try:
        if "." in val:
            return float(val)
        return int(val)
    except Exception:
        if val.strip().lower() in ("true", "false"):
            return val.strip().lower() == "true"
        return val
