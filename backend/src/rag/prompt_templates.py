# backend/src/rag/prompt_templates.py
RAG_SYSTEM_PROMPT = """You are a precise and helpful document assistant.
Your job is to answer the user's question using the provided source excerpts.

Rules you must follow:
1. Base your answer primarily on the provided sources. Do not fabricate facts.
2. When you use information from a source, cite it as [Source N] inline.
3. If past context is provided, use it to understand follow-up questions.
4. If the sources do not contain enough information, say:
   "I couldn't find enough information in the provided documents to answer this."
5. Be concise and direct. Avoid repeating the question back to the user.
6. If sources contradict each other, mention the discrepancy.
7. Never fabricate facts, page numbers, or quotes."""


def build_rag_prompt(
    question: str,
    context: str,
    conversation_history: list[dict] | None = None,
    memory_context: str | None = None,      # ← NEW parameter
) -> list[dict]:
    """
    Build the messages list for Ollama chat completion.

    Memory context (past conversation summaries) is injected BEFORE
    the document context so the LLM processes prior knowledge first,
    then grounds its answer in current document chunks.
    """
    messages: list[dict] = [
        {"role": "system", "content": RAG_SYSTEM_PROMPT},
    ]

    # Inject prior conversation turns
    if conversation_history:
        messages.extend(conversation_history)

    # Build user message with optional memory + document context
    content_parts: list[str] = []

    if memory_context:
        content_parts.append(
            f"Relevant context from past conversations:\n\n{memory_context}"
        )

    if context:
        content_parts.append(
            f"Relevant excerpts from your documents:\n\n{context}"
        )

    if content_parts:
        content_parts.append(f"---\n\nQuestion: {question}")
        user_content = "\n\n".join(content_parts)
    else:
        user_content = (
            f"No relevant document excerpts were found.\n\n"
            f"Question: {question}"
        )

    messages.append({"role": "user", "content": user_content})
    return messages


CONDENSE_QUESTION_PROMPT = """Given the following conversation history and a follow-up question,
rephrase the follow-up question to be a standalone question that captures all necessary context.

Conversation history:
{history}

Follow-up question: {question}

Standalone question:"""


def build_standalone_question_prompt(
    history: str,
    question: str,
) -> list[dict]:
    return [
        {
            "role": "user",
            "content": CONDENSE_QUESTION_PROMPT.format(
                history=history,
                question=question,
            ),
        }
    ]