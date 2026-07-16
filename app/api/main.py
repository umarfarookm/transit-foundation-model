"""FastAPI backend for UmarTransit-1B.

Serves the model as a REST API with a single /api/chat endpoint.

Run locally:
    uvicorn app.api.main:app --port 8000

Deploy to HuggingFace Spaces:
    See Dockerfile in this directory.
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.feed_explorer import (
    build_feed_prompt,
    explore_feed_from_zip,
    get_session,
    store_session,
)
from inference.run_local import ask, load_model

# Global model references (loaded once at startup)
_model = None
_tokenizer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model at startup, cleanup at shutdown."""
    global _model, _tokenizer
    print("Loading UmarTransit-1B model...")
    _model, _tokenizer = load_model()
    print("Model ready!")
    yield
    print("Shutting down...")


app = FastAPI(
    title="UmarTransit-1B API",
    description="A transit-domain AI assistant powered by UmarTransit-1B",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow cross-origin requests from any frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    tokens: int
    time_seconds: float


class FeedUploadResponse(BaseModel):
    upload_id: str | None
    validation: dict
    summary: dict | None


class FeedAskRequest(BaseModel):
    upload_id: str
    question: str


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "model_loaded": _model is not None,
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Generate a response to a transit/GTFS question."""
    if _model is None or _tokenizer is None:
        return ChatResponse(answer="Model is still loading. Please try again.", tokens=0, time_seconds=0)

    start = time.time()
    answer = ask(_model, _tokenizer, request.question)
    elapsed = time.time() - start

    # Rough token count from response length
    tokens = len(answer.split())

    return ChatResponse(
        answer=answer,
        tokens=tokens,
        time_seconds=round(elapsed, 1),
    )


# ── Feed Explorer endpoints ──────────────────────────────────────────────────


@app.post("/api/feed/upload", response_model=FeedUploadResponse)
async def upload_feed(file: UploadFile):
    """Upload a GTFS ZIP, validate it, and extract summary stats."""
    zip_bytes = await file.read()
    validation, summary = explore_feed_from_zip(zip_bytes)

    upload_id = None
    if summary is not None:
        upload_id = store_session(summary)

    return FeedUploadResponse(
        upload_id=upload_id,
        validation=validation,
        summary=summary,
    )


@app.post("/api/feed/ask", response_model=ChatResponse)
def ask_feed(request: FeedAskRequest):
    """Answer a question about an uploaded GTFS feed."""
    summary = get_session(request.upload_id)
    if summary is None:
        return ChatResponse(
            answer="Feed session expired or not found. Please re-upload the feed.",
            tokens=0,
            time_seconds=0,
        )

    if _model is None or _tokenizer is None:
        return ChatResponse(answer="Model is still loading. Please try again.", tokens=0, time_seconds=0)

    prompt = build_feed_prompt(request.question, summary)

    start = time.time()
    answer = ask(_model, _tokenizer, prompt)
    elapsed = time.time() - start

    return ChatResponse(
        answer=answer,
        tokens=len(answer.split()),
        time_seconds=round(elapsed, 1),
    )


@app.get("/api/feed/{upload_id}/summary")
def get_feed_summary(upload_id: str):
    """Retrieve the stored summary for an uploaded feed."""
    summary = get_session(upload_id)
    if summary is None:
        return {"error": "Feed session expired or not found."}
    return summary
