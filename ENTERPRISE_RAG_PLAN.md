# Enterprise Production RAG System: Architecture Blueprint & Implementation Roadmap

## 1. System Vision & Architecture

This roadmap details the transformation of standalone exploratory scripts (`1_ingestion_pipeline.py` through `13_reranker.ipynb`) into a unified, modular, enterprise-grade Retrieval-Augmented Generation (RAG) platform with a decoupled FastAPI backend and a modern React 18 frontend.

### High-Level Architecture Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                   React 18+ Enterprise Frontend                        │
│  ┌───────────────────────┐  ┌──────────────────────┐  ┌─────────────┐  │
│  │ Document Management   │  │ Conversational Chat  │  │ Retrieval   │  │
│  │ & Ingestion Inspector │  │ & Citation Viewer    │  │ Playground  │  │
│  └───────────┬───────────┘  └──────────┬───────────┘  └──────┬──────┘  │
│              └─────────────────────────┼─────────────────────┘         │
│                                        ▼                               │
│                         Typed API Client Layer (Axios)                 │
└────────────────────────────────────────┬───────────────────────────────┘
                                         │ HTTP REST / SSE Streaming
┌────────────────────────────────────────▼───────────────────────────────┐
│                        FastAPI Backend Engine                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ API Routing & Middleware (CORS, Request Logging, Error Handling) │  │
│  └─────────────────────────────────┬────────────────────────────────┘  │
│                                    ▼                                   │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Service Layer (Dependency Injection & Strategy Patterns)         │  │
│  │ ├─ IngestionService (Recursive, Semantic, Agentic Chunkers)       │  │
│  │ ├─ RetrievalService (Vector, Multi-Query, RRF, Hybrid, Rerank)   │  │
│  │ └─ ChatService (Query Rewriter, Grounded Generation, Citations)   │  │
│  └───────────────────┬──────────────────────────────┬───────────────┘  │
│                      ▼                              ▼                  │
│       ┌──────────────────────────────┐  ┌───────────────────────────┐  │
│       │ Storage & Vector Store       │  │ External LLM / Embeddings │  │
│       │ - ChromaDB (Persistent)      │  │ - OpenAI Embeddings       │  │
│       │ - BM25 Index / In-memory     │  │ - GPT-4o / GPT-4o-mini    │  │
│       │ - Metadata Store             │  │ - Cross-Encoder / Rerank  │  │
│       └──────────────────────────────┘  └───────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Target Directory & Module Structure

### 2.1 Backend (`/backend`)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # Application factory, lifespan, CORS, middleware
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Pydantic BaseSettings (env vars, model configs)
│   │   ├── exceptions.py           # Custom domain exceptions & global exception handlers
│   │   └── logging.py              # Structured logging configuration
│   ├── schemas/                    # Pydantic request/response validation schemas
│   │   ├── __init__.py
│   │   ├── document.py             # Ingestion request, chunk schema, doc metadata
│   │   ├── retrieval.py            # Search requests (strategy, k, thresholds), ranked chunks
│   │   ├── chat.py                 # Chat message, conversation thread, stream chunks
│   │   └── health.py               # Health checks and system diagnostic stats
│   ├── services/                   # Core business logic (Strategy patterns)
│   │   ├── __init__.py
│   │   ├── chunking/               # Extracted from scripts 1, 5, 6, 7
│   │   │   ├── base.py             # BaseChunker abstract class
│   │   │   ├── recursive.py        # RecursiveCharacterTextSplitter
│   │   │   ├── semantic.py         # SemanticChunker (breakpoint percentiles)
│   │   │   └── agentic.py          # LLM-based Agentic Chunker
│   │   ├── retrieval/              # Extracted from scripts 2, 9, 10, 11, 12, 13
│   │   │   ├── base.py             # BaseRetriever abstract interface
│   │   │   ├── vector.py           # Standard similarity & score threshold retriever
│   │   │   ├── multi_query.py      # LLM variation generation & multi-pass retrieval
│   │   │   ├── rrf.py              # Reciprocal Rank Fusion ranking
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

### 2.2 Frontend (`/frontend`)

