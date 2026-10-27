from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from ....schemas.chat import ChatRequest, ChatResponse
from ....services.chat_service import ChatService, get_chat_service
from ....core.logging import get_logger

logger = get_logger("chat_endpoint")
router = APIRouter(prefix="/chat", tags=["Conversational Chat"])


@router.post("/completions", response_model=ChatResponse)
async def chat_completion(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    """Generate a full, non-streaming history-aware conversational response with citations."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="User message cannot be empty")

    try:
        response = await chat_service.generate_response(
            message=request.message,
            history=request.history,
            strategy=request.strategy,
            k=request.k,
            temperature=request.temperature,
        )
        return response
    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
):
    """Server-Sent Events (SSE) streaming conversational response."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="User message cannot be empty")

    generator = chat_service.stream_response(
        message=request.message,
        history=request.history,
        strategy=request.strategy,
        k=request.k,
        temperature=request.temperature,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
