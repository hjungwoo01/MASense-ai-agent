import os
import json
import uuid
import shutil
import hashlib
import logging
import pathlib
import pdfplumber
from datetime import datetime
from decimal import Decimal
from collections import deque
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

from app.graph import evaluate_financial_action

# Remove duplicate logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

UPLOAD_ROOT = os.getenv("MAS_UPLOAD_DIR", os.path.join(os.getcwd(), "data", "uploads"))
pathlib.Path(UPLOAD_ROOT).mkdir(parents=True, exist_ok=True)

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
    sector: str = Field(..., description="Business sector of the activity")
    activity: str = Field(..., description="Specific activity being evaluated")
    description: str = Field(..., min_length=10, description="Detailed description of the activity")
    amount: float = Field(..., gt=0, description="Financial amount involved")
    currency: str = Field(default="SGD", min_length=3, max_length=3)
    additional_context: Optional[Dict] = Field(default=None)

    @validator('sector')
    def validate_sector(cls, v):
        if not v.strip():
            raise ValueError('Sector cannot be empty')
        return v.strip()

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return float(Decimal(str(v)).quantize(Decimal('0.01')))

class EvaluationResult(BaseModel):
    status: str = Field(..., description="Status of the evaluation")
    classification: Optional[str] = Field(None, description="Green, Amber, or Ineligible")
    explanation: Optional[str] = Field(None, description="Detailed explanation")
    required_documentation: List[str] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)

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

@app.post("/evaluate", response_model=EvaluationResult)
async def evaluate_action(action: FinancialAction):
    result = evaluate_financial_action(action.model_dump())

    if result.get("status") == "error":
        err = (result.get("errors") or ["Unknown error"])[0]
        raise HTTPException(status_code=500, detail=err)

    ev = result.get("evaluation", {}) or {}
    ex = result.get("explanation", {}) or {}

    classification = ev.get("classification")
    required_docs = ev.get("required_documentation", [])
    explanation_text = ex.get("summary") or "No explanation generated."
    confidence = ex.get("confidence") or 0.95

    return EvaluationResult(
        status="success",
        classification=classification,
        explanation=explanation_text,
        required_documentation=required_docs,
        confidence=confidence,
    )

@app.post("/batch-evaluate")
async def batch_evaluate(actions: List[FinancialAction]):
    """Evaluate multiple financial actions in batch"""
    results = []
    for action in actions:
        result = await evaluate_action(action)
        results.append(result)
    return results

