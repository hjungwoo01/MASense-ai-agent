from typing import Dict, Any, List, Optional
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import BedrockEmbeddings
import json
from pydantic import BaseModel

class OrganizationContext(BaseModel):
    org_type: str  # e.g., "SME", "Large Enterprise", "Financial Institution", "Startup", "Government", "NGO"
    industry: str
    size_category: Optional[str] = None  # e.g., "Small", "Medium", "Large"
    country: str = "Singapore"
    existing_sustainability_programs: Optional[List[str]] = None

def extract_inputs(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and validate input data for processing, with enhanced organization context
    """
    try:
        action_data = state["action"]
        
        # Validate basic required fields
        required_fields = ['description', 'amount']
        
        # Check required fields
        missing_fields = [field for field in required_fields if field not in action_data]
        if missing_fields:
            return {
                **state,
                "status": "error",
                "errors": [f"Missing required fields: {', '.join(missing_fields)}"]
            }
            
        # Validate organization data
        org_data = action_data.get('organization', {})
        try:
            org_context = OrganizationContext(**org_data)
        except Exception as e:
            return {
                **state,
                "status": "error",
                "errors": [f"Invalid organization data: {str(e)}"]
            }
            
        # Update context with validated data
        return {
            **state,
            "status": "success",
            "context": {
                "action": action_data,
                "organization": org_context.dict()
            }
        }
        
    except Exception as e:
        return {
            **state,
            "status": "error",
            "errors": [f"Error extracting inputs: {str(e)}"]
        }
    missing_fields = [field for field in required_fields if not action_data.get(field)]
    
    if missing_fields:
        return {
            "action": action_data,
            "status": "error",
            "errors": [f"Missing required field: {', '.join(missing_fields)}"],
            "context": {},
            "evaluation": {},
            "explanation": {},
            "artifacts": {}
        }
    
    # Extract organization context if provided
    org_context = action_data.get('organization', {
        'org_type': 'Unspecified',
        'industry': 'General',
        'country': 'Singapore'
    })
    
    # Use Bedrock to analyze the description and auto-categorize if sector/activity not provided
    if 'sector' not in action_data or 'activity' not in action_data:
        # This would be implemented in retrieve_clauses.py
        action_data['needs_categorization'] = True
    
    # Normalize any provided sector name
    if 'sector' in action_data:
        action_data['sector'] = action_data['sector'].lower().replace(' ', '_')
    
    return {
        "action": action_data,
        "status": "inputs_validated",
        "errors": [],
        "context": {
            "organization": org_context,
            "compliance_level": determine_compliance_level(org_context),
            "reporting_requirements": get_reporting_requirements(org_context)
        }
    }

def determine_compliance_level(org_context: Dict[str, Any]) -> str:
    """
    Determine the appropriate compliance level based on organization type
    """
    compliance_levels = {
        "Financial Institution": "Enhanced",
        "Large Enterprise": "Standard",
        "Government": "Enhanced",
        "SME": "Basic",
        "Startup": "Basic",
        "NGO": "Basic"
    }
    return compliance_levels.get(org_context['org_type'], "Standard")

def get_reporting_requirements(org_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Define reporting requirements based on organization type and size
    """
    base_requirements = {
        "documentation_level": "standard",
        "reporting_frequency": "quarterly",
        "verification_needed": False
    }
    
    if org_context['org_type'] in ["Financial Institution", "Large Enterprise"]:
        base_requirements.update({
            "documentation_level": "detailed",
            "reporting_frequency": "monthly",
            "verification_needed": True,
            "third_party_audit": True
        })
    elif org_context['org_type'] in ["Government", "NGO"]:
        base_requirements.update({
            "documentation_level": "detailed",
            "reporting_frequency": "quarterly",
            "verification_needed": True,
            "public_reporting": True
        })
    
    return base_requirements