```
frontend/
├── public/                         # Static assets, favicon, logo
├── src/
│   ├── assets/                     # Icons, brand SVG assets
│   ├── components/
│   │   ├── common/                 # Reusable atomic UI (Button, Input, Modal, Badge, Spinner)
│   │   ├── layout/                 # AppShell, Navbar, Sidebar, PageHeader
│   │   ├── chat/                   # Production Chat Window
│   │   │   ├── ChatContainer.jsx   # Message list, sticky input, streaming status
│   │   │   ├── MessageBubble.jsx   # Markdown renderer, code highlighting, timestamp
│   │   │   ├── CitationBadge.jsx   # Interactive source badges (1, 2, 3...)
│   │   │   ├── CitationModal.jsx   # Source chunk drawer with similarity score
│   │   │   └── StrategySelector.jsx# Select retrieval method & LLM temperature
│   │   ├── documents/              # Knowledge Base Management
│   │   │   ├── DocumentTable.jsx   # Active documents, chunk counts, source paths
│   │   │   ├── DocumentUploadModal.jsx # Drag-and-drop file upload with chunking options
│   │   │   └── ChunkViewerModal.jsx# Inspect generated chunks & embeddings metadata
│   │   └── playground/             # Retrieval Comparison Playground
│   │       ├── StrategyComparison.jsx # Run query against 2+ retrieval modes side-by-side
│   │       └── RankedResultCard.jsx   # Score, rank, source snippet viewer
│   ├── context/                    # React Context stores
│   │   ├── ChatContext.jsx         # Conversation threads, message streaming, active session
│   │   ├── DocumentContext.jsx     # Document collection, indexing state
│   │   └── ThemeContext.jsx        # Dark/light theme state
│   ├── services/                   # Typed API bindings & network handling
│   │   ├── apiClient.js            # Axios client with base URL, headers, error interceptors
│   │   ├── documentApi.js          # Ingestion & document endpoints
│   │   ├── retrievalApi.js         # Retrieval query endpoints
│   │   └── chatApi.js              # Chat streaming (fetch with ReadableStream / SSE)
│   ├── styles/                     # Design system CSS / variables
│   │   ├── index.css               # Global reset, typography, tokens, scrollbar styling
│   │   └── theme.css               # Design tokens (dark mode, glassmorphism, accent colors)
│   ├── App.jsx                     # Route / Tab switcher (Chat, Documents, Playground)
│   └── main.jsx                    # React 18 DOM mount
├── package.json                    # Frontend dependencies & scripts
├── vite.config.js                  # Vite bundler configuration & backend proxy
└── README.md                       # Frontend architecture & setup guide
```

---

## 3. Implementation Stories & Module Breakdown

The delivery roadmap is organized into 9 verifiable, sequential user stories:

```
[Story 1: Backend Foundation] ──► [Story 2: Ingestion & Chunking] ──► [Story 3: Retrieval Engine]
                                                                                │
[Story 5: Frontend Design System] ◄── [Story 4: History-Aware Chat Engine] ◄─────┘
         │
         ├──► [Story 6: Document Management UI]
         ├──► [Story 7: Conversational Chat UI & Citations]
         └──► [Story 8: Retrieval Comparison Playground]
                     │
                     └──► [Story 9: Docs (3 READMEs), Integration & Hardening]
```

---

### Story 1: Enterprise Backend Foundation & Configuration Layer
* **Goal:** Establish a modular FastAPI architecture with strict configuration management, structured logging, centralized error handling, and health diagnostics.
* **Modules Implemented:**
  - `backend/app/core/config.py`: Dynamic settings with `pydantic-settings`, parsing `.env` parameters (OpenAI API key, Chroma persist directory, embedding model, default LLM, temperature).
  - `backend/app/core/logging.py`: Structured console logging for traceability.
  - `backend/app/core/exceptions.py`: Custom domain exceptions (`DocumentNotFoundException`, `IndexingException`, `RetrievalException`) and global FastAPI exception handlers.
  - `backend/app/schemas/health.py`: Pydantic response models for `/health` and diagnostic telemetry.
  - `backend/app/api/v1/endpoints/health.py`: Health endpoint validating database availability, document collection size, and active configuration.
  - `backend/app/main.py`: Application factory incorporating CORS middleware, startup/shutdown lifecycles, and API routing.

---

