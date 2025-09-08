import os
import uuid
import requests
import logging
from typing import Dict, Any, Optional, List

# API Endpoint
API_BASE = os.getenv("ESG_API_BASE", "http://localhost:8000")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- helper functions ----------
def _post_json(path: str, payload: Dict[str, Any], timeout: int = 30) -> Optional[Dict[str, Any]]:
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[api_client] POST {path} failed: {e}")
        return None

def _post_file(path: str, files, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        r = requests.post(f"{API_BASE}{path}", files=files, data=data, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[api_client] POST file {path} failed: {e}")
        return None

# ---------- main API functions ----------
def start_session() -> Dict[str, Any]:
    resp = _post_json("/session/start", {})
    if resp is None:
        return {"session_id": "sess-mock-001"}
    return resp

def upload_document(session_id: str, file_name: str, file_bytes: bytes, kind: str = "sustainability_report") -> Dict[str, Any]:
    files = {"file": (file_name, file_bytes, "application/pdf")}
    data = {"session_id": session_id, "kind": kind}
    resp = _post_file("/session/upload", files, data)
    if resp is None:
        return {"doc_id": f"doc-mock-{len(file_bytes)}", "name": file_name}
    return resp

def chat_message(session_id: str, message: str, company_profile: Dict[str, Any], doc_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Send a chat message to the FastAPI /chat endpoint.
    """
    
    if "context" not in company_profile or not isinstance(company_profile["context"], dict):
        flat = dict(company_profile or {})
        ctx_keys = ("sector", "activity", "amount", "currency", "jurisdiction", "size")
        context = {k: flat[k] for k in ctx_keys if k in flat and flat[k] is not None}
        
        org_payload = {k: v for k, v in flat.items() if k not in context}
        org_payload["context"] = context
    else:
        org_payload = company_profile

    payload = {
        "session_id": session_id,
        "message": message,
        "company_profile": org_payload,
        "doc_ids": doc_ids or [],
        "client_message_id": str(uuid.uuid4()),
    }

    logger.info("POST %s/chat payload=%s", API_BASE, payload)

    resp = requests.post(
        f"{API_BASE}/chat",
        json=payload,
        headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    # Backend /chat returns:
    # {
    # "assistant": {"text": response_text},
    # "classification": result.classification,
    # "explanation": result.explanation,
    # "required_documentation": result.required_documentation,
    # "confidence": result.confidence,
    # "decision": {"label": result.classification},
    # "matched_criteria": mc,
    # }
    assistant_text = data.get("assistant", {}).get("text", "(no response)")
    decision = data.get("decision", {}) or {}
    classification = decision.get("label") or data.get("classification", "Unknown")

    return {
        "status": "success",
        "assistant": {"text": assistant_text},
        "decision": {"label": classification, **({} if "rule_path" not in decision else {"rule_path": decision["rule_path"]})},
        "explanation": data.get("explanation"),
        "required_documentation": data.get("required_documentation", []),
        "confidence": data.get("confidence"),
        "matched_criteria": data.get("matched_criteria", []),
        "raw": data,
    }

def answer_missing(session_id: str, answers: Dict[str, Any]) -> Dict[str, Any]:
    resp = _post_json("/chat/answer", {
        "session_id": session_id,
        "answers": answers
    })
    if resp is None:
        return {
            "status": "error",
            "classification": "Unknown",
            "explanation": "Failed to submit answers (service unavailable)",
            "required_documentation": [],
            "confidence": 0,
            "decision": {"label": "Unknown"},
            "assistant": {
                "text": "Failed to process your answers. Please try again later."
            }
        }
    return resp
