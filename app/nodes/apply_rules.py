from typing import Dict, Any
from app.bedrock_client import BedrockClient
import logging
import json

logger = logging.getLogger(__name__)

def apply_rules(state: Dict[str, Any]) -> Dict[str, Any]:
    """Apply MAS rules to evaluate the financial action"""
    try:
        # Get context from state
        context = state.get("context", {})
        action = context.get("action", {})
        clauses = context.get("clauses", [])
        
        if not action or not clauses:
            return {
                **state,
                "status": "error",
                "errors": ["Missing required action or clauses"]
            }

        # Use Bedrock to analyze against clauses
        client = BedrockClient()
        analysis_prompt = f"""
        Analyze this financial action against the MAS sustainability framework clauses:

        Action: {action.get('description')}
        Amount: {action.get('amount')} {action.get('currency')}
        
        Relevant Framework Clauses:
        {json.dumps(clauses, indent=2)}

        You must return a valid JSON object with exactly these fields:
        {{
            "classification": "Green" or "Amber" or "Ineligible",
            "explanation": "Detailed reasoning based on the clauses",
            "required_documentation": ["doc1", "doc2", ...]
        }}
        Only return the JSON, no other text."""

        response = client.generate_response(analysis_prompt)
        if response.get("status") == "error":
            return {
                **state,
                "status": "error",
                "errors": [f"Analysis failed: {response.get('error')}"]
            }

        # Parse the AI response content as JSON
        try:
            content = json.loads(response.get("content", "{}"))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {response.get('content')}")
            return {
                **state,
                "status": "error", 
                "errors": ["Invalid response format from AI"]
            }

        # Update evaluation with parsed content
        evaluation = {
            "classification": content.get("classification", ""),
            "explanation": content.get("explanation", ""),
            "required_documentation": content.get("required_documentation", [])
        }

        return {
            **state,
            "status": "success",
            "evaluation": evaluation,
            "context": {
                **context,
                "evaluation_details": content
            }
        }

    except Exception as e:
        logger.error(f"Error in apply_rules: {str(e)}")
        return {
            **state,
            "status": "error",
            "errors": [f"Rule application failed: {str(e)}"]
        }