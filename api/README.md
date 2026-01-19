# Ticket Management & News Analysis API

This project contains a production-ready API for managing support tickets and analyzing news, featuring a RAG (Retrieval-Augmented Generation) architecture, advanced security, and an administrative dashboard.

## Core Features
- **Ticket Ingestion**: Ingest individual tickets or bulk upload via JSON files with duplicate detection.
- **RAG-powered Search**: Retrieve similar past tickets using Pinecone vector database.
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

## Setup

1. **Environment Variables**: Create a `.env` file in the `api` directory:
   ```env
   GROQ_API_KEY=...
   PINECONE_API_KEY=...
   PINECONE_INDEX_NAME=...
   MONGODB_URI=...
   MONGODB_DB_NAME=ticket_system
   JWT_SECRET=your_jwt_secret
   CHAT_MODEL_NAME=llama-3.1-8b-instant
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
- `POST /api/get_similar_tickets`: Vector search in previous tickets.

### Administrative (Protected)
- `GET /admin`: Dashboard UI.
- `GET /api/admin/logs`: Audit technical errors.
- `GET /api/admin/ips`: Monitor daily usage per IP address.
- `GET /api/admin/registrations`: View account registrations from today.
- `POST /api/admin/flags/{name}`: Toggle feature flags in real-time.
- `POST /api/admin/users/{username}/quota`: Update user consumption limits.
