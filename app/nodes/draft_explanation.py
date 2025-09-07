from typing import Dict, Any
import logging
from ..bedrock_client import BedrockClient

logger = logging.getLogger(__name__)

def draft_explanation(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Draft an explanation for the evaluation using LLM reasoning.
    """
    try:
        eval_data = state.get("evaluation", {})
        action = state["context"]["action"]

        if not eval_data:
            return {**state, "status": "error", "errors": ["No evaluation data available"]}

        # Prepare LLM prompt
        prompt = f"""
        Action: {action.get('description')}
        Sector: {action.get('sector')}
        Classification: {eval_data.get('classification')}
        Matched Criteria: {eval_data.get('matched_criteria')}
        
        Please explain why this classification was given, 
        referencing MAS sustainability taxonomy principles.
        """

        try:
            client = BedrockClient()
            llm_response = client.generate_response(prompt)
            explanation_text = llm_response.get("content", "No explanation generated.")
        except Exception as e:
            logger.warning(f"Bedrock unavailable, fallback explanation used: {e}")
            explanation_text = (
                f"The action was classified as {eval_data.get('classification')} "
                f"based on alignment with MAS taxonomy clauses."
            )

        return {
            **state,
            "status": "success",
            "explanation": {
                "summary": explanation_text,
                "confidence": 0.9
            }
        }

    except Exception as e:
        logger.exception("Error in draft_explanation")
        return {**state, "status": "error", "errors": [str(e)]}
