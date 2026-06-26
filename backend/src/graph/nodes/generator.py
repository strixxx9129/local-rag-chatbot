# backend/src/graph/nodes/generator.py
"""
Generator node — calls Ollama and enqueues background summarization.
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import logger
from src.graph.state import GraphState
from src.models.message import MessageRole
from src.rag.llm_service import generate_answer_async
from src.rag.prompt_templates import build_rag_prompt
from src.repositories.conversation_repository import ConversationRepository

GREETING_RESPONSES = {
    "greeting": (
        "Hello! I'm your document assistant. Upload a PDF and ask me anything "
        "about its content — I'll find the relevant sections and answer with citations."
    ),
    "clarification": (
        "I'm a RAG (Retrieval-Augmented Generation) assistant. "
        "I search your uploaded documents and answer questions based on their content. "
        "Upload a PDF using the Documents page, then ask me questions about it here."
    ),
}

DIRECT_SYSTEM_PROMPT = """You are a helpful assistant. Answer the user's question
concisely and accurately. If you don't know, say so."""


async def generator_node(
    state: GraphState,
    *,
    session: AsyncSession,
) -> GraphState:
    """
    LangGraph node: generate the answer and persist messages to DB.
    Also enqueues background memory summarization.
    """
    query_type = state.get("query_type", "rag")
    question = state.get("standalone_question") or state["question"]
    original_question = state["question"]
    context_string = state.get("context_string", "")
    memory_context = state.get("memory_context", "")       # ← NEW
    history = state.get("conversation_history", [])
    convo_id = uuid.UUID(state["resolved_conversation_id"])

    repo = ConversationRepository(session)

    logger.info(
        "node.generator.start",
        query_type=query_type,
        conversation_id=str(convo_id),
        has_context=bool(context_string),
        has_memory=bool(memory_context),
    )

    # ── Path 1: Static responses ──────────────────────────────────────────────
    if query_type in GREETING_RESPONSES:
        answer = GREETING_RESPONSES[query_type]
        messages = [{"role": "user", "content": original_question}]

    # ── Path 2: RAG or direct ─────────────────────────────────────────────────
    else:
        if query_type == "rag" or context_string:
            messages = build_rag_prompt(
                question=question,
                context=context_string,
                conversation_history=history,
                memory_context=memory_context,             # ← NEW
            )
        else:
            messages = [
                {"role": "system", "content": DIRECT_SYSTEM_PROMPT},
                *history,
                {"role": "user", "content": question},
            ]

        try:
            answer = await generate_answer_async(messages)
        except Exception as exc:
            logger.exception("node.generator.llm_failed", error=str(exc))
            answer = "I encountered an error generating a response. Please try again."

    # ── Persist messages ──────────────────────────────────────────────────────
    try:
        await repo.add_message(
            conversation_id=convo_id,
            role=MessageRole.USER,
            content=original_question,
            token_count=len(original_question) // 4,
        )
        assistant_msg = await repo.add_message(
            conversation_id=convo_id,
            role=MessageRole.ASSISTANT,
            content=answer,
            token_count=len(answer) // 4,
        )
        await session.commit()
        assistant_msg_id = str(assistant_msg.id)
    except Exception as exc:
        logger.exception("node.generator.persist_failed", error=str(exc))
        assistant_msg_id = str(uuid.uuid4())

    # ── Enqueue background summarization ──────────────────────────────────────
    try:
        from src.workers.memory_worker import summarize_conversation
        from src.workers.queue import memory_queue

        memory_queue.enqueue(
            summarize_conversation,
            args=(str(convo_id),),
            job_id=f"mem-{convo_id}-{assistant_msg_id[:8]}",
        )
        logger.info(
            "node.generator.memory_enqueued",
            conversation_id=str(convo_id),
        )
    except Exception as exc:
        # Non-fatal — memory summarization failure never blocks the response
        logger.warning(
            "node.generator.memory_enqueue_failed",
            error=str(exc),
        )

    logger.info(
        "node.generator.complete",
        answer_length=len(answer),
        message_id=assistant_msg_id,
    )

    return {
        **state,
        "answer": answer,
        "prompt_messages": messages,
        "resolved_message_id": assistant_msg_id,
        "error": None,
    }