### Story 2: Advanced Document Ingestion & Pluggable Chunking Engine
* **Goal:** Unify scripts 1, 5, 6, 7 into an ingestion service supporting multiple chunking algorithms, metadata extraction, and vector store synchronization.
* **Modules Implemented:**
  - `backend/app/services/vector_store.py`: ChromaDB manager singleton providing thread-safe collection access with cosine distance metrics.
  - `backend/app/services/chunking/base.py`: `BaseChunker` abstract interface.
  - `backend/app/services/chunking/recursive.py`: Standard recursive character splitter with configurable chunk size and overlap.
  - `backend/app/services/chunking/semantic.py`: Semantic chunker segmenting text based on embedding cosine similarity drop percentiles.
  - `backend/app/services/chunking/agentic.py`: LLM-guided agentic chunker for natural context boundary detection.
  - `backend/app/services/ingestion_service.py`: Orchestration pipeline: file loading (`.txt`, `.md`, `.pdf`), chunking strategy dispatch, embedding generation (`text-embedding-3-small`), and batch persistence.
  - `backend/app/schemas/document.py`: Pydantic models for document metadata, chunk preview, ingestion request, and indexing job summary.
  - `backend/app/api/v1/endpoints/documents.py`:
    - `GET /api/v1/documents`: List indexed documents and metadata.
    - `POST /api/v1/documents/upload`: Multi-part file upload with chunking strategy selection.
    - `POST /api/v1/documents/reindex`: Automated batch reindexing of the local `docs/` folder.

---

### Story 3: Multi-Strategy Retrieval Engine (Similarity, Multi-Query, RRF, Hybrid & Reranking)
* **Goal:** Consolidate retrieval techniques from scripts 2, 9, 10, 11, 12, 13 into a pluggable retrieval service with a strategy pattern.
* **Modules Implemented:**
  - `backend/app/services/retrieval/base.py`: Abstract `BaseRetriever` class.
  - `backend/app/services/retrieval/vector.py`: Standard cosine similarity retrieval with optional score threshold filtering.
  - `backend/app/services/retrieval/multi_query.py`: LLM-based query variation generator producing 3-5 alternative query angles.
  - `backend/app/services/retrieval/rrf.py`: Reciprocal Rank Fusion ($RRF = \sum \frac{1}{k + rank}$) to merge results from multiple query variations.
  - `backend/app/services/retrieval/hybrid.py`: Hybrid search combining sparse BM25 keyword matching and dense vector similarity.
  - `backend/app/services/retrieval/reranker.py`: Cross-encoder / LLM reranking pipeline to re-score candidate chunks for maximal semantic precision.
  - `backend/app/schemas/retrieval.py`: Pydantic models (`RetrievalRequest`, `RetrievalResultItem`, `RetrievalStrategyEnum`).
  - `backend/app/api/v1/endpoints/retrieval.py`: `POST /api/v1/retrieval/query` endpoint supporting dynamic strategy switching with detailed ranking metrics.

---

### Story 4: History-Aware Conversational Engine with Streaming & Citations
* **Goal:** Integrate scripts 3 and 4 into a conversational RAG service with conversational memory, query contextualization (standalone query rewriting), strict grounded synthesis, exact document citations, and real-time token streaming.
* **Modules Implemented:**
  - `backend/app/schemas/chat.py`: `ChatMessage`, `ChatRequest`, `Citation`, `ChatStreamChunk`.
  - `backend/app/services/chat_service.py`:
    - Standalone query rewriter converting multi-turn ambiguous queries into clear search terms using conversation history.
    - Grounded prompt synthesizer that maps facts directly to chunk citations (`[1]`, `[2]`).
    - Hallucination guardrails: returns clear boundaries when the context is insufficient.
    - Async token generator for Server-Sent Events (SSE).
  - `backend/app/api/v1/endpoints/chat.py`:
    - `POST /api/v1/chat/completions`: Standard non-streaming endpoint.
    - `POST /api/v1/chat/stream`: Server-Sent Events (SSE) streaming endpoint delivering real-time tokens and structured citation payloads.

---

