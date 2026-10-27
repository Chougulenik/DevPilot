from .base import BaseChunker
from .recursive import RecursiveChunker
from .semantic import SemanticChunker
from .agentic import AgenticChunker


def get_chunker(
    strategy: str = "recursive",
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
) -> BaseChunker:
    """Factory creating appropriate chunker instance according to strategy name."""
    strategy_clean = strategy.lower().strip()
    if strategy_clean == "semantic":
        return SemanticChunker()
    elif strategy_clean == "agentic":
        return AgenticChunker(target_chunk_chars=chunk_size)
    else:
        return RecursiveChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


__all__ = [
    "BaseChunker",
    "RecursiveChunker",
    "SemanticChunker",
    "AgenticChunker",
    "get_chunker",
]
