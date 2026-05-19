# Enterprise RAG Assistant

A production-ready local Enterprise Knowledge Assistant with multi-provider AI support, automatic document indexing, and a streaming chat interface.

## Features

- Multi-provider AI support (OpenAI, Anthropic, OpenCode Go API)
- Local RAG with FAISS vector database
- Automatic document indexing via filesystem watcher
- Support for PDF, DOCX, TXT, and Markdown files
- Streaming chat responses via Server-Sent Events
- Suggested questions generated from document content
- Admin dashboard for document management
- Docker deployment ready

## Requirements

- Python 3.10+
- API keys for at least one provider

## Quick Start

### 1. Clone and Setup

```bash
cd chatbot
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### 2. Configure

Edit `.env` with your API keys:

```
OPENAI_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
OPENCODE_API_KEY=your-key-here
SECRET_KEY=your-secret-key
```

### 3. Run

```bash
python app.py
```

Open http://localhost:5000

## Project Structure

```
project/
├── app.py                 # Flask application factory
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── Dockerfile             # Production container
├── docker-compose.yml     # Docker orchestration
├── gunicorn.conf.py       # Gunicorn config
├── nginx.conf             # Nginx reverse proxy
│
├── providers/             # AI provider implementations
│   ├── base_provider.py
│   ├── openai_provider.py
│   ├── anthropic_provider.py
│   ├── opencode_provider.py
│   └── provider_manager.py
│
├── parsers/               # Document parsers
│   ├── txt_parser.py
│   ├── md_parser.py
│   ├── pdf_parser.py
│   ├── docx_parser.py
│   └── parser_factory.py
│
├── rag/                   # RAG components
│   ├── chunker.py
│   ├── embeddings.py
│   ├── vector_store.py
│   └── retrieval.py
│
├── sync/                  # Document synchronization
│   ├── processor.py
│   ├── watcher.py
│   └── suggested_questions.py
│
├── routes/                # Flask routes
│   ├── chat.py
│   ├── admin.py
│   └── upload.py
│
├── templates/             # HTML templates
├── static/                # CSS and JS
├── tests/                 # Unit tests
├── company_docs/          # Documents to index
├── vector_db/             # FAISS index + metadata
├── logs/                  # Application logs
└── cache/                 # Cached data
```

## Usage

### Adding Documents

Place files in `company_docs/` or use the upload feature in the admin dashboard. Supported formats: PDF, DOCX, TXT, MD.

### Chat Interface

Navigate to the chat page, select your AI provider, and ask questions about your documents. Responses are streamed in real-time with source citations.

### Admin Dashboard

Navigate to `/admin` to:
- View indexed documents and chunk counts
- Upload new documents
- Reindex individual or all documents
- Delete documents from the vector store
- Check provider health status

## Docker Deployment

```bash
docker-compose up -d
```

## Testing

```bash
python -m pytest tests/
# or
python -m unittest discover tests/
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

## API Documentation

See [API.md](API.md) for endpoint documentation.

## License

MIT
