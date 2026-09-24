from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.graph import graph
from app.models import AskRequest, AskResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Importing graph initializes the retriever and ensures
    # the Chroma collection exists.
    yield


app = FastAPI(
    title="Zepto Support Assistant",
    description="RAG-powered Zepto policy support service",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {
        "service": "Zepto Support Assistant",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    query = request.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty.",
        )

    result = graph.invoke({"query": query})

    return AskResponse(
        answer=result.get("answer", ""),
        sources=result.get("sources", []),
        confidence=result.get("confidence", 0.0),
    )