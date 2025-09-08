from typing import Dict, Any
import logging
import os

try:
    from ..bedrock_client import BedrockClient
    _BEDROCK_AVAILABLE = True
except Exception:
    _BEDROCK_AVAILABLE = False

logger = logging.getLogger(__name__)

def draft_explanation(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Draft an explanation for the evaluation using LLM reasoning when available;
    otherwise produce a deterministic, useful fallback explanation.
    """
    try:
        evaluation = state.get("evaluation", {}) or {}
        context = state.get("context", {}) or {}
        action = context.get("action", {}) or state.get("action", {}) or {}

        cls = evaluation.get("classification", "Unknown")
        criteria = evaluation.get("matched_criteria", []) or []
        sector = action.get("sector", "Unknown")
        activity = action.get("activity", "Unknown")
        description = action.get("description", "")

        prompt = (
            "You are an assistant that explains sustainability taxonomy decisions.\n"
            f"Sector: {sector}\n"
            f"Activity: {activity}\n"
            f"Action: {description}\n"
            f"Preliminary Classification: {cls}\n"
            f"Matched Criteria: {criteria}\n"
            "Explain concisely why this classification applies in the context of the MAS Singapore-Asia Taxonomy. "
            "Mention DNSH/safeguards briefly if present. Avoid speculation."
        )

        explanation_text = ""

        if _BEDROCK_AVAILABLE and os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
            try:
                client = BedrockClient()
                resp = client.generate_response(prompt)
                explanation_text = resp.get("content") or resp.get("text") or ""
            except Exception as llm_err:
                logger.warning("[draft_explanation] Bedrock unavailable (%s); using fallback.", llm_err)

        if not explanation_text:
            criteria_str = ", ".join(criteria) if criteria else "no explicit criteria found"
            explanation_text = (
                f"This activity ({activity} in {sector}) is classified as **{cls}** "
                f"based on detected MAS taxonomy signals: {criteria_str}."
            )

        has_explicit = any(c.lower().startswith(("meets green", "falls under amber", "fails eligibility")) for c in criteria)
        confidence = 0.9 if has_explicit else 0.75

        return {
            **state,
            "status": "success",
            "explanation": {"summary": explanation_text, "confidence": confidence}
        }

    except Exception as e:
        logger.exception("[draft_explanation] Unexpected error")
        errs = list(state.get("errors", [])) + [f"Error in draft_explanation: {e}"]
        return {
            **state,
            "status": "success",
            "errors": errs,
            "explanation": {"summary": "Explanation unavailable due to an internal error.", "confidence": 0.6}
        }