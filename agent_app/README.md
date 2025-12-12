# Ticket Resolution Agent (Part 2)

This directory contains the autonomous Ticket Resolution Agent, capable of analyzing tickets, searching for internal and external solutions, and proposing a comprehensive fix.

## Architecture

- **Backend**: FastAPI service (`backend/`) running a LangGraph ReAct agent.
- **Frontend**: Streamlit application (`frontend/`) for a user-friendly interface.
- **Tools**:
    - `get_similar_tickets_tool`: Queries the Part 1 API to find historical context.
    - `search_web_tool`: Searches the web (via Tavily) for documentation and public solutions.

## Requirements

- Python 3.12+
- Dependencies listed in `requirements.txt`

## Setup

1. Navigate to the `agent_app` directory:
   ```bash
   cd agent_app
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python3 -m venv agente_venv
   source agente_venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the `agent_app` directory with the following variables:
   ```env
   GROQ_API_KEY=your_groq_api_key
   TAVILY_API_KEY=your_tavily_api_key
   CHAT_MODEL_NAME=llama-3.1-8b-instant
   ```

## Running the System

**Prerequisite**: Ensure the Part 1 API is running on port 8000 (see `../api/README.md`).

### 1. Start the Agent Backend

Navigate to the `backend` directory and start the server:

```bash
cd backend
python3 main.py
```
This will start the agent service on `http://localhost:8001`.

### 2. Start the Streamlit Frontend

Open a new terminal, activate the environment, and navigate to the `frontend` directory:

```bash
cd frontend
streamlit run app.py
```

The interface will open in your browser (usually at `http://localhost:8501`).

## Usage

1. Open the Streamlit interface.
2. Paste a ticket JSON into the input area.
3. Click "Resolver Ticket".
4. The agent will:
   - Search for similar past tickets in the company database.
   - Search the web for relevant solutions.
   - Synthesize a final resolution in the language of the ticket.
