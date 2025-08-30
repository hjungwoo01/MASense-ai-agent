from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import json
import os
from dotenv import load_dotenv

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
