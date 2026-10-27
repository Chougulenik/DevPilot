# Enterprise RAG Platform: Backend Engine

Welcome to the **Enterprise Retrieval-Augmented Generation (RAG) Platform Backend**. This modular FastAPI application transforms raw corporate knowledge into accurate, grounded conversational answers with interactive inline citations and multi-strategy retrieval analytics.

---

## 1. Architecture & Module Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # Application factory, lifespan, CORS, middleware
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic BaseSettings & env loading
│   │   ├── exceptions.py           # Domain exceptions & global exception handlers
│   │   └── logging.py              # Structured console logging
│   ├── schemas/                    # Pydantic request/response validation schemas
│   │   ├── __init__.py
│   │   ├── document.py             # Ingestion request, chunk schema, doc metadata
│   │   ├── retrieval.py            # Search requests (strategy, k, thresholds), ranked chunks
│   │   ├── chat.py                 # Chat message, conversation thread, stream chunks
│   │   └── health.py               # Health checks and system diagnostic stats
│   ├── services/                   # Business logic (Strategy patterns)
│   │   ├── __init__.py
│   │   ├── chunking/               # Document chunking strategies
│   │   │   ├── base.py             # BaseChunker abstract interface
│   │   │   ├── recursive.py        # RecursiveCharacterTextSplitter
│   │   │   ├── semantic.py         # SemanticChunker (breakpoint percentiles)
│   │   │   └── agentic.py          # LLM-based Agentic Chunker
│   │   ├── retrieval/              # Multi-strategy retrieval engines
│   │   │   ├── base.py             # BaseRetriever abstract interface
│   │   │   ├── vector.py           # Standard similarity & score threshold retriever
│   │   │   ├── multi_query.py      # LLM variation generation & multi-pass retrieval
│   │   │   ├── rrf.py              # Reciprocal Rank Fusion (RRF) ranking
│   │   │   ├── hybrid.py           # Dense vector + BM25 sparse hybrid search
│   │   │   └── reranker.py         # Cross-encoder / contextual reranking pipeline
│   │   ├── vector_store.py         # ChromaDB persistence & lifecycle manager
│   │   ├── ingestion_service.py    # Document loading, pipeline execution & indexing
│   │   └── chat_service.py         # History-aware rewriting, grounded synthesis & citations
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── router.py           # Consolidated API router
│           ├── endpoints/
│           │   ├── health.py       # GET /health, system stats
│           │   ├── documents.py    # POST /upload, GET /documents, POST /reindex
│           │   ├── retrieval.py    # POST /retrieval/query (strategy comparative testing)
│           │   └── chat.py         # POST /chat/completions (SSE streaming & regular)
├── tests/                          # Backend unit & integration tests
├── requirements.txt                # Enterprise backend dependency pins
└── README.md                       # Comprehensive backend documentation
```

---

## 2. Installation & Quickstart

### Prerequisites
- Python 3.10+
- `pip` or modern packaging tools (`pip install -e .` with `pyproject.toml`)

### 1. Configure Environment Variables
Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your-openai-api-key-here
COHERE_API_KEY=your-cohere-api-key-here   # Optional: For Cohere reranker
CHROMA_PERSIST_DIR=db/chroma_db
DOCS_DIR=docs
EMBEDDING_MODEL=text-embedding-3-small
DEFAULT_LLM_MODEL=gpt-4o
FAST_LLM_MODEL=gpt-4o-mini
DEFAULT_TEMPERATURE=0.2
```

### 2. Install Dependencies
Using `uv`:
```bash
uv sync
```
Or using standard `pip`:
```bash
pip install -e .
```

### 3. Run the Backend API Server
```bash
# Option A: Run directly with Uvicorn
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# Option B: Run via module
python -m backend.main
```

Once running:
- **Interactive Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Diagnostic Endpoint**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## 3. API Specification Reference

### 3.1 Health & System Diagnostics

