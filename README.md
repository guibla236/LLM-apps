# GenAI-Powered Technical Support System

This repository houses an integrated solution for the automated management and resolution of technical support tickets. The project combines a robust API for data management with an autonomous intelligent agent capable of proposing solutions.

## Project Structure

The system is divided into two main components:

### 1. Ticket Management API (`api/`)
The core of the system. Provides the base functionalities for the support team:
*   **RAG Knowledge Base**: Ingestion and vectorization of historical tickets.
*   **Semantic Search**: Finds similar problems that occurred in the past.
*   **Enrichment Assistant**: Uses LLMs to summarize incidents and suggest internal experts.

👉 **[View API documentation and installation](api/README.md)**

### 2. Autonomous Resolution Agent (`agent_app/`)
An intelligent agent designed to act on tickets. Built with LangGraph, FastAPI (with modular architecture) and Streamlit:
*   **Research**: Queries the main API to obtain historical context.
*   **Web Search**: Uses search tools (Tavily) to find public documentation and external solutions.
*   **Synthesis**: Generates a step-by-step solution proposal ready for the user.

👉 **[View Agent documentation and installation](agent_app/README.md)**

## Production Deployment (Hybrid Architecture)

The system is designed for optimized cloud deployment (zero cost) using three specialized platforms:

| Component | Platform | Role |
| :--- | :--- | :--- |
| **API Backend** | **Vercel** | Data management, RAG search, and Admin Panel. |
| **Agent Backend** | **Render** | Asynchronous agent processing (Docker). |
| **Agent Frontend** | **Streamlit Cloud** | Interactive and secure user interface. |

### Monorepo Configuration
Although each service resides on a different platform, deployment is performed directly from this repository using **Root Directory** functionality.

---

## Recommended Workflow

1. **Start the API (Part 1)**: The API must be running on port 8000 to provide historical context.
2. **Start the Agent (Part 2)**: Launch the agent backend and its graphical interface to begin resolving tickets.

For specific technical details, dependencies, and environment variable configuration, please consult the respective `README.md` of each module.
