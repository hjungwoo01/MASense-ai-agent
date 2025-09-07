from typing import Dict, Any, List
import logging
import json
from ..bedrock_client import BedrockClient

logger = logging.getLogger(__name__)

def draft_explanation(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate organization-specific detailed explanation of evaluation results
    """
    try:
        if state.get("status") == "error":
            return state
            
        # Get context from state
        context = state.get("context", {})
        evaluation = state.get("evaluation", {})
        
        logger.info(f"Starting draft_explanation with evaluation: {evaluation}")
        logger.info(f"Context: {context}")
        
        if not evaluation:
            logger.error("No evaluation data found in state")
            return {
                **state,
                "status": "error",
                "errors": ["No evaluation results to explain"]
            }
            
        # Get the action details
        action = context.get("action", {})
        org = context.get("organization", {})
        rules = context.get("rules", {})
        
        if not all([action, org, rules]):
            return {
                **state,
                "status": "error",
                "errors": ["Missing required context for explanation"]
            }
            
        client = BedrockClient()
        
        # Create explanation prompt
        explanation_prompt = f"""
        Generate a detailed explanation for this financial action evaluation:

        Action Details:
        - Description: {action.get('description', '')}
        - Classification: {evaluation.get('classification', '')}
        - Sector: {action.get('sector', '')}
        - Amount: {action.get('amount')} {action.get('currency', 'SGD')}

        You must return a valid JSON object with this structure:
        {{
            "text": "Detailed explanation of the classification and reasoning",
            "key_points": ["Point 1", "Point 2", ...],
            "recommendations": ["Recommendation 1", "Recommendation 2", ...]
        }}
        Only return the JSON, no other text.
        """
        
        # Get detailed explanation from Bedrock
        result = client.generate_response(explanation_prompt)
        
        if result.get("status") == "error":
            return {
                **state,
                "status": "error",
                "errors": [result.get("error", "Failed to generate explanation")]
            }
        
        # Parse the response content
        explanation_content = json.loads(result.get("content", "{}"))
        return {
            **state,
            "status": "success",
            "explanation": explanation_content
        }
        
    except Exception as e:
        error_msg = f"Error generating explanation: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "status": "error",
            "errors": [error_msg]
        }

