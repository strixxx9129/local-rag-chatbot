# backend/src/graph/builder.py
"""
Updated graph topology with memory node:

  [START]
     │
     ▼
  query_analyzer
     │
     ▼
  memory_node          ← NEW: retrieve long-term memories
     │
     ▼
  should_retrieve?
     │
  ┌──┴──────────┐
retrieve    skip_retrieve
  │               │
  ▼               │
should_build_context?
  │               │
build_context  generate◄─┘
  │               │
  └──────►generate
             │
             ▼
        should_cite?
             │
      ┌──────┴──────┐
     cite           end
      │              │
      └──────┬───────┘
             ▼
           [END]
"""
import functools

from langgraph.graph import END, START, StateGraph

from src.graph.edges import should_build_context, should_cite, should_retrieve
from src.graph.nodes.citation_builder import citation_builder_node
from src.graph.nodes.context_builder import context_builder_node
from src.graph.nodes.generator import generator_node
from src.graph.nodes.memory import memory_node                    # ← NEW
from src.graph.nodes.query_analyzer import query_analyzer_node
from src.graph.nodes.retriever import retriever_node
from src.graph.state import GraphState


def build_rag_graph_with_session(session):
    """
    Build and compile the RAG graph with session-injected nodes.

    Called per-request in GraphService with the request's AsyncSession.
    """
    graph = StateGraph(GraphState)

    # ── Register nodes ────────────────────────────────────────────────────────
    graph.add_node(
        "query_analyzer",
        functools.partial(query_analyzer_node, session=session),
    )
    graph.add_node(
        "memory",                                                   # ← NEW
        functools.partial(memory_node, session=session),
    )
    graph.add_node(
        "retriever",
        functools.partial(retriever_node, session=session),
    )
    graph.add_node("context_builder", context_builder_node)
    graph.add_node(
        "generator",
        functools.partial(generator_node, session=session),
    )
    graph.add_node(
        "citation_builder",
        functools.partial(citation_builder_node, session=session),
    )

    # ── Edges ─────────────────────────────────────────────────────────────────
    graph.add_edge(START, "query_analyzer")
    graph.add_edge("query_analyzer", "memory")                     # ← NEW

    graph.add_conditional_edges(
        "memory",                                                   # ← FROM memory
        should_retrieve,
        {
            "retrieve": "retriever",
            "skip_retrieve": "generator",
        },
    )
    graph.add_conditional_edges(
        "retriever",
        should_build_context,
        {
            "build_context": "context_builder",
            "generate": "generator",
        },
    )
    graph.add_edge("context_builder", "generator")
    graph.add_conditional_edges(
        "generator",
        should_cite,
        {
            "cite": "citation_builder",
            "end": END,
        },
    )
    graph.add_edge("citation_builder", END)

    return graph.compile()