@app.post("/evaluate-with-context")
async def evaluate_with_context(
    action: FinancialAction,
    context_query: Optional[str] = None
):
    """Evaluate action with additional context from RAG"""
    try:
        # If context query provided, search RAG
        if context_query:
            try:
                # Load FAISS index
                vectorstore = FAISS.load_local("faiss_index")
                docs = vectorstore.similarity_search(context_query)
                
                # Add RAG context to action
                action_dict = action.model_dump()
                action_dict["rag_context"] = [
                    {
                        "content": doc.page_content,
                        "metadata": doc.metadata
                    } for doc in docs
                ]
            except Exception as e:
                logger.warning(f"RAG lookup failed: {str(e)}")
                action_dict = action.model_dump()
        else:
            action_dict = action.model_dump()

        # Run evaluation workflow
        result = evaluate_financial_action(action_dict)
        
        if result.get("status") == "error":
            raise HTTPException(
                status_code=500,
                detail=result.get("errors", ["Unknown error occurred"])
            )

        return {
            "status": "success",
            "evaluation": result.get("evaluation", {}),
            "rag_sources": [
                doc.get("metadata", {}).get("source")
                for doc in action_dict.get("rag_context", [])
            ] if "rag_context" in action_dict else []
        }

    except Exception as e:
        logger.error(f"Evaluation with context failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint
@app.get("/health")
async def health_check():
    """Check API and Bedrock client health"""
    try:
        client = BedrockClient()
        test_response = client.generate_response("test")
        return {
            "status": "healthy",
            "bedrock_client": "connected" if test_response.get("status") == "success" else "error"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

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
    if session_id not in app.state.sessions:
        raise HTTPException(status_code=404, detail="session not found")

    # Read all bytes to compute a stable hash
    data = await file.read()
    sha256 = hashlib.sha256(data).hexdigest()

    # Check if already uploaded in this session
    for d in app.state.sessions[session_id]["docs"]:
        if d.get("sha256") == sha256:
            return {
                "doc_id": d["doc_id"],
                "name": d["name"],
                "kind": d["kind"],
                "size_kb": d.get("size_kb"),
                "page_count": d.get("page_count"),
                "preview": d.get("preview"),
                "deduplicated": True,
            }

    # Persist new file
    sess_dir = os.path.join(UPLOAD_ROOT, session_id)
    os.makedirs(sess_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    safe_name = f"{ts}__{file.filename}".replace("/", "_")
    dest_path = os.path.join(sess_dir, safe_name)
    with open(dest_path, "wb") as out:
        out.write(data)

    size_kb = round(os.path.getsize(dest_path) / 1024, 2)
    page_count, preview = None, None
    if (file.content_type or "").lower() == "application/pdf" or dest_path.lower().endswith(".pdf"):
        try:
            with pdfplumber.open(dest_path) as pdf:
                page_count = len(pdf.pages)
                if page_count:
                    t = pdf.pages[0].extract_text() or ""
                    preview = (t[:800] + "…") if len(t) > 800 else t
        except Exception as e:
            logger.warning(f"PDF preview extraction failed: {e}")

    doc_id = f"doc-{uuid.uuid4()}"
    record = {
        "doc_id": doc_id,
        "name": file.filename,
        "kind": kind,
        "mime": file.content_type,
        "path": dest_path,
        "sha256": sha256,
        "size_kb": size_kb,
        "page_count": page_count,
        "preview": preview,
        "uploaded_at": ts,
    }
    app.state.sessions[session_id]["docs"].append(record)

    return {
        "doc_id": doc_id,
        "name": file.filename,
        "kind": kind,
        "size_kb": size_kb,
        "page_count": page_count,
        "preview": preview,
        "deduplicated": False,
    }
    
@app.get("/session/docs")
async def list_session_docs(session_id: str):
    """List docs for a session (without heavy fields)."""
    if session_id not in app.state.sessions:
        raise HTTPException(status_code=404, detail="session not found")
    docs = app.state.sessions[session_id]["docs"]
    # trim path/preview for listing
    return [
        {
            "doc_id": d["doc_id"],
            "name": d["name"],
            "kind": d.get("kind"),
            "mime": d.get("mime"),
            "size_kb": d.get("size_kb"),
            "page_count": d.get("page_count"),
            "uploaded_at": d.get("uploaded_at"),
        }
        for d in docs
    ]

@app.get("/session/doc/{doc_id}")
async def get_session_doc(session_id: str, doc_id: str):
    """Fetch full doc metadata (incl. preview)."""
    if session_id not in app.state.sessions:
        raise HTTPException(status_code=404, detail="session not found")
    for d in app.state.sessions[session_id]["docs"]:
        if d["doc_id"] == doc_id:
            return d
    raise HTTPException(status_code=404, detail="doc not found")

@app.post("/chat")
async def chat(payload: Dict[str, Any]):
    try:
        sid = payload.get("session_id")
        message = (payload.get("message") or "").strip()
        org = payload.get("company_profile") or {}
        ctx = org.get("context", {}) if isinstance(org.get("context"), dict) else {}

        selected_docs = []
        doc_ids = payload.get("doc_ids") or []
        if sid and sid in app.state.sessions and doc_ids:
            by_id = {d["doc_id"]: d for d in app.state.sessions[sid]["docs"]}
            selected_docs = [by_id[i] for i in doc_ids if i in by_id]

        amount = float(ctx.get("amount") or 1.0)
        if amount <= 0:
            amount = 1.0
        currency = ctx.get("currency", "SGD")

        action_dict = {
            "sector": ctx.get("sector", "Energy"),
            "activity": ctx.get("activity", "Solar Panel Installation"),
            "description": message,
            "amount": amount,
            "currency": currency,
            "organization": org,
            "documents": selected_docs,
        }

        logger.info("[/chat] running graph sector=%s activity=%s docs=%d",
                    action_dict["sector"], action_dict["activity"], len(selected_docs))

        result = evaluate_financial_action(action_dict)

        ev = result.get("evaluation", {}) or {}
        ex = result.get("explanation", {}) or {}

        classification = ev.get("classification", "Unknown")
        matched = ev.get("matched_criteria", [])
        required_docs = ev.get("required_documentation", [])
        explanation_text = ex.get("summary") or "No explanation generated."
        confidence = ex.get("confidence") or 0.95

        response_text = (
            f"**Classification**: {classification}\n\n"
            f"**Explanation**: {explanation_text}\n\n"
            "**Required Documentation:**\n" +
            ("\n".join([f"- {doc}" for doc in required_docs]) or "- None")
        )

        return {
            "assistant": {"text": response_text},
            "classification": classification,
            "explanation": explanation_text,
            "required_documentation": required_docs,
            "confidence": confidence,
            "decision": {"label": classification},
            "matched_criteria": matched,
            "raw": result,
        }

    except Exception as e:
        logger.exception("Chat processing failed")
        raise HTTPException(status_code=500, detail=f"Chat endpoint error: {e}")


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
