from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class RuleStep(BaseModel):
    clause_id: str
    test: str
    passed: bool

class Evidence(BaseModel):
    type: str
    source: str
    url: Optional[str] = None
    local_path: Optional[str] = None

class Decision(BaseModel):
    action_id: str
    label: str  # Green|Amber|Red
    activity: Dict[str, str]
    rule_path: List[RuleStep]
    DNSH: List[Dict[str, Any]] = []
    Safeguards: List[Dict[str, Any]] = []
    evidence: List[Evidence] = []
    confidence: float = Field(ge=0, le=1)
    explanation: str
    reporting_implications: Dict[str, Any] = {}