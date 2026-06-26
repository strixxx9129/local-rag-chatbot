# backend/src/graph/nodes/query_analyzer.py
"""
Query analyzer node — the entry point of the graph.

Responsibilities:
  1. Classify the query type:
       "greeting"      → "hello", "hi", "thanks" etc.
       "direct"        → general question not needing document retrieval
       "rag"           → question that needs document retrieval
       "clarification" → user asking about the chatbot itself

  2. Condense follow-up questions into standalone questions.
     "What about the second point?" with history →
     "What is the second point discussed in the document?"

  3. Load conversation history from the DB for multi-turn context.

Why classify first?
  Routing "hello" through the full RAG pipeline wastes 2-4 seconds
  on embedding + retrieval + LLM generation when a simple direct
  response would take 0.5 seconds.
"""
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import logger
from src.graph.state import GraphState
from src.rag.llm_service import generate_answer_async
from src.rag.prompt_templates import build_standalone_question_prompt
from src.repositories.conversation_repository import ConversationRepository


# ── Simple keyword-based classifiers (fast, no LLM needed) ───────────────────

GREETING_PATTERNS = re.compile(
    r"^\s*(hi|hello|hey|howdy|greetings|good\s+(morning|afternoon|evening)|thanks|thank\s+you|bye|goodbye)\s*[!?.]*\s*$",
    re.IGNORECASE,
)

CLARIFICATION_PATTERNS = re.compile(
    r"(what can you do|who are you|what are you|how do you work|what is your purpose|help me understand you)",
    re.IGNORECASE,
)

DIRECT_PATTERNS = re.compile(
    r"^\s*(what is|what are|define|explain|describe|tell me about|who is|when was|where is)\s+(?!this document|the document|this file|the file)",
    re.IGNORECASE,
)


def _classify_query(question: str) -> str:
    """
    Fast keyword-based query classification.

    Returns one of: "greeting", "clarification", "direct", "rag"
    """
    if GREETING_PATTERNS.match(question):
        return "greeting"
    if CLARIFICATION_PATTERNS.search(question):
        return "clarification"
    # Default to "rag" — retrieval is always safer than skipping it
    return "rag"


async def _condense_question(
    question: str,
    history: list[dict],
) -> str:
    """
    If there is conversation history, ask the LLM to rephrase the
    follow-up question as a standalone question.

    Returns the original question unchanged if history is empty or
    the question is already self-contained.
    """
    if not history:
        return question

    # Only condense if the question looks like a follow-up
    follow_up_signals = [
        "it", "they", "them", "that", "this", "those", "these",
        "the same", "also", "and", "but", "what about", "how about",
        "why", "what else", "more about",
    ]
    question_lower = question.lower()
    is_follow_up = any(
        question_lower.startswith(signal) or f" {signal} " in question_lower
        for signal in follow_up_signals
    )

    if not is_follow_up:
        return question

    # Build history string for the condensation prompt
    history_str = "\n".join(
        f"{turn['role'].upper()}: {turn['content']}"
        for turn in history[-4:]   # last 2 turns
    )

    messages = build_standalone_question_prompt(
        history=history_str,
        question=question,
    )

    try:
        standalone = await generate_answer_async(
            messages,
            temperature=0.0,   # deterministic condensation
            max_tokens=200,
        )
        logger.info(
            "query_analyzer.condensed",
            original=question,
            standalone=standalone,
        )
        return standalone.strip()
    except Exception as exc:
        logger.warning("query_analyzer.condense_failed", error=str(exc))
        return question   # fall back to original on error


async def query_analyzer_node(
    state: GraphState,
    *,
    session: AsyncSession,
) -> GraphState:
    """
    LangGraph node: analyze query, condense if follow-up, load history.
    """
    question = state["question"]
    conversation_id = state.get("conversation_id")
    user_id = state["user_id"]

    logger.info(
        "node.query_analyzer.start",
        question=question[:80],
        conversation_id=conversation_id,
    )

    repo = ConversationRepository(session)

    # ── Load or create conversation ───────────────────────────────────────────
    if conversation_id:
        convo = await repo.get_conversation(uuid.UUID(conversation_id))
        if convo and convo.user_id == uuid.UUID(user_id):
            history = [
                {"role": msg.role.value, "content": msg.content}
                for msg in await repo.get_recent_messages(
                    convo.id, limit=6
                )
            ]
            resolved_convo_id = str(convo.id)
        else:
            history = []
            resolved_convo_id = conversation_id
    else:
        # Create new conversation
        title = question[:60] + ("..." if len(question) > 60 else "")
        convo = await repo.create_conversation(
            user_id=uuid.UUID(user_id),
            document_id=uuid.UUID(state["document_id"]) if state.get("document_id") else None,
            title=title,
        )
        await session.commit()
        history = []
        resolved_convo_id = str(convo.id)

    # ── Classify query ────────────────────────────────────────────────────────
    query_type = _classify_query(question)

    # ── Condense follow-up if needed ──────────────────────────────────────────
    standalone = await _condense_question(question, history)

    needs_retrieval = query_type == "rag"

    logger.info(
        "node.query_analyzer.complete",
        query_type=query_type,
        needs_retrieval=needs_retrieval,
        has_history=bool(history),
    )

    return {
        **state,
        "query_type": query_type,
        "standalone_question": standalone,
        "needs_retrieval": needs_retrieval,
        "conversation_history": history,
        "resolved_conversation_id": resolved_convo_id,
        "error": None,
    }