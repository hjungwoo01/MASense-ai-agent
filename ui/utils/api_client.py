import os
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

def chat_message(session_id: str, message: str, company_profile: Dict[str, Any], doc_ids: List[str] = None) -> Dict[str, Any]:
    """Send a chat message and get response"""
    try:
        # Create FinancialAction payload
        context = company_profile.get("context", {})
        payload = {
            "sector": context.get("sector", "Energy"),
            "activity": context.get("activity", "Solar Panel Installation"),
            "description": message,
            "amount": float(context.get("amount", 500000)),  # Default amount if not provided
            "currency": "SGD",
            "additional_context": {
                "session_id": session_id,
                "doc_ids": doc_ids or [],
                "company_profile": company_profile
            }
        }
        
        logger.info(f"Sending evaluation request: {payload}")
        resp = _post_json("/evaluate", payload)
        
        if resp is None:
            return {
                "status": "error",
                "assistant": {"text": "Service is currently unavailable. Please try again later."},
                "classification": "Unknown",
                "explanation": None,
                "required_documentation": [],
                "confidence": 0,
                "decision": {"label": "Unknown"}
            }

        # Extract nested data from response
        artifacts = resp.get("artifacts", {})
        evaluation = artifacts.get("evaluation", {})
        explanation = artifacts.get("explanation", {})
        
        # Extract specific fields
        classification = evaluation.get("classification", "Unknown")
        matched_criteria = evaluation.get("matched_criteria", [])
        required_docs = evaluation.get("required_documentation", [])
        explanation_text = explanation.get("summary", "No explanation available")
        confidence = explanation.get("confidence", 0)
        
        # Build formatted response
        emoji = {"Green": "🟢", "Amber": "🟡", "Ineligible": "🔴"}.get(classification, "ℹ️")
        
        response_sections = [
            f"{emoji} **Classification**: {classification}",
            "",
            "**Matched Criteria:**"
        ]
        
        # Add numbered matched criteria
        for i, criterion in enumerate(matched_criteria, 1):
            response_sections.append(f"{i}. {criterion}")
        
        # Add detailed explanation
        if explanation_text:
            response_sections.extend([
                "",
                "**Detailed Explanation:**",
                explanation_text
            ])
        
        # Add required documentation
        if required_docs:
            response_sections.extend([
                "",
                "**Required Documentation:**",
                *[f"- {doc}" for doc in required_docs]
            ])
        
        # Add confidence score
        if confidence:
            response_sections.extend([
                "",
                f"**Confidence Score**: {confidence*100:.0f}%"
            ])
        
        return {
            "status": "success",
            "assistant": {"text": "\n".join(response_sections)},
            "classification": classification,
            "explanation": explanation_text,
            "required_documentation": required_docs,
            "confidence": confidence,
            "decision": {
                "label": classification,
                "matched_criteria": matched_criteria
            }
        }

    except Exception as e:
        logger.error(f"Error in chat_message: {str(e)}")
        return {
            "status": "error",
            "assistant": {"text": f"Error processing request: {str(e)}"},
            "classification": "Unknown",
            "explanation": None,
            "required_documentation": [],
            "confidence": 0,
            "decision": {"label": "Unknown"}
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