# backend/src/graph/nodes/retriever.py
"""
Retriever node — executes hybrid or vector search.

Reads:  standalone_question, use_hybrid, user_id, document_id, top_k
Writes: retrieved_chunks (list of dicts), retrieval_mode
"""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import logger
from src.graph.state import GraphState
from src.rag.hybrid_retriever import hybrid_retrieve
from src.rag.llm_service import embed_query_async
from src.rag.reranker import diversify_results
from src.rag.retriever import retrieve_similar_chunks
from src.schemas.rag import RetrievedChunk


def _chunk_to_dict(chunk: RetrievedChunk) -> dict:
    return {
        "chunk_id": str(chunk.chunk_id),
        "document_id": str(chunk.document_id),
        "document_title": chunk.document_title,
        "content": chunk.content,
        "page_number": chunk.page_number,
        "chunk_index": chunk.chunk_index,
        "similarity_score": chunk.similarity_score,
    }


async def retriever_node(
    state: GraphState,
    *,
    session: AsyncSession,
) -> GraphState:
    """
    LangGraph node: retrieve relevant chunks for the query.
    """
    question = state.get("standalone_question") or state["question"]
    user_id = uuid.UUID(state["user_id"])
    document_id = (
        uuid.UUID(state["document_id"]) if state.get("document_id") else None
    )
    top_k = state.get("top_k", 5)
    use_hybrid = state.get("use_hybrid", True)
    vector_weight = state.get("vector_weight", 0.6)
    fts_weight = state.get("fts_weight", 0.4)

    logger.info(
        "node.retriever.start",
        question=question[:80],
        use_hybrid=use_hybrid,
        top_k=top_k,
    )

    try:
        # Embed the query
        query_embedding = await embed_query_async(question)

        if use_hybrid:
            raw_chunks = await hybrid_retrieve(
                session,
                query=question,
                query_embedding=query_embedding,
                user_id=user_id,
                document_id=document_id,
                top_k=top_k * 2,
                vector_weight=vector_weight,
                fts_weight=fts_weight,
            )
            chunks = diversify_results(raw_chunks)[:top_k]
            retrieval_mode = "hybrid"
        else:
            chunks = await retrieve_similar_chunks(
                session,
                query_embedding=query_embedding,
                user_id=user_id,
                document_id=document_id,
                top_k=top_k,
            )
            retrieval_mode = "vector"

        chunk_dicts = [_chunk_to_dict(c) for c in chunks]

        logger.info(
            "node.retriever.complete",
            mode=retrieval_mode,
            chunks_found=len(chunk_dicts),
        )

        return {
            **state,
            "retrieved_chunks": chunk_dicts,
            "retrieval_mode": retrieval_mode,
            "error": None,
        }

    except Exception as exc:
        logger.exception("node.retriever.failed", error=str(exc))
        return {
            **state,
            "retrieved_chunks": [],
            "retrieval_mode": "none",
            "error": f"Retrieval failed: {exc}",
        }