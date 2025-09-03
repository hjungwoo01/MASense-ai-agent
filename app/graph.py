from typing import Dict, Any, TypedDict, Annotated, Union
from langgraph.graph import StateGraph, END
import json
from .nodes import (
    extract_inputs,
    retrieve_clauses,
    apply_rules,
    draft_explanation,
    ask_user,
    emit_artifacts
)

# Define our state type
class State(TypedDict):
    action: Dict[str, Any]
    status: str
    errors: list[str]
    context: Dict[str, Any]
    evaluation: Dict[str, Any]
    explanation: Dict[str, Any]
    artifacts: Dict[str, Any]

def should_continue(state: State) -> bool:
    """Determine if we should continue processing or need clarification"""
    return state["status"] not in ["needs_clarification", "error"]

def create_evaluation_graph() -> StateGraph:
    """
    Create the LangGraph workflow for financial action evaluation
    """
    # Initialize the graph
    workflow = StateGraph(State)

    # Add nodes to the graph
    workflow.add_node("extract_inputs", extract_inputs.extract_inputs)
    workflow.add_node("retrieve_clauses", retrieve_clauses.retrieve_clauses)
    workflow.add_node("apply_rules", apply_rules.apply_rules)
    workflow.add_node("draft_explanation", draft_explanation.draft_explanation)
    workflow.add_node("ask_user", ask_user.ask_user)
    workflow.add_node("emit_artifacts", emit_artifacts.emit_artifacts)

    # Define the conditional edges
    workflow.add_edge("extract_inputs", "retrieve_clauses")
    workflow.add_edge("retrieve_clauses", "apply_rules")
    workflow.add_edge("apply_rules", "draft_explanation")
    workflow.add_edge("draft_explanation", "ask_user")
    
    # Add conditional branching
    workflow.add_conditional_edges(
        "ask_user",
        lambda state: should_continue(state),
        {
            True: "emit_artifacts",
            False: END
        }
    )

    # Set entry point
    workflow.set_entry_point("extract_inputs")

    # Compile the graph
    chain = workflow.compile()
    return chain

def evaluate_financial_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate a financial action using the workflow graph
    """
    try:
        print("[DEBUG] Starting evaluate_financial_action")  # ✅ You MUST see this line

        # Create initial state
        initial_state = State(
            action=action,
            status="started",
            errors=[],
            context={
                "action": action,
                "organization": action.get("organization", {})
            },
            evaluation={},
            explanation={},
            artifacts={}
        )

        graph = create_evaluation_graph()

        # ✅ Use stream, not invoke
        final_state = None
        for state in graph.stream(initial_state):
            print(f"\n🔄 Step: {state.get('status')}")
            print("🧠 Current State:", json.dumps(state, indent=2))
            if state.get("errors"):
                print("❌ Errors:", state["errors"])
            final_state = state

        return {
            "status": "success" if not final_state.get("errors") else "error",
            "evaluation": final_state.get("evaluation", {}),
            "explanation": final_state.get("explanation", {}),
            "artifacts": final_state.get("artifacts", {}),
            "context": final_state.get("context", {}),
            "errors": final_state.get("errors", [])
        }

    except Exception as e:
        print(f"[EXCEPTION] {str(e)}")  # ✅ See any runtime issues
        return {
            "status": "error",
            "errors": [f"Workflow error: {str(e)}"]
        }
