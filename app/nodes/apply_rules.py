from app.bedrock_client import call_claude

def apply_rules(state : dict) -> dict:
    """
    Apply MAS rules to the extracted user input using Bedrock (Claude).
    """
    user_action = state.get("query", "")
    retrieved_clauses = state.get("retrieved_clauses", [])
    extracted_inputs = state.get("extracted_inputs", {})

    # Construct prompt for classification
    rules_text = "\n\n".join([
        f"Activity: {c['activity']}\nClassification: {c['classification']}\nDescription: {c['description']}"
        for c in retrieved_clauses
    ])
    prompt = f"""
    You are an ESG compliance AI agent. Your job is to classify the user's financial activity
    according to the MAS Singapore-Asia taxonomy.

    User activity:
    "{user_action}"

    Extracted metadata:
    Sector: {extracted_inputs.get('sector')}
    Activity: {extracted_inputs.get('activity')}
    Attributes: {extracted_inputs.get('attributes')}

    MAS Classification Rules (retrieved from vector DB):
    {rules_text}

    Instructions:
    1. Assign a classification: Green, Amber, or Ineligible.
    2. Justify the label using MAS clauses above.
    3. If ambiguous, request clarification from user.

    Respond in this JSON format:
    {{
    "label": "...",
    "explanation": "...",
    "needs_clarification": true/false
    }}
    """

    try:
        result = bedrock_client.call_claude(prompt)
        output = result.get("completion", result) # handling raw JSON vs structured response

    except Exception as e:
        output = {
            "label": "Error",
            "explanation": f"Failure in calling Bedrock Client: {str(e)}",
            "needs_clarification": True
        }
    
    state.update({
        "label": output['label'],
        "explanation": output['explanation'],
        "needs_clarification": output['needs_clarification']
    })

    return state