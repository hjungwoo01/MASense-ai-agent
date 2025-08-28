import streamlit as st

def input_form():
    st.subheader("Describe your financial action")
    with st.form("action_form", clear_on_submit=False):
        action_id = st.text_input("Action ID", value=st.session_state.action_id)
        desc = st.text_area(
            "Description (plain English)",
            value=st.session_state.description,
            height=120,
            help="E.g., 'Loan for a gas-fired power plant upgrade with carbon capture in Singapore.'",
        )
        col1, col2 = st.columns(2)
        with col1:
            sector = st.text_input("Sector (optional)", value="")
        with col2:
            activity = st.text_input("Activity (optional)", value="")

        submitted = st.form_submit_button("Classify", use_container_width=True)
    if submitted:
        st.session_state.action_id = action_id
        st.session_state.description = desc
        payload = {
            "action_id": action_id,
            # Let backend do NER if these are blank; send description regardless
            "sector": sector or None,
            "activity": activity or None,
            "description": desc,
            "metrics": {} # Known metrics, can add more in the loop
        }
        return payload
    return None