### Story 5: Enterprise React Frontend Architecture & Design System Setup
* **Goal:** Construct a robust frontend foundation utilizing Vite, React 18, a modern glassmorphic design system, and structured API clients.
* **Modules Implemented:**
  - `frontend/package.json`: Production dependencies (`lucide-react`, markdown parsers, syntax highlighter, axios).
  - `frontend/vite.config.js`: Bundler configuration with development proxy forwarding `/api` to `http://localhost:8000`.
  - `frontend/src/styles/theme.css` & `index.css`: Design tokens, dark mode palette, typography hierarchy, custom scrollbars, and card elevations.
  - `frontend/src/components/common/`: Reusable atomic UI elements (`Button`, `Input`, `Select`, `Badge`, `Card`, `Modal`, `Spinner`).
  - `frontend/src/components/layout/`: `AppShell`, `Navbar` with server health badge, and multi-view tab navigation (`Chat`, `Knowledge Base`, `Retrieval Playground`).
  - `frontend/src/services/apiClient.js`: Centralized Axios client with interceptors, timeouts, and structured error propagation.

---

### Story 6: Document Management & Ingestion Control Dashboard (Frontend)
* **Goal:** Deliver an intuitive management interface for the document knowledge base.
* **Modules Implemented:**
  - `frontend/src/services/documentApi.js`: API bindings for document listing, uploading, and re-indexing.
  - `frontend/src/context/DocumentContext.jsx`: React context for tracking document state, upload progress, and indexing tasks.
  - `frontend/src/components/documents/DocumentTable.jsx`: Filterable data table displaying document sources, chunk counts, character lengths, and indexing timestamps.
  - `frontend/src/components/documents/DocumentUploadModal.jsx`: Modal supporting drag-and-drop file upload with chunking algorithm selection (`Recursive`, `Semantic`, `Agentic`).
  - `frontend/src/components/documents/ChunkViewerModal.jsx`: Drawer modal displaying individual document chunks, embedding details, and source metadata.

---

### Story 7: Production-Grade Conversational Chat Interface & Citation Inspector (Frontend)
* **Goal:** Deliver a conversational interface featuring streaming tokens, Markdown code highlighting, and interactive source citations.
* **Modules Implemented:**
  - `frontend/src/services/chatApi.js`: Fetch-based `ReadableStream` parser for handling Server-Sent Events (SSE).
  - `frontend/src/context/ChatContext.jsx`: State manager for message history, active streaming state, and citation registries.
  - `frontend/src/components/chat/ChatContainer.jsx`: Auto-scrolling chat history viewport with sticky input composer and keyboard shortcuts (`Enter` / `Shift+Enter`).
  - `frontend/src/components/chat/MessageBubble.jsx`: Message renderer supporting Markdown, code syntax highlighting, timestamp indicators, and clickable citation pills (`[1]`, `[2]`).
  - `frontend/src/components/chat/CitationModal.jsx`: Interactive slide-over drawer detailing the referenced document, chunk index, text snippet, and relevance score.
  - `frontend/src/components/chat/StrategySelector.jsx`: Collapsible settings bar allowing real-time switching of retrieval strategies and model parameters.

---

### Story 8: Advanced Retrieval Playground & Strategy Comparison Hub (Frontend)
* **Goal:** Provide an engineering playground to compare and evaluate retrieval strategies side-by-side.
* **Modules Implemented:**
  - `frontend/src/services/retrievalApi.js`: API client for the `/api/v1/retrieval/query` endpoint.
  - `frontend/src/components/playground/StrategyComparison.jsx`: Side-by-side split screen view comparing results of two or more strategies (e.g. Cosine Similarity vs. RRF vs. Hybrid).
  - `frontend/src/components/playground/RankedResultCard.jsx`: Visual representation of retrieved chunks detailing score, rank position, source file, and content preview.

---

### Story 9: End-to-End Integration, Comprehensive Documentation & Deployment Hardening
* **Goal:** Validate end-to-end flows, optimize performance, and create three thorough README documentation files.
* **Deliverables:**
  - **Root `README.md`**: Overall system architecture, prerequisite guide, quickstart command reference, component interactions, and feature catalog.
  - **Backend `backend/README.md`**: Module layout, environment variable reference, API specifications (endpoints, request/response examples), chunking/retrieval architecture documentation, testing guidelines, and production deployment recommendations (Gunicorn + Uvicorn, Docker).
  - **Frontend `frontend/README.md`**: Frontend component hierarchy, state flow, design system guide, API proxy details, and production build/deployment procedures.
  - Integration validation: Automated checks for ingestion, retrieval queries, streaming conversation with citations, and edge-case handling.
