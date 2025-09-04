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
import logging
from .bedrock_client import BedrockClient
from .graph import evaluate_financial_action
from langchain_community.vectorstores import FAISS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    """Evaluate a financial action using our workflow"""
    try:
        # Convert Pydantic model to dict for workflow
        action_dict = action.model_dump()
        
        # Run through our evaluation workflow
        result = evaluate_financial_action(action_dict)
        
        if result.get("status") == "error":
            raise HTTPException(
                status_code=500,
                detail=result.get("errors", ["Unknown error occurred"])
            )
            
        # Extract evaluation results
        evaluation = result.get("evaluation", {})
        return {
            "status": "success",
            "classification": evaluation.get("classification"),
            "explanation": evaluation.get("explanation"),
            "required_documentation": evaluation.get("required_documentation", []),
            "confidence": 0.95  # TODO: Implement confidence scoring
        }

    except Exception as e:
        logger.error(f"Evaluation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
    """Process chat messages using our evaluation workflow"""
    try:
        # Extract action details from chat payload
        action = {
            "description": payload.get("message", ""),
            "amount": float(payload.get("amount", 0)),
            "currency": payload.get("currency", "SGD"),
            "organization": payload.get("company_profile", {})
        }
        
        # Run evaluation
        result = evaluate_financial_action(action)
        
        if result.get("status") == "error":
            raise HTTPException(
                status_code=500,
                detail=result.get("errors", ["Unknown error occurred"])
            )

        evaluation = result.get("evaluation", {})
        
        # Format response for chat
        response_text = (
            f"**Classification**: {evaluation.get('classification', 'Unknown')}\n\n"
            f"**Explanation**: {evaluation.get('explanation', 'No explanation available')}\n\n"
            "**Required Documentation**:\n" + 
            "\n".join([f"- {doc}" for doc in evaluation.get("required_documentation", [])])
        )

        return {
            "assistant": {"text": response_text},
            "decision": {"label": evaluation.get("classification")},
            "raw_evaluation": evaluation
        }

    except Exception as e:
        logger.error(f"Chat processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
