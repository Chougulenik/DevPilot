from abc import ABC, abstractmethod
from typing import List
from ...schemas.retrieval import RetrievalResultItem


class BaseRetriever(ABC):
    """Abstract interface for all retrieval strategies."""

    @abstractmethod
    def retrieve(
        self, query: str, k: int = 5, score_threshold: float = 0.0
    ) -> List[RetrievalResultItem]:
        """Execute retrieval logic and return ranked chunk items."""
        pass
