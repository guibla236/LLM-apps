# Ticket Management & News Analysis API

This project contains a production-ready API for managing support tickets and analyzing news, featuring a RAG (Retrieval-Augmented Generation) architecture, advanced security, and an administrative dashboard.

## Core Features
- **Ticket Ingestion**: Ingest individual tickets or bulk upload via JSON files with duplicate detection.
- **RAG-powered Search**: Retrieve similar past tickets using Pinecone vector database. (_Note: the old `rag_tickets_retriever` module is deprecated in favor of `rag_unified_retriever`._)
- **AI Augmentation**: Generates summaries and identifies relevant contacts using Llama 3 models via Groq.
- **News Summarization**: Specialized endpoint for processing and summarizing technical news.
- **Hybrid Authentication**: Support for both JWT (for web users) and API Keys (for agents).
- **Admin Dashboard**: A secure web interface to manage feature flags, monitor error logs, track IP usage, and control registration limits.

## Security & Reliability
- **Comprehensive Quotas**: Usage limits per individual user and per IP address (Anti Sybil/Multi-account).
- **Rate Limiting**: Throttling per IP to prevent DoS attacks.
- **Global Error Handling**: Centralized logging of tracebacks to MongoDB with generic client responses and traceability via `error_id`.
- **Asynchronous Execution**: Fully refactored to use `async/await` and `AsyncGroq` for high performance.

For detailed information on quotas and safety measures, see [API_LIMITATIONS.md](API_LIMITATIONS.md).

## Deployment
This API is configured for deployment on **Vercel** as a series of Serverless Functions.
*   **Monorepo Support**: Use the `api/` folder as the **Root Directory** in Vercel settings.
*   **Infrastructure**: Managed via the `api/vercel.json` configuration file.

## Requirements
- Python 3.12+
- MongoDB Atlas account
- Pinecone API Key
- Groq API Key

The list of allowed LLM models is driven by `available_models.json`; edit this file to enable/disable models or change their metadata. The API exposes these values at `GET /api/models`.
## Testing
A small test suite lives under `api/tests`. To verify core functionality run:
```bash
cd api
python -m pytest tests
```
The tests cover model listing and validation logic introduced with the `model_name` parameter, as well as the security headers.

## Setup

1. **Environment Variables**: Create a `.env` file in the `api` directory:
   ```env
   GROQ_API_KEY=...
   PINECONE_API_KEY=...
   PINECONE_INDEX_NAME=...     # vector store for tickets
   PINECONE_KB_INDEX_NAME=...  # vector store for knowledge base docs
   MONGODB_URI=...
   MONGODB_DB_NAME=ticket_system
   JWT_SECRET=your_jwt_secret
   DEFAULT_CHAT_MODEL_NAME=llama-3.1-8b-instant
   # Optional tuning variables:
   # IP_QUOTA_LIMIT=200        # override per-IP daily quota
   # LANGSMITH_*              # used for telemetry/tracing (optional)
   ```

2. **Installation**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Running**:
   ```bash
   uvicorn app:app --reload --port 8000
   ```

## Key API Endpoints

### Public / Authenticated
- `POST /api/register`: New user registration (Limit: 3/day/IP).
- `POST /api/login`: JWT token acquisition.
- `POST /api/summarize_news`: AI news summary.
- **Ticket ingestion**:
  - `POST /api/ingest_json_ticket`: Ingest a single ticket JSON.
  - `POST /api/ingest_json_file`: Bulk ingest tickets from uploaded JSON file.
  - `POST /api/ingest_kb_zip`: (Admin only) Bulk ingest knowledge‑base docs from ZIP.
  - `POST /api/ingest_kb_md`: (Admin only) Ingest a single Markdown KB document.
- `POST /api/get_similar_tickets`: Vector search in previous tickets. Requires `model_name` in payload. **Now requires** a `model_name` field in the JSON body to select which LLM model will power the HyDE augmentation. Check `/api/models` for valid identifiers.
- `POST /api/augment_ticket_information`: Similar to `/get_similar_tickets` but returns an AI-generated summary/contacts for a single ticket. Also requires `model_name`.
- `POST /api/augment_search_results`: Support assistant entry point; accepts a `SearchRequest` object and returns summary + contacts. Includes `model_name` as part of request data.
- `POST /api/raw_unified_search`: Low-level search endpoint used by other services/tools; returns raw `results` array. Accepts `model_name` when `use_hyde` is true.
- `GET /api/models`: List available chat models (id/name). No authentication required but respects API key.
### Administrative (Protected)
- `GET /admin`: Dashboard UI.
- `GET /api/admin/logs`: Audit technical errors.
- `GET /api/admin/ips`: Monitor daily usage per IP address.
- `GET /api/admin/registrations`: View account registrations from today.
- `POST /api/admin/flags/{name}`: Toggle feature flags in real-time.
- `POST /api/admin/users/{username}/quota`: Update user consumption limits.
