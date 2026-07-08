"""FastAPI backend for UmarTransit-1B.

Serves the model as a REST API with a single /api/chat endpoint.

Run locally:
    uvicorn app.api.main:app --port 8000

Deploy to HuggingFace Spaces:
    See Dockerfile in this directory.
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
