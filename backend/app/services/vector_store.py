import os
import re
import time
import uuid
import threading
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from langchain_chroma import Chroma
from langchain_core.documents import Document

from ..core.config import settings
from ..core.logging import get_logger
from ..core.exceptions import VectorStoreException

logger = get_logger("vector_store")


def _extract_retry_delay(err: Exception) -> Optional[float]:
    """Parse retry delay duration specified in Google API error messages."""
    err_str = str(err)
    m = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    m = re.search(r"retryDelay['\"]?:\s*['\"]?(\d+)s", err_str, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _sanitize_metadata(meta: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Ensure metadata contains only primitive types supported by ChromaDB."""
    if not meta:
        return {}
    clean: Dict[str, Any] = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)):
            clean[k] = v
        elif v is None:
            clean[k] = ""
        else:
            clean[k] = str(v)
    return clean


class VectorStoreManager:
    """Thread-safe ChromaDB vector store lifecycle manager."""

    _instance: Optional["VectorStoreManager"] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self):
        self.persist_directory = settings.CHROMA_PERSIST_DIR
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        self.embedding_model_name = settings.EMBEDDING_MODEL
        self._embeddings: Optional[Any] = None
        self._genai_client: Optional[Any] = None
        self._db: Optional[Chroma] = None
        self._init_db()

    @classmethod
    def get_instance(cls) -> "VectorStoreManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _get_genai_client(self):
        """Lazily initialize Google GenAI SDK client for high-throughput batching."""
        if self._genai_client is None and settings.GOOGLE_API_KEY:
            try:
                from google import genai
                self._genai_client = genai.Client(api_key=settings.GOOGLE_API_KEY)
                logger.info("Initialized google-genai Client for batch embedding")
            except Exception as e:
                logger.warning(f"Could not initialize google.genai Client: {e}")
        return self._genai_client

    def _get_embedding_function(self):
        """Lazily initialize GoogleGenerativeAIEmbeddings or OpenAIEmbeddings."""
        if self._embeddings is None:
            if settings.GOOGLE_API_KEY:
                try:
                    from langchain_google_genai import GoogleGenerativeAIEmbeddings
                    model_name = self.embedding_model_name
                    if "text-embedding" in model_name or model_name in ("models/embedding-001", "embedding-001"):
                        model_name = "models/gemini-embedding-001"
                    elif not model_name.startswith("models/"):
                        model_name = f"models/{model_name}"
                    logger.info(f"Initializing GoogleGenerativeAIEmbeddings with model: {model_name}")
                    self._embeddings = GoogleGenerativeAIEmbeddings(
                        model=model_name,
                        google_api_key=settings.GOOGLE_API_KEY,
                    )
                except Exception as e:
                    logger.error(f"Failed to load GoogleGenerativeAIEmbeddings: {e}")
            elif settings.OPENAI_API_KEY:
                try:
                    from langchain_openai import OpenAIEmbeddings
                    self._embeddings = OpenAIEmbeddings(
                        model=self.embedding_model_name,
                        openai_api_key=settings.OPENAI_API_KEY,
                    )
                except Exception as e:
                    logger.error(f"Failed to load OpenAIEmbeddings: {e}")

            if self._embeddings is None:
                logger.warning("No valid API key found. Initializing fallback Google embeddings.")
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                self._embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/gemini-embedding-001",
                    google_api_key=settings.GOOGLE_API_KEY or "dummy-key",
                )
        return self._embeddings

    def _init_db(self) -> None:
        """Initialize ChromaDB handle."""
        try:
            embeddings = self._get_embedding_function()
            self._db = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=embeddings,
                collection_metadata={"hnsw:space": "cosine"},
            )
            count = self.get_count()
            logger.info(f"ChromaDB initialized at {self.persist_directory} with {count} chunks")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise VectorStoreException(f"ChromaDB initialization error: {e}")

    @property
    def db(self) -> Chroma:
        if self._db is None:
            self._init_db()
        return self._db

    def get_count(self) -> int:
        """Return total chunks in the vector store."""
        try:
            return self._db._collection.count()
        except Exception:
            return 0

    def add_documents(
        self, documents: List[Document], batch_size: int = 20, pause_seconds: float = 1.5
    ) -> List[str]:
        """Add documents to ChromaDB in batches respecting API velocity (100 RPM) & token limits (30,000 TPM).

        1. Groups chunks into small batches (e.g., 20 chunks) to stay within TPM quotas.
        2. Sends each batch in a single embed_content API request (consumes only 1 request).
        3. Dynamically extracts API retryDelay on 429 quota exhaustion and pauses as instructed.
        4. Pauses between batches (pause_seconds) to ensure safe velocity and token pacing.
        """
        if not documents:
            return []

        total_chunks = len(documents)
        logger.info(
            f"Embedding and indexing {total_chunks} chunks in batches of {batch_size} "
            f"(pause={pause_seconds}s between batches)"
        )

        batches = [documents[i : i + batch_size] for i in range(0, total_chunks, batch_size)]
        total_batches = len(batches)

        genai_client = self._get_genai_client()
        embedding_fn = self._get_embedding_function()

        # Clean model name for google-genai
        raw_model = self.embedding_model_name or "gemini-embedding-001"
        if "text-embedding" in raw_model or raw_model in ("models/embedding-001", "embedding-001"):
            embed_model = "gemini-embedding-001"
        else:
            embed_model = raw_model.replace("models/", "")

        all_ids: List[str] = []

        for batch_idx, batch in enumerate(batches):
            batch_texts = [doc.page_content for doc in batch]
            batch_metadatas = [_sanitize_metadata(doc.metadata) for doc in batch]
            batch_ids = [str(uuid.uuid4()) for _ in batch]

            embeddings: Optional[List[List[float]]] = None

            # 1. Use google.genai batch embed_content
            if genai_client:
                max_retries = 8
                base_backoff = 3.0
                for attempt in range(max_retries):
                    try:
                        result = genai_client.models.embed_content(
                            model=embed_model,
                            contents=batch_texts,
                        )
                        embeddings = [list(emb.values) for emb in result.embeddings]
                        break
                    except Exception as e:
                        err_msg = str(e).lower()
                        is_rate_limit = any(
                            kw in err_msg
                            for kw in ("429", "quota", "resource_exhausted", "velocity", "rate")
                        )
                        retry_delay = _extract_retry_delay(e)
                        if is_rate_limit and attempt < max_retries - 1:
                            wait = (retry_delay + 2.0) if retry_delay is not None else min(60.0, base_backoff * (2**attempt))
                            logger.warning(
                                f"Rate/quota limit hit on batch {batch_idx + 1}/{total_batches} "
                                f"(attempt {attempt + 1}/{max_retries}). Pausing for {wait:.1f}s as instructed by API..."
                            )
                            time.sleep(wait)
                        elif attempt < max_retries - 1:
                            wait = base_backoff
                            logger.warning(
                                f"Batch {batch_idx + 1}/{total_batches} error (attempt {attempt + 1}/{max_retries}). "
                                f"Retrying in {wait:.1f}s: {e}"
                            )
                            time.sleep(wait)
                        else:
                            logger.error(
                                f"Batch {batch_idx + 1}/{total_batches} failed after {max_retries} attempts: {e}"
                            )
                            raise VectorStoreException(f"Batch embedding failed: {e}")

            # 2. Fallback to LangChain embedding_fn if genai_client was not available
            if embeddings is None and embedding_fn is not None:
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        embeddings = embedding_fn.embed_documents(batch_texts)
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            time.sleep(3.0 * (attempt + 1))
                        else:
                            raise VectorStoreException(f"Fallback embedding failed: {e}")

            # 3. Upsert batch into ChromaDB collection with precomputed vectors
            try:
                self.db._collection.upsert(
                    ids=batch_ids,
                    embeddings=embeddings,
                    metadatas=batch_metadatas,
                    documents=batch_texts,
                )
                all_ids.extend(batch_ids)
                logger.info(
                    f"Successfully embedded & indexed batch {batch_idx + 1}/{total_batches} "
                    f"({len(batch_texts)} chunks, {len(all_ids)}/{total_chunks} total indexed)"
                )
            except Exception as e:
                logger.error(f"Failed to upsert batch {batch_idx + 1} into ChromaDB: {e}")
                raise VectorStoreException(f"Failed to persist batch {batch_idx + 1}: {e}")

            # 4. Sleep briefly between batch requests to safely respect the 100 RPM velocity limit
            if batch_idx + 1 < total_batches and pause_seconds > 0:
                time.sleep(pause_seconds)

        logger.info(f"Successfully embedded and indexed all {len(all_ids)} chunks into ChromaDB.")
        return all_ids

    def similarity_search_with_score(
        self, query: str, k: int = 4, score_threshold: float = 0.0
    ) -> List[Tuple[Document, float]]:
        """Perform cosine similarity search and normalize distances to similarity scores."""
        try:
            # Chroma with cosine distance returns distance d in [0, 2]
            # Cosine similarity = 1 - distance
            results = self.db.similarity_search_with_score(query, k=k)
            filtered_results = []
            for doc, distance in results:
                # Convert cosine distance to similarity score
                similarity = max(0.0, min(1.0, 1.0 - distance))
                if similarity >= score_threshold:
                    filtered_results.append((doc, similarity))
            return filtered_results
        except Exception as e:
            logger.error(f"Similarity search failed for query '{query}': {e}")
            raise VectorStoreException(f"Search failed: {e}")

    def get_all_documents_metadata(self) -> List[Dict[str, Any]]:
        """Retrieve all documents grouped by source with chunk previews."""
        try:
            collection = self.db._collection
            raw = collection.get(include=["metadatas", "documents"])
            docs_map: Dict[str, Dict[str, Any]] = {}

            metadatas = raw.get("metadatas") or []
            documents = raw.get("documents") or []

            for meta, content in zip(metadatas, documents):
                meta_dict = meta if isinstance(meta, dict) else {}
                source = meta_dict.get("source", "Unknown") if meta_dict else "Unknown"
                filename = Path(source).name if source and source != "Unknown" else "Uploaded Document"
                safe_content = content or ""

                if source not in docs_map:
                    docs_map[source] = {
                        "source": source,
                        "filename": filename,
                        "chunk_count": 0,
                        "total_chars": 0,
                        "chunks": [],
                    }

                chunk_entry = {
                    "page_content": safe_content,
                    "length": len(safe_content),
                    "metadata": meta_dict,
                }
                docs_map[source]["chunks"].append(chunk_entry)
                docs_map[source]["chunk_count"] += 1
                docs_map[source]["total_chars"] += len(safe_content)

            return list(docs_map.values())
        except Exception as e:
            logger.error(f"Failed to retrieve catalog from ChromaDB: {e}")
            return []

    def reset_collection(self) -> None:
        """Reset or clear all entries in the Chroma collection."""
        try:
            try:
                self.db.delete_collection()
            except Exception:
                pass
            self._init_db()
            logger.info("ChromaDB collection reset successfully")
        except Exception as e:
            logger.error(f"Failed to reset ChromaDB collection: {e}")
            raise VectorStoreException(f"Failed to reset vector database: {e}")


def get_vector_store() -> VectorStoreManager:
    """Dependency injection helper."""
    return VectorStoreManager.get_instance()
