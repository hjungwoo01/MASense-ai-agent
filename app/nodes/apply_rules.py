from app.bedrock_client import BedrockClient
import logging
import json

logger = logging.getLogger(__name__)

def apply_rules(state: dict) -> dict:
    """
    Apply MAS rules to the extracted user input using Bedrock (Claude).
    """
    try:
        client = BedrockClient()

        # Get context from state
        context = state.get("context", {})
        action = context.get("action", {})
        org = context.get("organization", {})

        if not action or not org:
            logger.error("Missing action or organization context")
            return {
                **state,
                "status": "error",
                "errors": ["Missing action or organization context"]
            }

        # Prepare action data for analysis
        analysis_request = {
            "description": action.get("description", ""),
            "amount": action.get("amount", 0),
            "currency": action.get("currency", "SGD"),
            "organization": org
        }

        logger.info(f"Analyzing financial action: {analysis_request}")
        result = client.analyze_financial_action(analysis_request)

        if result.get("status") == "error":
            error_msg = result.get("error", "Unknown error in rule analysis")
            logger.error(f"Analysis failed: {error_msg}")
            return {
                **state,
                "status": "error",
                "errors": [error_msg]
            }

        # Use the content directly if already a dict, else try to parse
        content = result.get("content", {})
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                logger.warning("LLM response is not valid JSON.")
                return {
                    **state,
                    "status": "error",
                    "errors": ["LLM returned invalid JSON format"]
                }

        # Extract evaluation results
        evaluation = {
            "classification": content.get("classification", ""),
            "explanation": content.get("explanation", ""),
            "required_documentation": content.get("required_documentation", [])
        }

        logger.info(f"Analysis completed with classification: {evaluation['classification']}")
        return {
            **state,
            "status": "success",
            "evaluation": evaluation
        }

    except Exception as e:
        error_msg = f"Error in rule analysis: {str(e)}"
        logger.error(error_msg)
        return {
            **state,
            "status": "error",
            "errors": [error_msg]
        }
