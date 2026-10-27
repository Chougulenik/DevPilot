import json
import asyncio
from typing import List, AsyncGenerator, Dict, Any, Tuple, Optional
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage

from ..core.config import settings
from ..core.logging import get_logger
from ..core.exceptions import RAGException
from .retrieval import get_retriever
from .vector_store import VectorStoreManager, get_vector_store
from ..schemas.chat import ChatMessage, Citation, ChatResponse
from ..schemas.retrieval import RetrievalResultItem

logger = get_logger("chat_service")


class ChatService:
    """Conversational RAG service with history rewriting, grounded citations, and token streaming."""

    def __init__(self, vector_store: Optional[VectorStoreManager] = None):
        self.vector_store = vector_store or get_vector_store()
        self.default_model = settings.DEFAULT_LLM_MODEL
        self.fast_model = settings.FAST_LLM_MODEL

    def _get_llm(self, model: str, temperature: float = 0.0, streaming: bool = False):
        """Instantiate LLM using Google AI Studio (Gemini) or OpenAI."""
        if settings.GOOGLE_API_KEY:
            from langchain_google_genai import ChatGoogleGenerativeAI
            gemini_model = model
            if "gpt" in gemini_model:
                gemini_model = "gemini-1.5-flash"
            return ChatGoogleGenerativeAI(
                model=gemini_model,
                temperature=temperature,
                google_api_key=settings.GOOGLE_API_KEY,
                streaming=streaming,
            )
        elif settings.OPENAI_API_KEY:
            try:
                from langchain_openai import ChatOpenAI
                return ChatOpenAI(
                    model=model,
                    temperature=temperature,
                    openai_api_key=settings.OPENAI_API_KEY,
                    streaming=streaming,
                )
            except ImportError:
                logger.warning("langchain_openai is not installed.")
        return None

    def _convert_history(self, history: List[ChatMessage]) -> List[BaseMessage]:
        """Convert chat history schemas to LangChain message objects."""
        messages: List[BaseMessage] = []
        for msg in history:
            role = msg.role.lower().strip()
            if role == "user":
                messages.append(HumanMessage(content=msg.content))
            elif role == "assistant":
                messages.append(AIMessage(content=msg.content))
            elif role == "system":
                messages.append(SystemMessage(content=msg.content))
        return messages

    def rewrite_query_with_history(self, user_question: str, history: List[ChatMessage]) -> str:
        """Rewrite multi-turn ambiguous queries into a standalone searchable query."""
        if not history:
            return user_question

        llm = self._get_llm(self.fast_model, temperature=0.0)
        if llm is None:
            return user_question

        try:
            lc_history = self._convert_history(history[-6:])  # Use last 3 turns
            prompt_messages = [
                SystemMessage(
                    content=(
                        "Given the chat history, rewrite the new user question to be a standalone, searchable question "
                        "that includes necessary context. Do not answer the question; just return the rewritten question."
                    )
                ),
                *lc_history,
                HumanMessage(content=f"New question: {user_question}"),
            ]
            response = llm.invoke(prompt_messages)
            rewritten = response.content.strip()
            logger.info(f"Rewrote query '{user_question}' -> '{rewritten}'")
            return rewritten
        except Exception as e:
            logger.warning(f"History query rewriting failed: {e}. Using original question.")
            return user_question

    def retrieve_context(
        self, query: str, strategy: str = "vector", k: int = 4
    ) -> List[RetrievalResultItem]:
        """Retrieve relevant context chunks according to chosen strategy."""
        retriever = get_retriever(strategy=strategy, vector_store=self.vector_store)
        return retriever.retrieve(query=query, k=k)

    def _build_grounded_prompt(
        self, question: str, retrieved_items: List[RetrievalResultItem]
    ) -> Tuple[str, List[Citation]]:
        """Construct prompt with numbered context snippets and build citation objects."""
        citations: List[Citation] = []
        context_blocks: List[str] = []

        for idx, item in enumerate(retrieved_items, start=1):
            citation = Citation(
                id=idx,
                source=item.source,
                content=item.content[:280] + ("..." if len(item.content) > 280 else ""),
                score=item.score,
            )
            citations.append(citation)
            context_blocks.append(f"[{idx}] Source: {item.source}\n{item.content}")

        joined_context = "\n\n".join(context_blocks)
        prompt = (
            f"Based on the following documents, please answer this question: {question}\n\n"
            f"Documents:\n{joined_context}\n\n"
            "Instructions:\n"
            "- Provide a clear, accurate, and comprehensive answer using ONLY the information from the provided documents.\n"
            "- Cite your sources inline using brackets like [1], [2] when stating facts from specific documents.\n"
            "- If you cannot find the answer in the provided documents, strictly state:\n"
            "\"I don't have enough information to answer that question based on the provided documents.\""
        )
        return prompt, citations

    async def generate_response(
        self,
        message: str,
        history: List[ChatMessage] = None,
        strategy: str = "vector",
        k: int = 4,
        temperature: float = 0.2,
    ) -> ChatResponse:
        """Non-streaming complete conversational response."""
        history = history or []
        search_query = self.rewrite_query_with_history(message, history)
        retrieved_items = self.retrieve_context(search_query, strategy=strategy, k=k)
        prompt, citations = self._build_grounded_prompt(message, retrieved_items)

        llm = self._get_llm(self.default_model, temperature=temperature)
        if llm is None:
            answer = (
                "⚠️ GOOGLE_API_KEY is not configured on the server.\n\n"
                f"Retrieved {len(citations)} chunks from knowledge base for query: '{search_query}'.\n"
                "Please configure GOOGLE_API_KEY in your .env file to enable live Gemini LLM generation."
            )
            return ChatResponse(answer=answer, citations=citations, rewritten_query=search_query)

        try:
            lc_history = self._convert_history(history[-4:])
            messages = [
                SystemMessage(
                    content=(
                        "You are a helpful, professional enterprise AI assistant that answers questions based on "
                        "provided documents and conversation history. Always cite your sources with [1], [2], etc."
                    )
                ),
                *lc_history,
                HumanMessage(content=prompt),
            ]
            res = await llm.ainvoke(messages)
            answer = res.content
            return ChatResponse(
                answer=answer,
                citations=citations,
                rewritten_query=search_query,
            )
        except Exception as e:
            logger.error(f"Chat completion generation failed: {e}")
            raise RAGException(f"Error generating chat response: {e}")

    async def stream_response(
        self,
        message: str,
        history: List[ChatMessage] = None,
        strategy: str = "vector",
        k: int = 4,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        """Server-Sent Events (SSE) streaming token generator."""
        history = history or []
        search_query = self.rewrite_query_with_history(message, history)
        retrieved_items = self.retrieve_context(search_query, strategy=strategy, k=k)
        prompt, citations = self._build_grounded_prompt(message, retrieved_items)

        # 1. Immediately emit citation payload so frontend displays source cards
        citations_data = [c.model_dump() for c in citations]
        yield f"data: {json.dumps({'type': 'citations', 'citations': citations_data})}\n\n"

        llm = self._get_llm(self.default_model, temperature=temperature, streaming=True)
        if llm is None:
            mock_text = (
                "⚠️ Note: `GOOGLE_API_KEY` is not set in environment.\n\n"
                f"Successfully retrieved **{len(citations)} sources** from knowledge base for query:\n"
                f"> *\"{search_query}\"*\n\n"
                "Please set your `GOOGLE_API_KEY` in `.env` to enable live Gemini streaming."
            )
            for token in mock_text.split(" "):
                yield f"data: {json.dumps({'type': 'token', 'content': token + ' '})}\n\n"
                await asyncio.sleep(0.04)
            yield "data: [DONE]\n\n"
            return

        try:
            lc_history = self._convert_history(history[-4:])
            messages = [
                SystemMessage(
                    content=(
                        "You are an enterprise AI assistant that answers questions based on "
                        "provided documents and conversation history. Always ground your facts and cite sources "
                        "using inline tags like [1], [2]."
                    )
                ),
                *lc_history,
                HumanMessage(content=prompt),
            ]

            async for chunk in llm.astream(messages):
                token = chunk.content
                if token:
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Streaming token generation error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"


_chat_service_instance: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    global _chat_service_instance
    if _chat_service_instance is None:
        _chat_service_instance = ChatService()
    return _chat_service_instance