#### `GET /api/v1/health`
Checks backend and vector database availability.
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-10-27T14:30:00Z",
  "database_status": "connected",
  "document_count": 5,
  "chunk_count": 48,
  "environment": "development"
}
```

#### `GET /api/v1/health/stats`
Telemetry statistics rendered in the frontend navigation bar.

---

### 3.2 Knowledge Base Document Management

#### `GET /api/v1/documents`
Lists all indexed documents and previews of their chunks.
```json
{
  "total_documents": 5,
  "total_chunks": 48,
  "documents": [
    {
      "source": "docs/Google.txt",
      "filename": "Google.txt",
      "chunk_count": 12,
      "total_chars": 11840,
      "chunks": [
        {
          "page_content": "Google LLC is an American multinational...",
          "length": 985,
          "metadata": {"source": "docs/Google.txt", "chunk_index": 0}
        }
      ]
    }
  ]
}
```

#### `POST /api/v1/documents/upload`
Uploads a single `.txt`, `.md`, or `.pdf` file via `multipart/form-data`:
- `file`: Binary file
- `strategy`: `recursive` | `semantic` | `agentic`
- `chunk_size`: integer (default: 1000)
- `chunk_overlap`: integer (default: 100)

#### `POST /api/v1/documents/reindex`
Resets the vector database and re-indexes all compatible files inside `docs/`.
```json
{
  "strategy": "recursive",
  "chunk_size": 1000,
  "chunk_overlap": 100
}
```

---

### 3.3 Retrieval Engine Comparison

#### `POST /api/v1/retrieval/query`
Executes search using any of the 5 pluggable strategies:
```json
{
  "query": "How much did Microsoft pay to acquire GitHub?",
  "strategy": "rrf",
  "k": 5,
  "score_threshold": 0.0
}
```
**Response:**
```json
{
  "query": "How much did Microsoft pay to acquire GitHub?",
  "strategy": "rrf",
  "latency_ms": 142,
  "total_results": 5,
  "results": [
    {
      "rank": 1,
      "content": "Microsoft acquired GitHub for 7.5 billion dollars in 2018...",
      "source": "docs/Microsoft.txt",
      "score": 0.0328,
      "metadata": {"source": "docs/Microsoft.txt"}
    }
  ]
}
```

---

### 3.4 Conversational Chat & Streaming Citations

#### `POST /api/v1/chat/completions` (Non-streaming)
```json
{
  "message": "What year was the Roadster first produced?",
  "history": [
    {"role": "user", "content": "Tell me about Tesla."},
    {"role": "assistant", "content": "Tesla is an electric vehicle company [1]."}
  ],
  "strategy": "vector",
  "k": 4,
  "temperature": 0.2
}
```

#### `POST /api/v1/chat/stream` (Server-Sent Events)
Streams tokens directly to client applications:
1. `data: {"type": "citations", "citations": [{"id": 1, "source": "docs/Tesla.txt", "content": "..."}]}`
2. `data: {"type": "token", "content": "Tesla "}`
3. `data: {"type": "token", "content": "began "}`
4. `data: [DONE]`

---

## 4. Chunking Strategies

| Chunker | Mechanism | Best For |
|---|---|---|
| **Recursive** | Splits on `["\n\n", "\n", ". ", " ", ""]` within chunk budget. | General corporate documents, technical specs. |
| **Semantic** | Calculates embedding distance drops between adjacent sentences. | Long narrative prose, reports where section breaks vary. |
| **Agentic** | LLM identifies topic shifts and outputs `<<<SPLIT>>>` boundaries. | Complex documents where semantic context must stay grouped. |

---

## 5. Retrieval Strategies

1. **Vector (Cosine)**: Standard dense vector embeddings search (`text-embedding-3-small`).
2. **Multi-Query**: LLM generates 3 query rephrasings from different angles to pool documents.
3. **Reciprocal Rank Fusion (RRF)**: Merges multiple query result lists using $RRF = \sum \frac{1}{60 + rank}$.
4. **Hybrid (BM25 + Dense)**: Weighted combination (0.7 vector + 0.3 BM25) for keyword + semantic precision.
5. **Cross-Encoder Reranker**: Retrieves top candidates, then reranks them via Cohere or contextual scoring.

---

## 6. Running Tests

```bash
pytest backend/tests -v
```

---

## 7. Production Deployment (Gunicorn + Uvicorn)

For high-throughput production environments:
```bash
gunicorn backend.app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```
