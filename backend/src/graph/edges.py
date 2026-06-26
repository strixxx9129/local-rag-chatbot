# backend/src/graph/edges.py
"""
Conditional edge functions for the LangGraph agent.

Edge functions read the current state and return a string key
that selects the next node. They must be pure — no side effects,
no async, no DB calls.

Available return values must match node names registered in the graph.
"""
from src.graph.state import GraphState


def should_retrieve(state: GraphState) -> str:
    """
    After query_analyzer: decide whether to retrieve documents.

    Routes:
      "retrieve"      → needs_retrieval=True, go to retriever_node
      "skip_retrieve" → needs_retrieval=False, go directly to generator_node
    """
    # If there's an error from the analyzer, skip retrieval
    if state.get("error"):
        return "skip_retrieve"

    if state.get("needs_retrieval", True):
        return "retrieve"

    return "skip_retrieve"


def should_build_context(state: GraphState) -> str:
    """
    After retriever: decide whether we have chunks to build context from.

    Routes:
      "build_context" → chunks found, assemble context
      "generate"      → no chunks (empty doc or threshold miss),
                        generate directly with empty context
    """
    if state.get("error"):
        return "generate"

    chunks = state.get("retrieved_chunks", [])
    if chunks:
        return "build_context"

    return "generate"


def should_cite(state: GraphState) -> str:
    """
    After generator: decide whether there are chunks to cite.

    Routes:
      "cite"    → used_chunks exist, build citations
      "end"     → no chunks (greeting/direct), skip citations
    """
    used_chunks = state.get("used_chunks", [])
    if used_chunks and state.get("resolved_message_id"):
        return "cite"
    return "end"