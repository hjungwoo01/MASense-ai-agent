import os
import requests
from typing import Dict, Any, Optional, List

# API Endpoint
API_BASE = os.getenv("ESG_API_BASE", "http://localhost:8000")

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

def chat_message(session_id: str, message: str, company_profile: Dict[str, Any], doc_ids: List[str] = None) -> Dict[str, Any]:
    # Create action from company profile
    action = {
        "sector": company_profile.get("context", {}).get("sector", ""),
        "activity": company_profile.get("context", {}).get("activity", ""),
        "description": message,
        "amount": company_profile.get("context", {}).get("amount", 0),
        "currency": "SGD",
        "additional_context": company_profile
    }
    
    # Create financial action payload
    payload = {
        "sector": company_profile.get("context", {}).get("sector", ""),
        "activity": company_profile.get("context", {}).get("activity", ""),
        "description": message,
        "amount": float(company_profile.get("context", {}).get("amount", 0)),
        "currency": "SGD",
        "additional_context": {
            "doc_ids": doc_ids or [],
            "session_id": session_id,
            **company_profile
        }
    }
    
    resp = _post_json("/evaluate", payload)
    
    if resp is None:
        return {
            "status": "success",
            "classification": "Unknown",
            "explanation": "No evaluation available (service unavailable)",
            "required_documentation": [],
            "confidence": 0,
            "decision": {"label": "Unknown"},
            "assistant": {
                "text": "Service is currently unavailable. Please try again later."
            }
        }

    # Transform the API response into a nicely formatted message
    classification = resp.get("classification", "Unknown")
    emoji = {"Green": "🟢", "Amber": "🟡", "Ineligible": "🔴"}.get(classification, "ℹ️")
    
    formatted_text = [
        f"{emoji} **Classification:** {classification}\n",
        f"**Explanation:**\n{resp.get('explanation', 'No explanation available')}\n"
    ]
    
    if resp.get("required_documentation"):
        formatted_text.append("**Required Documentation:**")
        for doc in resp.get("required_documentation", []):
            formatted_text.append(f"- {doc}")
            
    if resp.get("confidence") is not None:
        formatted_text.append(f"\n**Confidence:** {resp.get('confidence')*100:.0f}%")
    
    # Return the structured response
    return {
        "status": resp.get("status", "error"),
        "classification": classification,
        "explanation": resp.get("explanation"),
        "required_documentation": resp.get("required_documentation", []),
        "confidence": resp.get("confidence", 0),
        "decision": {"label": classification},
        "assistant": {"text": "\n".join(formatted_text)}
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