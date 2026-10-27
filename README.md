# Enterprise Production RAG System

An enterprise-grade Retrieval-Augmented Generation (RAG) platform with a decoupled **FastAPI** backend and modern **React 18** frontend.

---

## 🌟 Key Features

1. **Conversational Chat & Grounded Citations**:
   - Multi-turn conversation with automatic history-aware query rewriting.
   - Grounded prompt synthesis ensuring claims link directly to source chunks with interactive citation badges (`[1]`, `[2]`).
   - Real-time token streaming via Server-Sent Events (SSE).
   - Hallucination guardrails: fallback responses when documents lack relevant information.

2. **Knowledge Base Management & Ingestion**:
   - Ingest documents (`.txt`, `.md`, `.pdf`) into persistent ChromaDB vector storage.
   - Pluggable chunking strategies: **Recursive Character**, **Semantic (Percentile Breakpoint)**, and **Agentic (LLM-Guided)**.
   - Chunk inspection modal: view exact chunks and character statistics.

3. **Retrieval Comparison Playground**:
   - Compare two or more retrieval algorithms side-by-side with latency metrics and scores:
     - **Vector (Cosine Similarity)**
     - **Multi-Query Expansion**
     - **Reciprocal Rank Fusion (RRF)**
     - **Hybrid (Dense Vector + Sparse BM25)**
     - **Cross-Encoder Reranker**

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                   React 18+ Frontend (Vite)                      │
│   • Conversational Chat   • Knowledge Base   • Playground        │
└────────────────────────────────┬─────────────────────────────────┘
                                 │ HTTP REST / SSE (/api/v1)
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend Engine                         │
│   • API Routing & CORS Middleware                                │
│   • Services: Ingestion, Multi-Strategy Retrieval, Chat          │
│   • Storage: Persistent ChromaDB & Embeddings                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart Guide

### 1. Environment Configuration
Create a `.env` file in the root directory:
```env
OPENAI_API_KEY=your-openai-api-key
COHERE_API_KEY=your-cohere-api-key   # Optional: For Cohere reranking
CHROMA_PERSIST_DIR=db/chroma_db
DOCS_DIR=docs
EMBEDDING_MODEL=text-embedding-3-small
DEFAULT_LLM_MODEL=gpt-4o
FAST_LLM_MODEL=gpt-4o-mini
DEFAULT_TEMPERATURE=0.2
```

### 2. Backend Setup & Startup
Install dependencies with `uv`:
```bash
uv sync
```
Or with `pip`:
```bash
pip install -e .
```

Start the FastAPI backend:
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
The backend will run on `http://localhost:8000`. You can explore the interactive API documentation at `http://localhost:8000/docs`.

### 3. Frontend Setup & Startup
In a separate terminal, install Node dependencies and start the Vite dev server:
```bash
cd frontend
npm install
npm run dev
```
The frontend will start at `http://localhost:5173`. Vite automatically proxies `/api` requests to `http://127.0.0.1:8000`.

---

## 📂 Project Organization

- [`backend/`](file:///c:/Users/garg0/Downloads/Projects/nikita/rag-for-beginners/backend): FastAPI production application, services, and tests.
- [`frontend/`](file:///c:/Users/garg0/Downloads/Projects/nikita/rag-for-beginners/frontend): React 18 frontend dashboard.
- [`docs/`](file:///c:/Users/garg0/Downloads/Projects/nikita/rag-for-beginners/docs): Document corpus (Google, Microsoft, Nvidia, SpaceX, Tesla, Attention paper).
- [`pyproject.toml`](file:///c:/Users/garg0/Downloads/Projects/nikita/rag-for-beginners/pyproject.toml): Modern Python project packaging.
- [`ENTERPRISE_RAG_PLAN.md`](file:///c:/Users/garg0/Downloads/Projects/nikita/rag-for-beginners/ENTERPRISE_RAG_PLAN.md): Blueprint and design specification.
