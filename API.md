# API Documentation

## Base URL

```
http://localhost:5000
```

## Endpoints

### Health Check

```
GET /health
```

**Response:**
```json
{ "status": "ok" }
```

---

### Chat

```
POST /api/chat
```

**Headers:**
- `Content-Type: application/json`
- `X-CSRFToken: <csrf-token>`

**Request Body:**
```json
{
  "message": "What is the company policy on remote work?",
  "provider": "openai"
}
```

**Response:** Server-Sent Events stream

```
data: {"content": "Based"}
data: {"content": " on the"}
data: {"content": " documents,"}
data: {"content": " ..."}
data: {"sources": [{"filename": "policy.pdf", "chunk_id": "...", "score": 0.85}]}
data: [DONE]
```

**Error Response:**
```json
{ "error": "Message is required" }
```

---

### Suggested Questions

```
GET /api/suggested-questions
```

**Response:**
```json
{
  "questions": [
    "What is in the policy document?",
    "Summarize the policy document",
    "Tell me about remote work in the documents"
  ]
}
```

### Refresh Suggested Questions

```
POST /api/suggested-questions/refresh
```

**Headers:**
- `X-CSRFToken: <csrf-token>`

**Response:**
```json
{
  "questions": ["...", "..."]
}
```

---

### Upload Document

```
POST /api/upload
```

**Headers:**
- `X-CSRFToken: <csrf-token>`

**Request:** Multipart form with `file` field

**Supported Types:** PDF, DOCX, TXT, MD
**Max Size:** 50MB

**Response:**
```json
{
  "filename": "policy.pdf",
  "chunks": 15,
  "status": "indexed"
}
```

**Error Response:**
```json
{ "error": "File type not allowed. Allowed: {'pdf', 'docx', 'txt', 'md'}" }
```

---

### Admin Dashboard

```
GET /admin/
```

Renders the admin dashboard HTML page.

---

### List Documents

```
GET /admin/api/documents
```

**Response:**
```json
{
  "documents": [
    {
      "filename": "policy.pdf",
      "document_type": "pdf",
      "chunk_count": 15
    }
  ]
}
```

---

### Reindex Document

```
POST /admin/api/documents/<filename>/reindex
```

**Headers:**
- `X-CSRFToken: <csrf-token>`

**Response:**
```json
{
  "filename": "policy.pdf",
  "chunks": 15,
  "status": "indexed"
}
```

---

### Delete Document

```
DELETE /admin/api/documents/<filename>
```

**Headers:**
- `X-CSRFToken: <csrf-token>`

**Response:**
```json
{
  "filename": "policy.pdf",
  "removed_chunks": 15
}
```

---

### Reindex All

```
POST /admin/api/reindex-all
```

**Headers:**
- `X-CSRFToken: <csrf-token>`

**Response:**
```json
{
  "results": [
    { "filename": "policy.pdf", "chunks": 15, "status": "indexed" }
  ]
}
```

---

### Provider Health

```
GET /admin/api/health
```

**Response:**
```json
{
  "providers": {
    "openai": { "status": "connected", "provider": "openai" },
    "anthropic": { "status": "failed", "provider": "anthropic", "error": "..." },
    "opencode": { "status": "connected", "provider": "opencode", "base_url": "..." }
  }
}
```

---

### Vector Store Stats

```
GET /admin/api/stats
```

**Response:**
```json
{
  "total_chunks": 150,
  "total_vectors": 150,
  "unique_documents": 10
}
```
