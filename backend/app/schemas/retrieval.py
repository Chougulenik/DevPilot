from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class RetrievalStrategyEnum(str, Enum):
    """Supported retrieval strategy modes."""
    VECTOR = "vector"
    MULTI_QUERY = "multi_query"
    RRF = "rrf"
    HYBRID = "hybrid"
    RERANK = "rerank"


class RetrievalRequest(BaseModel):
    """Payload for POST /api/v1/retrieval/query."""
    query: str = Field(description="Search or natural language question")
    strategy: str = Field(default="vector", description="Strategy: vector, multi_query, rrf, hybrid, rerank")
    k: int = Field(default=5, ge=1, le=50, description="Top-k number of chunks to return")
    score_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score filter")


class RetrievalResultItem(BaseModel):
    """An individual retrieved chunk result with ranking information."""
    rank: Optional[int] = Field(default=None, description="Ordinal rank position (1-based)")
    content: str = Field(description="Retrieved chunk text content")
    source: str = Field(description="Document source path or filename")
    score: Optional[float] = Field(default=None, description="Calculated similarity or fusion score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Original chunk metadata")


class RetrievalResponse(BaseModel):
    """Response returned by POST /api/v1/retrieval/query."""
    query: str
    strategy: str
    latency_ms: int = Field(description="Execution latency in milliseconds")
    total_results: int = Field(description="Number of results returned")
    results: List[RetrievalResultItem] = Field(default_factory=list)
