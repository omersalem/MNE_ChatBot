# Architecture

## Overview

The Enterprise RAG Assistant is a modular Flask application that implements Retrieval-Augmented Generation (RAG) without external RAG frameworks. All components are custom-built for full control and transparency.

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend                            │
│  ┌───────────┐  ┌─────────────────┐  ┌───────────────┐ │
│  │   Chat UI │  │ Admin Dashboard │  │ SSE Streaming │ │
│  └─────┬─────┘  └────────┬────────┘  └───────┬───────┘ │
└────────┼─────────────────┼───────────────────┼─────────┘
         │                 │                   │
┌────────▼─────────────────▼───────────────────▼─────────┐
│                     Flask Routes                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │
│  │ /api/chat│  │ /admin/* │  │ /api/upload          │ │
│  └────┬─────┘  └────┬─────┘  └──────────┬───────────┘ │
└───────┼─────────────┼───────────────────┼─────────────┘
        │             │                   │
┌───────▼─────────────▼───────────────────▼─────────────┐
│                   Core Services                        │
│                                                       │
│  ┌─────────────────┐    ┌──────────────────────────┐  │
│  │ Provider Manager│    │   Document Processor     │  │
│  │ ┌─────┬─────┬──┐│    │ ┌──────┬──────┬───────┐  │  │
│  │ │OpenAI│Anth │OC ││    │ │Parse │Chunk │Embed │  │  │
│  │ └─────┴─────┴──┘│    │ └──────┴──────┴───────┘  │  │
│  └─────────────────┘    └──────────────────────────┘  │
│                                                       │
│  ┌─────────────────┐    ┌──────────────────────────┐  │
│  │ Retrieval Engine│    │   Vector Store (FAISS)   │  │
│  │ ┌──────┬──────┐ │    │ ┌──────────────────────┐ │  │
│  │ │Search│Context│ │    │ │ Index + Metadata DB  │ │  │
│  │ └──────┴──────┘ │    │ └──────────────────────┘ │  │
│  └─────────────────┘    └──────────────────────────┘  │
└───────────────────────────────────────────────────────┘
```

## Data Flows

### Retrieval Flow (Chat)

```
User Question
    │
    ▼
┌─────────────┐
│ Chat Route  │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Query      │────▶│  Vector      │────▶│  Top-K      │
│  Embedding  │     │  Search      │     │  Chunks     │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                                                ▼
                                       ┌─────────────┐
                                       │  Context    │
                                       │  Builder    │
                                       └──────┬──────┘
                                              │
                                              ▼
                                     ┌────────────────┐
                                     │  System Prompt │
                                     │  + Context     │
                                     └───────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │  AI Provider    │
                                    │  (Streaming)    │
                                    └─────────────────┘
```

### Indexing Flow

```
File in company_docs/
    │
    ▼
┌─────────────┐
│  Watchdog   │ (detects create/modify/delete)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Parser     │ (TXT, MD, PDF, DOCX)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Chunker    │ (configurable size + overlap)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Embedding  │ (Sentence Transformers)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  FAISS      │ (IndexFlatIP + JSON metadata)
└─────────────┘
```

### Provider Flow

```
┌─────────────────────┐
│  Provider Manager   │ (Singleton)
│  - Select provider  │
│  - Switch providers │
│  - Health checks    │
└──────────┬──────────┘
           │
    ┌──────┼──────┐
    ▼      ▼      ▼
┌──────┐┌──────┐┌──────┐
│OpenAI││Anthro││OpenCo│
│      ││pic   ││de    │
└──────┘└──────┘└──────┘
```

## Key Components

### Provider System
- Base provider defines interface (generate, stream, health, validate)
- Each provider implements the interface using native SDKs
- ProviderManager is a singleton for state management

### Vector Store
- FAISS IndexFlatIP (cosine similarity via normalized vectors)
- JSON metadata file for chunk attributes
- Singleton pattern with lazy loading
- Supports add, search, remove-by-source operations

### Document Processor
- Pipeline: parse -> remove old -> chunk -> embed -> store
- Handles full document lifecycle
- Used by both manual upload and automatic watcher

### Watchdog Monitor
- Monitors `company_docs/` directory
- Debounced processing (2s delay) to handle rapid changes
- Handles created, modified, and deleted events

### Retrieval Engine
- Converts query to embedding
- Searches FAISS for top-K similar chunks
- Builds context with token limits
- Deduplicates and formats sources

## Security

- CSRF protection via Flask-WTF
- Rate limiting via Flask-Limiter
- File type validation (whitelist)
- Upload size limit (50MB)
- No hardcoded secrets (all via .env)

## Performance

- Singleton pattern for heavy resources (embeddings, vector store)
- FAISS index loaded once at startup
- Debounced file watching
- Rotating log files (10MB max, 5 backups)
