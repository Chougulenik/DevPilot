from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ChatRole(str, Enum):
    """Permitted conversational message roles."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """Individual conversational message record."""
    role: str = Field(description="Message role: user, assistant, system")
    content: str = Field(description="Message text body")
    timestamp: Optional[str] = Field(default=None, description="Optional client timestamp")


class Citation(BaseModel):
    """Reference citation linking response claims to source chunk text."""
    id: int = Field(description="Citation index (1-based: [1], [2], etc.)")
    source: str = Field(description="Document source path or filename")
    content: str = Field(description="Excerpt snippet of the cited chunk")
    score: Optional[float] = Field(default=None, description="Relevance similarity score")


class ChatRequest(BaseModel):
    """Payload for POST /api/v1/chat/completions and /api/v1/chat/stream."""
    message: str = Field(description="Latest user prompt / question")
    history: List[ChatMessage] = Field(default_factory=list, description="Prior conversation messages")
    strategy: str = Field(default="vector", description="Retrieval strategy: vector, multi_query, rrf, hybrid, rerank")
    k: int = Field(default=4, ge=1, le=20, description="Number of context chunks to retrieve")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0, description="LLM sampling temperature")


class ChatResponse(BaseModel):
    """Response returned by POST /api/v1/chat/completions."""
    answer: str = Field(description="Grounded assistant answer")
    citations: List[Citation] = Field(default_factory=list, description="Extracted chunk citations")
    rewritten_query: Optional[str] = Field(default=None, description="History-aware standalone query")
