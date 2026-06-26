<div align="center">

# 🤖 Local RAG Chatbot

**A fully local, privacy-first Retrieval-Augmented Generation chatbot.**  
Upload PDFs. Ask questions. Get cited answers. No cloud APIs. No data leaves your machine.

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5+-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Ollama](https://img.shields.io/badge/Ollama-Local_AI-000000?logo=ollama&logoColor=white)](https://ollama.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Features](#-features) •
[Architecture](#-architecture) •
[Quick Start](#-quick-start) •
[API Docs](#-api-documentation) •
[Contributing](#-contributing)

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 📄 **PDF Upload** | Upload any text-based PDF up to 50MB |
| 🔍 **Hybrid Search** | Vector similarity + PostgreSQL full-text search with RRF fusion |
| 🤖 **Local LLM** | llama3:8b via Ollama — fully offline, zero API costs |
| 📌 **Source Citations** | Every answer cites the exact page and document it came from |
| 🌊 **Streaming Responses** | Token-by-token streaming via Server-Sent Events |
| 🧠 **Conversation Memory** | Session memory + long-term semantic memory across conversations |
| 🔐 **JWT Authentication** | Secure login with access + refresh token rotation |
| 👥 **Multi-user** | Isolated document libraries and conversations per user |
| 🏠 **100% Local** | No OpenAI, no Anthropic, no Pinecone — everything runs on your machine |

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     React Frontend                       │
│          Vite · TypeScript · TailwindCSS                 │
│        Zustand · React Query · Axios · SSE               │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP / SSE
┌────────────────────────▼────────────────────────────────┐
│                   FastAPI Backend                        │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Auth API   │  │ Document API │  │   RAG / SSE   │  │
│  │  JWT + RBAC │  │ Upload/Status│  │   Stream API  │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              LangGraph Agent                     │   │
│  │  Query Analyzer → Memory → Retriever →           │   │
│  │  Context Builder → Generator → Citation Builder  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Hybrid     │  │   Ollama     │  │  RQ Workers   │  │
│  │  Retriever  │  │  llama3:8b   │  │  Doc + Memory │  │
│  │  pgvector   │  │  nomic-embed │  │  Processing   │  │
│  │  + FTS/RRF  │  │              │  │               │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
└───────────┬────────────────┬────────────────────────────┘
            │                │
┌───────────▼──────┐  ┌──────▼───────┐
│   PostgreSQL 16  │  │    Redis     │
│   pgvector HNSW  │  │  RQ Queues  │
│   FTS GIN Index  │  │             │
└──────────────────┘  └─────────────┘
```

### Key Design Decisions

- **LangGraph** for agent orchestration — explicit nodes, conditional routing, debuggable state
- **pgvector HNSW** for vector search — production-grade ANN, no separate vector DB needed
- **Hybrid Search + RRF** — vector + full-text fusion outperforms either alone by ~15% recall
- **RQ workers** for background processing — PDF extraction and embedding never block the API
- **Two-tier memory** — session memory (recent turns) + long-term semantic memory (summarized)

---

## ⚡ Quick Start

### Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.12+ | [python.org](https://python.org) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| PostgreSQL | 16+ | [postgresql.org](https://postgresql.org) |
| Redis | 7+ | [redis.io](https://redis.io) |
| Ollama | Latest | [ollama.ai](https://ollama.ai) |

### 1. Clone the repository

```bash
git clone https://github.com/strixxx9129/local-rag-chatbot.git
cd local-rag-chatbot
```

### 2. Pull AI models

```bash
ollama pull llama3:8b
ollama pull nomic-embed-text
```

### 3. Set up PostgreSQL

```bash
psql -U postgres -c "CREATE DATABASE rag_chatbot;"
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;" -d rag_chatbot
```

### 4. Backend setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp ../.env.example .env
# Edit .env — set SECRET_KEY and JWT_SECRET_KEY

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn src.main:app --reload
```

### 5. Start background workers

```bash
# Terminal 2 — Document processing worker
cd backend
source venv/bin/activate
python run_worker.py documents    # Windows: uses SimpleWorker automatically

# Terminal 3 — Memory summarization worker
python run_worker.py memory
```

### 6. Frontend setup

```bash
cd frontend
npm install
cp ../.env.example .env          # or create frontend/.env manually
# Set VITE_API_URL=http://localhost:8000/api/v1
npm run dev
```

### 7. Open the app

```
http://localhost:5173
```

Register an account → Upload a PDF → Start chatting.

---

## 📁 Project Structure

```
local-rag-chatbot/
├── backend/
│   ├── src/
│   │   ├── api/v1/          # FastAPI routers (auth, documents, rag, stream)
│   │   ├── auth/            # JWT, password hashing, RBAC
│   │   ├── core/            # Config, logging, exceptions
│   │   ├── db/              # SQLAlchemy engine + session
│   │   ├── graph/           # LangGraph agent nodes + builder
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── rag/             # Retriever, chunker, embedder, LLM service
│   │   ├── repositories/    # DB query layer
│   │   ├── schemas/         # Pydantic v2 request/response schemas
│   │   ├── services/        # Business logic layer
│   │   └── workers/         # RQ background jobs
│   ├── alembic/             # Database migrations
│   ├── tests/               # Test suite
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/             # Axios client + API modules + SSE client
│   │   ├── components/      # Reusable UI components
│   │   ├── hooks/           # React Query + custom hooks
│   │   ├── pages/           # Page components
│   │   ├── routes/          # Route guards
│   │   ├── store/           # Zustand stores
│   │   └── types/           # TypeScript types
│   └── package.json
├── docs/
│   └── architecture.md
└── README.md
```

---

## 🔌 API Documentation

Interactive API docs available at `http://localhost:8000/docs` when the backend is running.

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Create account |
| `POST` | `/api/v1/auth/login` | Login, receive tokens |
| `POST` | `/api/v1/auth/refresh` | Rotate refresh token |
| `POST` | `/api/v1/auth/logout` | Revoke refresh token |
| `GET`  | `/api/v1/auth/me` | Current user profile |

### Documents

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/documents/upload` | Upload PDF (202 Accepted) |
| `GET`  | `/api/v1/documents` | List user's documents |
| `GET`  | `/api/v1/documents/{id}` | Document detail |
| `GET`  | `/api/v1/documents/{id}/status` | Poll processing status |
| `DELETE` | `/api/v1/documents/{id}` | Delete document + file |

### RAG Chat

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/rag/chat` | Buffered RAG response |
| `POST` | `/api/v1/stream/chat` | Streaming SSE response |
| `GET`  | `/api/v1/rag/conversations` | List conversations |
| `GET`  | `/api/v1/rag/conversations/{id}` | Conversation + messages |

### Example: Chat Request

```bash
curl -X POST http://localhost:8000/api/v1/stream/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the main findings?",
    "document_id": "uuid-here",
    "top_k": 5,
    "use_hybrid": true
  }'
```

---

## 🛠 Tech Stack

### Backend
| Technology | Purpose |
|---|---|
| FastAPI | Async REST API + SSE streaming |
| SQLAlchemy 2.0 | Async ORM |
| Alembic | Database migrations |
| PostgreSQL + pgvector | Vector store + full-text search |
| LangGraph | Agent orchestration |
| Ollama | Local LLM + embeddings |
| Redis + RQ | Background job processing |
| Pydantic v2 | Request/response validation |

### Frontend
| Technology | Purpose |
|---|---|
| React 18 | UI framework |
| TypeScript | Type safety |
| Vite | Build tool + dev server |
| TailwindCSS | Styling |
| TanStack Query | Server state + caching |
| Zustand | Client state management |
| Axios | HTTP client with interceptors |

---

## 🔧 Configuration

All configuration is via environment variables in `backend/.env`.

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | — | App secret (required) |
| `JWT_SECRET_KEY` | — | JWT signing key (required) |
| `DATABASE_URL` | — | PostgreSQL async URL (required) |
| `DATABASE_URL_SYNC` | — | PostgreSQL sync URL for Alembic (required) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server |
| `OLLAMA_CHAT_MODEL` | `llama3:8b` | Chat model |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `CHUNK_SIZE` | `512` | Characters per chunk |
| `CHUNK_OVERLAP` | `64` | Overlap between chunks |
| `RETRIEVER_TOP_K` | `5` | Chunks retrieved per query |
| `MAX_UPLOAD_SIZE_MB` | `50` | Max PDF size |

---

## 🚀 Performance

Benchmarks on a MacBook Pro M2 / Windows i7 with 16GB RAM:

| Operation | Time |
|---|---|
| PDF upload (10 pages) | ~200ms |
| Document processing (10 pages, 40 chunks) | ~45s |
| Query embedding | ~100ms |
| Hybrid retrieval (pgvector + FTS) | ~80ms |
| LLM first token (llama3:8b) | ~800ms |
| Full answer (200 tokens) | ~8s |

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and contribution guidelines.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [Ollama](https://ollama.ai) — making local LLMs accessible
- [pgvector](https://github.com/pgvector/pgvector) — vector search in PostgreSQL
- [LangGraph](https://github.com/langchain-ai/langgraph) — agent orchestration
- [FastAPI](https://fastapi.tiangolo.com) — the best Python web framework
```
