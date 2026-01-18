"""FastAPI application for Fed RAG API."""

import os
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..config import Config
from ..services.query_pipeline import QueryPipeline

app = FastAPI(
    title="Fed RAG API",
    description="Query Federal Reserve documents using RAG",
    version="0.1.0",
)

# CORS configuration
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://fedrag.vercel.app",
]
# Add production frontend URL from env
if frontend_url := os.getenv("FRONTEND_URL"):
    ALLOWED_ORIGINS.append(frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-load pipeline (heavy initialization)
_pipeline: QueryPipeline | None = None


def get_pipeline() -> QueryPipeline:
    """Get or create the query pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        _pipeline = QueryPipeline(Config())
    return _pipeline


class HistoryMessage(BaseModel):
    """A message in the conversation history."""

    role: Literal["user", "assistant"]
    content: str


class QueryRequest(BaseModel):
    """Request body for query endpoint."""

    question: str
    history: list[HistoryMessage] = []


class SourceResponse(BaseModel):
    """A source document returned with the query response."""

    chunk_id: str
    doc_id: str
    text: str
    score: float
    rerank_score: float
    doc_type: str
    speaker: str | None
    date: str
    title: str
    url: str


class QueryResponse(BaseModel):
    """Response body for query endpoint."""

    answer: str
    sources: list[SourceResponse]
    tool_calls_made: int


@app.post("/api/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    """Query Federal Reserve documents.

    Takes a natural language question and returns an answer
    with relevant source documents.
    """
    history = [{"role": msg.role, "content": msg.content} for msg in request.history]
    result = get_pipeline().query(request.question, history=history)
    return QueryResponse(
        answer=result.answer,
        sources=[
            SourceResponse(
                chunk_id=s.chunk_id,
                doc_id=s.doc_id,
                text=s.text,
                score=s.score,
                rerank_score=s.rerank_score,
                doc_type=s.doc_type,
                speaker=s.speaker,
                date=s.date,
                title=s.title,
                url=s.url,
            )
            for s in result.sources
        ],
        tool_calls_made=result.tool_calls_made,
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
