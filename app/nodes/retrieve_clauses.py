from typing import Dict, Any, List
import os
import logging

try:
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings
    _RAG_AVAILABLE = True
except Exception:
    _RAG_AVAILABLE = False

logger = logging.getLogger(__name__)

CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "data/chroma")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


def _safe_get_action(state: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(state.get("action"), dict):
        return state["action"]
    ctx = state.get("context", {}) or {}
    return ctx.get("action", {}) or {}


def retrieve_clauses(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve relevant MAS framework clauses using Chroma RAG.
    If retrieval fails or is unavailable, return a robust fallback clause so
    downstream nodes can still produce a meaningful result.
    """
    try:
        ctx = state.get("context", {}) or {}
        action = _safe_get_action(state)

        search_query = (
            f"Sector: {action.get('sector', '')}\n"
            f"Activity: {action.get('activity', '')}\n"
            f"Description: {action.get('description', '')}"
        )
        logger.info("[retrieve_clauses] Query:\n%s", search_query)

        clauses: List[str] = []
        errors: List[str] = list(state.get("errors", []))

        if _RAG_AVAILABLE and os.path.isdir(CHROMA_DB_PATH) and os.listdir(CHROMA_DB_PATH):
            try:
                embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
                vectorstore = Chroma(
                    persist_directory=CHROMA_DB_PATH,
                    embedding_function=embeddings
                )
                docs = vectorstore.similarity_search(search_query, k=5)
                if docs:
                    clauses = [d.page_content for d in docs if getattr(d, "page_content", None)]
                    logger.info("[retrieve_clauses] Retrieved %d clauses from Chroma", len(clauses))
                else:
                    logger.warning("[retrieve_clauses] No clauses from Chroma; using fallback.")
            except Exception as rag_err:
                msg = f"RAG retrieval error: {rag_err}"
                logger.warning(msg)
                errors.append(msg)
        else:
            if not _RAG_AVAILABLE:
                errors.append("RAG dependencies missing")
                logger.warning("[retrieve_clauses] RAG deps not available; using fallback.")
            else:
                errors.append("Chroma index missing or empty")
                logger.warning("[retrieve_clauses] Chroma index not found/empty at %s; using fallback.", CHROMA_DB_PATH)

        if not clauses:
            fallback = (
                "Green: Project aligns with renewable generation pathways for the Energy sector. "
                "Environmental Impact Assessment required; Water conservation plan required; "
                "Biodiversity safeguards required. Ineligible if lifecycle emissions exceed thresholds."
            )
            clauses = [fallback]

        new_ctx = {
            **ctx,
            "action": action,
            "clauses": clauses,
            "search_query": search_query
        }

        return {**state, "status": "success", "context": new_ctx, "errors": errors}

    except Exception as e:
        logger.exception("[retrieve_clauses] Unexpected failure; returning fallback clause.")
        fallback = "Ineligible: Fails eligibility criteria. Environmental Impact Assessment required."
        new_ctx = {
            **state.get("context", {}),
            "action": _safe_get_action(state),
            "clauses": [fallback],
            "search_query": "fallback"
        }
        errs = list(state.get("errors", [])) + [f"Error in retrieve_clauses: {e}"]
        return {**state, "status": "success", "context": new_ctx, "errors": errs}
