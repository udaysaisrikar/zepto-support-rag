from typing import Literal

from langgraph.graph import StateGraph, START, END

from app.models import GraphState
from app.retrieval import PolicyRetriever
from app.config import MOCK_LLM
from app.prompts import build_support_prompt


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

retriever = PolicyRetriever()

POLICY_KEYWORDS = [
    "delivery",
    "return",
    "refund",
    "membership",
    "tracking",
    "cancel",
    "gift card",
    "support hours",
]


# ---------------------------------------------------------
# Node 1: Classify Intent
# ---------------------------------------------------------

def classify_intent(state: GraphState) -> GraphState:
    query = state["query"]
    query_lower = query.lower()

    is_policy_question = any(
        keyword in query_lower
        for keyword in POLICY_KEYWORDS
    )

    if is_policy_question:
        intent = "policy_question"
    else:
        intent = "general_question"

    return {
        "intent": intent,
    }


# ---------------------------------------------------------
# Node 2: Retrieve and Answer
# ---------------------------------------------------------

def retrieve_and_answer(state: GraphState) -> GraphState:
    query = state["query"]
    chunks = retriever.retrieve(query=query, top_k=3)

    if not chunks:
        return {
            "retrieved_chunks": [],
            "answer": "No relevant policy information was found.",
            "sources": [],
            "confidence": 0.0,
        }

    context = "\n\n".join(
        f"[{chunk['chunk_id']}] {chunk['text']}"
        for chunk in chunks
    )

    # Prompt is constructed here so the generation layer is ready
    # for a real LLM in a future phase.
    _prompt = build_support_prompt(query=query, context=context)

    top_chunk = chunks[0]

    if MOCK_LLM:
        answer = f"Based on the retrieved context: {top_chunk['text']}"
    else:
        # Real LLM integration is intentionally optional for this baseline.
        # Keep deterministic behavior when no provider is configured.
        answer = f"Based on the retrieved context: {top_chunk['text']}"

    return {
        "retrieved_chunks": chunks,
        "answer": answer,
        "sources": [chunk["chunk_id"] for chunk in chunks],
        "confidence": 1.0,
    }

# ---------------------------------------------------------
# Node 3: Direct Answer
# ---------------------------------------------------------

def direct_answer(state: GraphState) -> GraphState:
    return {
        "answer": "I can only answer questions about Zepto policies right now.",
        "sources": [],
        "confidence": 1.0,
    }


# ---------------------------------------------------------
# Conditional Routing
# ---------------------------------------------------------

def route_intent(
    state: GraphState,
) -> Literal["retrieve_and_answer", "direct_answer"]:

    if state["intent"] == "policy_question":
        return "retrieve_and_answer"

    return "direct_answer"


# ---------------------------------------------------------
# Build LangGraph
# ---------------------------------------------------------

builder = StateGraph(GraphState)

builder.add_node(
    "classify_intent",
    classify_intent,
)

builder.add_node(
    "retrieve_and_answer",
    retrieve_and_answer,
)

builder.add_node(
    "direct_answer",
    direct_answer,
)

builder.add_edge(
    START,
    "classify_intent",
)

#conditional edge
builder.add_conditional_edges(
    "classify_intent",
    route_intent,
    {
        "retrieve_and_answer": "retrieve_and_answer",
        "direct_answer": "direct_answer",
    },
)

builder.add_edge(
    "retrieve_and_answer",
    END,
)

builder.add_edge(
    "direct_answer",
    END,
)

graph = builder.compile()