import streamlit as st
import hashlib

from utils.session_state import init_state
from utils.api_client import start_session, upload_document, chat_message, answer_missing
from components.chat_sections import intro_block, sidebar_docs
from utils.rules_catalog import load_rules, sectors, activities_for_sector

st.set_page_config(page_title="Sustainability Compliance Assistant", page_icon="✅", layout="wide")
state = init_state()

RULES = load_rules()
all_sectors = sectors(RULES)

# ---------- sidebar: upload docs & session ----------
with st.sidebar:
    st.title("Compliance Assistant")

    # ensure required keys exist
    if "docs" not in state: state.docs = []
    if "doc_hashes" not in state: state.doc_hashes = set()

    if not state.session_id:
        if st.button("Start new session", use_container_width=True):
            resp = start_session()
            state.session_id = resp["session_id"]
            state.docs = []
            state.doc_hashes = set()
            st.rerun()

    uploaded = st.file_uploader(
        "Upload PDF(s) to analyze",
        type=["pdf"],
        accept_multiple_files=True,
        key="uploader",
        help="Files are uploaded once per session. New chats will reuse them."
    )

    if uploaded:
        if not state.session_id:
            st.warning("Click **Start new session** first.")
        else:
            new_count = 0
            for uf in uploaded:
                data = uf.getvalue()
                sha = hashlib.sha256(data).hexdigest()
                if sha in state.doc_hashes:
                    # already uploaded this exact content; skip
                    continue
                with st.spinner(f"Uploading {uf.name}…"):
                    resp = upload_document(state.session_id, uf.name, data, kind="sustainability_report")
                state.doc_hashes.add(sha)
                state.docs.append({
                    "doc_id": resp.get("doc_id", "doc-mock"),
                    "name": uf.name
                })
                new_count += 1
            if new_count:
                st.success(f"Uploaded {new_count} new file(s).")
            else:
                st.info("No new files detected (duplicates skipped).")

    sidebar_docs(state.docs)

    if st.button("Reset session", use_container_width=True):
        # clear everything including file uploader widget state
        for key in ["session_id","chat_history","docs","doc_hashes","intro_dismissed","company_profile","pending_missing_fields","_prefill","uploader"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# ---------- main area ----------
st.title("Sustainability Compliance (MAS Singapore-Asia Taxonomy)")
st.caption("Green • Amber • Ineligible — with rule-level explanations and next steps")

if not state.intro_dismissed:
    intro_block()

    with st.expander("Provide optional company/context hints", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            sector = st.selectbox("Sector", options=["(select)"] + all_sectors, index=0)
        with c2:
            options = activities_for_sector(RULES, sector) if sector and sector != "(select)" else []
            activity = st.selectbox("Activity", options=["(select)"] + options, index=0)

        jurisdiction = st.text_input("Jurisdiction / Market", value=state.company_profile.get("jurisdiction",""))
        size = st.text_input("Company / Project size (e.g., 50MW, 100k sqm)")

        st.caption("Hints help narrow retrieval & rules. You can leave them blank.")
        if st.button("Save hints"):
            state.company_profile = {
                "sector": None if sector in ("", "(select)") else sector,
                "activity": None if activity in ("", "(select)") else activity,
                "jurisdiction": jurisdiction or None,
                "size": size or None
            }
            st.success("Saved.")

    if st.button("Let's begin!"):
        state.intro_dismissed = True
        if not state.session_id:
            resp = start_session()
            state.session_id = resp["session_id"]
        st.rerun()

# Chat area
if not state.session_id:
    st.info("Click **Let’s Begin** to get started, or use **Start new session** on the left.")
else:
    # Suggested prompts
    with st.container(border=True):
        st.write("**Try one of these to start:**")
        cols = st.columns(3)
        suggestions = [
            "Scan the uploaded report and summarize our taxonomy-relevant activities.",
            "We plan to finance a 50MW solar PV project in Singapore. Classify and explain.",
            "Evaluate if our gas plant retrofit with 90% CCS could be Green or Transition."
        ]
        for i, s in enumerate(suggestions):
            if cols[i].button(s, use_container_width=True, key=f"suggest_{i}"):
                st.session_state._prefill = s

    # Conversation history
    for msg in state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input(
        placeholder="Ask a question or describe your action… e.g., 'We want to issue a green loan for our rooftop solar.'",
        key="user_input",
    )
    if "_prefill" in st.session_state:
        user_input = st.session_state._prefill
        del st.session_state._prefill

    if user_input:
        # show user msg immediately
        state.chat_history.append({"role":"user","content":user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # prepare doc_ids so backend can use already-uploaded docs
        doc_ids = [d["doc_id"] for d in state.docs]

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                # utils.api_client.chat_message may or may not accept doc_ids.
                # Try with doc_ids first; if TypeError, call without.
                try:
                    resp = chat_message(state.session_id, user_input, state.company_profile, doc_ids=doc_ids)
                except TypeError:
                    resp = chat_message(state.session_id, user_input, state.company_profile)

                assistant_text = resp.get("assistant",{}).get("text","(no response)")
                st.markdown(assistant_text)

                # pending follow-ups
                state.pending_missing_fields = resp.get("missing_fields", []) or []

                # compact decision chip
                decision = resp.get("decision")
                if decision and "label" in decision:
                    label = decision["label"]
                    chip = {"Green":"🟢","Amber":"🟠","Ineligible":"🔴","Red":"🔴"}.get(label,"ℹ️")
                    st.markdown(f"**Decision:** {chip} **#{label}**" if label in ("Green","Amber","Ineligible","Red") else f"**Decision:** {chip} {label}")
                    if decision.get("rule_path"):
                        with st.expander("Why (rule path)"):
                            for step in decision["rule_path"]:
                                status = "✅" if step.get("passed") else "❌"
                                st.write(f"- {status} {step.get('clause_id','N/A')} — `{step.get('test','')}`")

        state.chat_history.append({"role":"assistant","content":assistant_text})

    # Follow-up form for missing fields
    if state.pending_missing_fields:
        st.info("More information required to refine the classification:")
        answers = {}
        with st.form("missing_fields_followup"):
            for f in state.pending_missing_fields:
                answers[f] = st.text_input(f"Provide **{f}**")
            submitted = st.form_submit_button("Submit answers")
        if submitted:
            with st.spinner("Updating…"):
                resp = answer_missing(state.session_id, answers)
                assistant_text = resp.get("assistant",{}).get("text","(no response)")
                state.chat_history.append({"role":"assistant","content":assistant_text})
                st.chat_message("assistant").markdown(assistant_text)
                state.pending_missing_fields = resp.get("missing_fields", []) or []
