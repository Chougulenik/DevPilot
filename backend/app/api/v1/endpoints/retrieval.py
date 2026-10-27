import time
from fastapi import APIRouter, Depends, HTTPException
from ....schemas.retrieval import RetrievalRequest, RetrievalResponse
from ....services.retrieval import get_retriever
from ....services.vector_store import VectorStoreManager, get_vector_store
from ....core.logging import get_logger

logger = get_logger("retrieval_endpoint")
router = APIRouter(prefix="/retrieval", tags=["Retrieval Engine"])


@router.post("/query", response_model=RetrievalResponse)
async def query_retrieval(
    request: RetrievalRequest,
    vector_store: VectorStoreManager = Depends(get_vector_store),
):
    """Execute comparative retrieval query across any of the 5 supported strategies."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    start_time = time.perf_counter()
    try:
        retriever = get_retriever(strategy=request.strategy, vector_store=vector_store)
        results = retriever.retrieve(
            query=request.query,
            k=request.k,
            score_threshold=request.score_threshold,
        )
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return RetrievalResponse(
            query=request.query,
            strategy=request.strategy,
            latency_ms=elapsed_ms,
            total_results=len(results),
            results=results,
        )
    except Exception as e:
        logger.error(f"Retrieval failed for strategy '{request.strategy}': {e}")
        raise HTTPException(status_code=500, detail=f"Retrieval query failed: {str(e)}")
