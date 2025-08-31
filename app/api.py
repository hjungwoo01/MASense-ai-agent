from fastapi import FastAPI, Request, HTTPException
from fastapi import UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
from typing import Any
import json
import os
from dotenv import load_dotenv

from collections import deque
import uuid

# Load environment variables
load_dotenv()

app = FastAPI(
    title="MASense AI Agent API",
    description="API for evaluating financial actions against MAS sustainability frameworks",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Input Models
class FinancialAction(BaseModel):
    sector: str
    activity: str
    description: str
    amount: float
    currency: str = "SGD"
    additional_context: Optional[Dict] = None

class EvaluationResponse(BaseModel):
    action_id: str
    classification: str  # Green, Amber, or Ineligible
    matched_criteria: List[Dict]
    suggestions: List[str]
    confidence_score: float
    explanation: str

# Load MAS ruleset
def load_mas_ruleset():
    try:
        with open("mas_ruleset.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="MAS ruleset not found")

if not hasattr(app.state, "sessions"):
    app.state.sessions = {}  # session_id -> {"docs": list[dict], "chat": deque}

# API Routes
@app.get("/")
async def root():
    return {"message": "Welcome to MASense AI Agent API"}

@app.get("/sectors")
async def get_sectors():
    """Get all available sectors from the MAS taxonomy"""
    ruleset = load_mas_ruleset()
    return {"sectors": list(ruleset.keys())}

@app.get("/sector/{sector_name}")
async def get_sector_details(sector_name: str):
    """Get detailed criteria for a specific sector"""
    ruleset = load_mas_ruleset()
    if sector_name not in ruleset:
        raise HTTPException(status_code=404, detail="Sector not found")
    return ruleset[sector_name]

@app.post("/evaluate")
async def evaluate_action(action: FinancialAction):
    """Evaluate a financial action against MAS sustainability criteria"""
    try:
        # 1. Load relevant sector criteria
        ruleset = load_mas_ruleset()
        if action.sector.lower() not in [s.lower() for s in ruleset.keys()]:
            raise HTTPException(status_code=400, detail="Invalid sector")

        # 2. Here you would typically:
        # - Use RAG to find relevant criteria
        # - Apply your agent's evaluation logic
        # - Generate explanation and suggestions
        
        # Placeholder response - replace with actual agent logic
        return EvaluationResponse(
            action_id="test_id",
            classification="Amber",  # Replace with actual classification logic
            matched_criteria=[],  # Add actual matched criteria
            suggestions=["Implement proper monitoring systems", "Consider green alternatives"],
            confidence_score=0.85,
            explanation="This is a placeholder explanation"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch-evaluate")
async def batch_evaluate(actions: List[FinancialAction]):
    """Evaluate multiple financial actions in batch"""
    results = []
    for action in actions:
        result = await evaluate_action(action)
        results.append(result)
    return results

# Health check endpoint
@app.get("/health")
async def health_check():
    from datetime import datetime
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ----------------------------
# Endpoints for Streamlit
# ----------------------------

@app.post("/session/start")
async def session_start():
    """Create a demo session and return session_id."""
    sid = f"sess-{uuid.uuid4()}"
    app.state.sessions[sid] = {"docs": [], "chat": deque(maxlen=100)}
    return {"session_id": sid}

@app.post("/session/upload")
async def session_upload(
    session_id: str = Form(...),
    kind: str = Form("sustainability_report"),
    file: UploadFile = File(...),
):
    """Accept a PDF upload and register it to the session (demo: metadata only)."""
    if session_id not in app.state.sessions:
        raise HTTPException(status_code=404, detail="session not found")

    # For demo we don't persist content; store metadata only.
    doc_id = f"doc-{uuid.uuid4()}"
    app.state.sessions[session_id]["docs"].append({
        "doc_id": doc_id,
        "name": file.filename,
        "kind": kind,
        "mime": file.content_type,
    })
    return {"doc_id": doc_id, "name": file.filename, "kind": kind}

@app.post("/chat")
async def chat(payload: Dict[str, Any]):
    """
    Chat façade that maps to the existing /evaluate logic.
    Expects: session_id, message, company_profile, (optional) chat_history, doc_ids
    """
    sid = payload.get("session_id")
    if not sid or sid not in app.state.sessions:
        raise HTTPException(status_code=404, detail="session not found")

    message = (payload.get("message") or "").strip()
    profile = payload.get("company_profile") or {}

    # Map company_profile + message into FinancialAction
    sector = str(profile.get("sector") or "Energy")
    activity = str(profile.get("activity") or "General activity")
    description = str(profile.get("description") or message or "No description")
    try:
        amount = float(profile.get("amount") or 0.0)
    except Exception:
        amount = 0.0
    currency = str(profile.get("currency") or "SGD")
    additional_context = {
        k: v for k, v in profile.items()
        if k not in {"sector", "activity", "description", "amount", "currency"}
    } or None

    action_model = FinancialAction(
        sector=sector,
        activity=activity,
        description=description,
        amount=amount,
        currency=currency,
        additional_context=additional_context,
    )

    eval_res = await evaluate_action(action_model)
    # normalize to dict
    if hasattr(eval_res, "dict"):
        eval_dict = eval_res.dict()
    else:
        eval_dict = dict(eval_res)

    assistant_text = (
        f"**{eval_dict.get('classification')}** "
        f"(confidence {eval_dict.get('confidence_score')})\n\n"
        f"{eval_dict.get('explanation')}\n\n"
        "Suggestions: " + ", ".join(eval_dict.get("suggestions", []))
    )

    # Append to session chat history
    app.state.sessions[sid]["chat"].append({"role": "user", "content": message})
    app.state.sessions[sid]["chat"].append({"role": "assistant", "content": assistant_text})

    return {
        "assistant": {"text": assistant_text},
        "decision": {"label": eval_dict.get("classification")},
        "matched_criteria": eval_dict.get("matched_criteria", []),
        "missing_fields": [],
        "raw": eval_dict,
    }

@app.post("/chat/answer")
async def chat_answer(payload: Dict[str, Any]):
    """Demo endpoint to acknowledge follow-up answers."""
    sid = payload.get("session_id")
    if not sid or sid not in app.state.sessions:
        raise HTTPException(status_code=404, detail="session not found")
    answers = payload.get("answers") or {}
    app.state.sessions[sid]["chat"].append({"role": "user", "content": f"[answers] {answers}"})
    return {
        "assistant": {"text": "Thanks, noted your additional details (demo)."},
        "decision": {"label": "Green"},
        "missing_fields": [],
    }
