# Ticket Resolution Agent (Part 2)

This directory contains the production-ready Ticket Resolution Agent, capable of analyzing tickets, searching for internal and external solutions, and proposing comprehensive fixes. It is now fully integrated with the Part 1 API for security and auditing.

## Architecture

- **Backend**: Modular FastAPI service (`backend/`) with a fully **asynchronous** LangGraph ReAct agent.
    - `core/`: Config, database connection, security, and logging.
    - `services/`: Business logic, agent execution, and session management.
    - `routers/`: FastAPI routes for chat, sessions, and history.
    - `schema/`: Pydantic models for data validation.
- **Frontend**: Streamlit application (`frontend/`) with built-in **JWT Authentication**.
- **Auditing**: Every execution is logged to the `agent_executions` and `error_logs` collections in MongoDB.
- **Memory & Persistence**: Stateful conversation history stored in MongoDB (`checkpoints`), maintaining context across sessions.
- **Session Management**: Multi-session support with auto-generated titles, deletion capabilities, and cookie-based login persistence.
- **Tools**:
    - `get_similar_tickets_tool`: Queries the Part 1 API to find historical context (respects Feature Flags).
  *New:* this tool now sends a `model_name` field with every request; the default value is derived from the `CHAT_MODEL_NAME` environment variable, but callers (and tests) may override it if necessary. Valid identifiers can be fetched from the `/api/models` endpoint on the RAG API.

## Requirements

- Python 3.12+
- Dependencies: `pip install -r requirements.txt` (includes `motor`, `httpx`, and `langgraph`).

## Setup

1. **Environment Variables**: Create a `.env` file in the `agent_app` directory:
   ```env
   GROQ_API_KEY=your_groq_api_key
   TAVILY_API_KEY=your_tavily_api_key
   CHAT_MODEL_NAME=llama-3.1-8b-instant  # default LLM used by the agent; also sent as 'model_name' to API requests if not overridden
   API_BASE_URL=http://localhost:8000
   PORT=8001  # backend listens on this port (default 8001)
   APP_API_KEY=your_api_key  # key that frontend/tools use to call Part 1 API
   MONGODB_URI=your_mongodb_uri
   MONGODB_DB_NAME=ticket_system
   ```

2. **Installation**:
   ```bash
   pip install -r requirements.txt
   ```

## Running the System

**Prerequisite**: The Part 1 API must be running on port 8000.

You can use the root script to start everything:
```bash
./run_all.sh
```

Or start manually:
1. **Backend**: `cd backend && python3 main.py` (Port 8001)
2. **Frontend**: `cd frontend && streamlit run app.py` (Port 8501)

## Backend API Endpoints
The agent backend exposes the following authenticated routes (JWT required):

* `POST /chat/` – send a message to the agent, returns `response` and tool `trace`.
* `GET /sessions/` – list your active session IDs.
* `GET /history/{session_id}` – retrieve messages for a session.
* `DELETE /history/{session_id}` – delete a session.
* `POST /solve_ticket` – **deprecated** legacy endpoint; returns solution for a ticket. Please use `/chat/solve_ticket` or call `/chat/` directly.

These same endpoints are used by the Streamlit frontend in `frontend/app.py`.

## Testing Backend
Automated tests for the backend live in `backend/tests`. Execute them with:
```bash
cd agent_app/backend
python -m pytest tests
```
The set includes agent capability tests and search tool validations (model_name, HyDE routing, etc.).
## Security & Usage

1. **Login**: Access `http://localhost:8501` and log in with your API credentials.
2. **Identity**: The agent identifies you via your JWT token and discounts consultations from your daily quota.
3. **Monitoring**: Administrators can view your agent usage and any errors in the **Admin Dashboard** (`http://localhost:8000/admin`).
4. **Tool Control**: Tools like web search can be enabled/disabled in real-time by administrators via Feature Flags.
