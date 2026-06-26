# backend/src/graph/state.py
"""
LangGraph state definition.

GraphState is the single shared data structure passed between every node.
Each node reads what it needs and writes back its outputs.

Design rules:
  - All fields are Optional with None defaults — nodes only populate
    the fields they're responsible for.
  - Never delete keys from state — LangGraph merges state dicts,
    so missing keys cause KeyErrors in downstream nodes.
  - UUIDs are stored as strings — TypedDict doesn't serialize uuid.UUID
    cleanly across LangGraph's internal serialization layer.
"""
from typing import Any, TypedDict
import uuid


class GraphState(TypedDict, total=False):
    # ── Input (set by the caller before graph execution) ─────────────────────
    question: str                       # raw user question
    user_id: str                        # UUID string
    document_id: str | None            # UUID string or None (cross-doc search)
    conversation_id: str | None        # UUID string or None (new conversation)
    top_k: int                          # max chunks to retrieve
    use_hybrid: bool                    # hybrid vs vector-only search
    vector_weight: float
    fts_weight: float

    # ── Query analysis (set by query_analyzer_node) ───────────────────────────
    query_type: str                     # "rag" | "direct" | "greeting" | "clarification"
    standalone_question: str            # condensed question (for follow-ups)
    needs_retrieval: bool               # True → go to retriever, False → direct LLM
    
    # ── Memory (set by memory_node) ───────────────────────────────────────────
    long_term_memories: list[dict]      # retrieved past conversation memories
    memory_context: str                 # formatted memory block for prompt
    query_embedding: list[float]        # reusable embedding for retrieval

    # ── Retrieval (set by retriever_node) ─────────────────────────────────────
    retrieved_chunks: list[dict]        # list of RetrievedChunk dicts
    retrieval_mode: str                 # "hybrid" | "vector" | "none"

    # ── Context (set by context_builder_node) ─────────────────────────────────
    context_string: str                 # assembled context block for prompt
    used_chunks: list[dict]             # chunks that fit in token budget

    # ── Generation (set by generator_node) ────────────────────────────────────
    answer: str                         # LLM-generated answer
    prompt_messages: list[dict]         # the actual messages sent to Ollama

    # ── Citations (set by citation_builder_node) ───────────────────────────────
    citations: list[dict]               # CitationResponse dicts

    # ── Conversation (set by query_analyzer_node + generator_node) ────────────
    conversation_history: list[dict]    # prior [role, content] turns
    resolved_conversation_id: str       # UUID string — created or existing

    # ── Error (set by any node on failure) ────────────────────────────────────
    error: str | None                   # human-readable error message
