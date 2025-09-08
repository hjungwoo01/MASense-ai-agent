from typing import Dict, Any, TypedDict
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
    return state.get("status") not in ["needs_clarification", "error"]

def create_evaluation_graph() -> StateGraph:
    """
    Create the LangGraph workflow for financial action evaluation
    """
    workflow = StateGraph(State)

    workflow.add_node("extract_inputs", extract_inputs.extract_inputs)
    workflow.add_node("retrieve_clauses", retrieve_clauses.retrieve_clauses)
    workflow.add_node("apply_rules", apply_rules.apply_rules)
    workflow.add_node("draft_explanation", draft_explanation.draft_explanation)
    workflow.add_node("ask_user", ask_user.ask_user)
    workflow.add_node("emit_artifacts", emit_artifacts.emit_artifacts)

    workflow.add_edge("extract_inputs", "retrieve_clauses")
    workflow.add_edge("retrieve_clauses", "apply_rules")
    workflow.add_edge("apply_rules", "draft_explanation")
    workflow.add_edge("draft_explanation", "ask_user")

    workflow.add_conditional_edges(
        "ask_user",
        should_continue,
        {
            True: "emit_artifacts",
            False: END
        }
    )

    workflow.set_entry_point("extract_inputs")
    return workflow.compile()

def evaluate_financial_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate a financial action using the workflow graph.
    IMPORTANT: Each stream update is {<node_name>: <state>}. We must unwrap it.
    """
    try:
        print("[DEBUG] Starting evaluate_financial_action")

        initial_state: State = {
            "action": action,
            "status": "started",
            "errors": [],
            "context": {
                "action": action,
                "organization": action.get("organization", {})
            },
            "evaluation": {},
            "explanation": {},
            "artifacts": {},
        }

        graph = create_evaluation_graph()

        final_state: Dict[str, Any] | None = None

        for update in graph.stream(initial_state):
            node_name, node_state = next(iter(update.items()))
            print(f"\n🔄 Node: {node_name} | status={node_state.get('status')}")
            try:
                print("🧠 Current State:", json.dumps(node_state, indent=2))
            except Exception:
                print("🧠 Current State: [unserializable]")
            if node_state.get("errors"):
                print("❌ Errors:", node_state.get("errors"))
            final_state = node_state
        
        if not final_state:
            return {
                "status": "error",
                "errors": ["Graph produced no final state"]
            }

        return {
            "status": "success" if not final_state.get("errors") else "error",
            "evaluation": final_state.get("evaluation", {}) or {},
            "explanation": final_state.get("explanation", {}) or {},
            "artifacts": final_state.get("artifacts", {}) or {},
            "context": final_state.get("context", {}) or {},
            "errors": final_state.get("errors", []) or [],
        }

    except Exception as e:
        print(f"[EXCEPTION] {str(e)}")
        return {
            "status": "error",
            "errors": [f"Workflow error: {str(e)}"]
        }
        