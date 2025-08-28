import os
import requests
from typing import Dict, Any, Optional, List

## TODO: SET TO FASTAPI ENDPOINT
API_BASE = os.getenv("ESG_API_BASE", "http://localhost:8000")

# ---------- real endpoints (fall back to mocks if not available) ----------

def _post_json(path: str, payload: Dict[str, Any], timeout: int = 30) -> Optional[Dict[str, Any]]:
    # Send JSON payload to backend
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def _post_file(path: str, files, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Send files + form fields as multipart/form-data
    try:
        r = requests.post(f"{API_BASE}{path}", files=files, data=data, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

def start_session() -> Dict[str, Any]:
    # Obtain a session_id used by uploads and chat.
    resp = _post_json("/session/start", {})
    if resp is None:
        # mock session (local fallback; backend should return session_id)
        return {"session_id": "sess-mock-001"}
    return resp

def upload_document(session_id: str, file_name: str, file_bytes: bytes, kind: str = "sustainability_report") -> Dict[str, Any]:
    """
    Upload a PDF document to the backend for a given session.
    Args:
        session_id: str - unique session identifier
        file_name: str - name of the file
        file_bytes: bytes - file content
        kind: str - document kind (e.g., "sustainability_report")
    Returns:
        dict with at least doc_id (should be returned by backend)
    """
    # MIME type must be "application/pdf"
    files = {"file": (file_name, file_bytes, "application/pdf")}
    data = {"session_id": session_id, "kind": kind}
    resp = _post_file("/session/upload", files, data)
    if resp is None:
        # mock doc_id (local fallback; backend should return doc_id, name, kind)
        return {"doc_id": f"doc-mock-{len(file_bytes)}", "name": file_name}
    return resp

def chat_message(session_id: str, message: str, company_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a chat turn and context to the backend agent.
    Backend expects:
        - session_id: str
        - message: str (user's latest message)
        - company_profile: dict (optional hints)
        - chat_history: list[{"role":"user|assistant","content": str}]   
        - doc_ids: list[str]
        - client_meta: dict (optional, e.g., {"ui_version": ...})
    Currently only session_id, message, and company_profile are sent.
    """
    payload = {
        "session_id": session_id,
        "message": message,
        "company_profile": company_profile,  # optional hints (sector, activity, metrics)
        "chat_history": [...],
        "doc_ids": [...],
        # "client_meta": {"ui_version": "streamlit-0.1.0"},
    }
    resp = _post_json("/chat", payload)
    if resp is None:
        # ---------- mock assistant behavior (local fallback; real backend should populate all fields) ----------
        text = (
            "Thanks! I’ve scanned your document (mock). Based on MAS Singapore-Asia Taxonomy, "
            "this looks **Green** under Energy → Solar PV (GFIT-EN-1.2.3). "
            "DNSH & safeguards appear satisfied. If you have the plant’s emissions intensity "
            "(gCO₂e/kWh) or commissioning year, share it here."
        )
        return {
            "assistant": {"text": text},
            "decision": {
                "label": "Green",
                "rule_path": [{"clause_id": "GFIT-EN-1.2.3", "test": "grams_co2e_per_kwh <= 100", "passed": True}],
            },
            "missing_fields": []  # e.g., ["grams_co2e_per_kwh"]
        }
    return resp

def answer_missing(session_id: str, answers: Dict[str, Any]) -> Dict[str, Any]:
    """
    Submit answers for missing fields requested by the agent.
    Expects:
        - session_id: str
        - answers: dict[str, Any]
        - chat_history: list[...]
        - doc_ids: list[str]
    """
    payload = {
        "session_id": session_id,
        "answers": answers,
        "chat_history": [...],
        "doc_ids": [...],
    }
    resp = _post_json("/chat/answer", payload)
    if resp is None:
        # mock answer (local fallback; real backend should return updated assistant, decision, missing_fields)
        return {
            "assistant": {"text": "Updated with your inputs (mock). Classification remains **Green**."},
            "decision": {"label": "Green"},
            "missing_fields": []
        }
    return resp