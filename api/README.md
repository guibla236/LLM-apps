# Ticket Management API (Part 1)

This project contains the core API for managing support tickets, including ingestion, similarity search, and AI-powered data augmentation.

## Features

- **Ticket Ingestion**: Ingest individual tickets or bulk upload via JSON files.
- **RAG-powered Search**: Retrieve similar past tickets using Pinecone vector database.
- **AI Augmentation**: Generates summaries and identifies relevant contacts using LLMs (Groq).
- **Interactive UI**: A simple HTML/JS frontend to interact with the API.

## Requirements

- Python 3.12+
- Dependencies listed in `requirements.txt`

## Setup

1. Navigate to the `api` directory:
   ```bash
   cd api
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the `api` directory with the following variables:
   ```env
   GROQ_API_KEY=your_groq_api_key
   PINECONE_API_KEY=your_pinecone_api_key
   PINECONE_ENVIRONMENT=your_pinecone_env
   PINECONE_INDEX_NAME=your_index_name
   ```

## Running the Application

Start the FastAPI server:

```bash
uvicorn app:app --reload --port 8000
```
Or potentially using the provided `main.py` if preferred:
```bash
python3 main.py
```

The application will be available at `http://localhost:8000`.

## API Endpoints

- `POST /api/ingest_ticket`: Ingest a single ticket.
- `POST /api/ingest_json_file`: Bulk ingest tickets from an uploaded JSON file.
- `POST /api/get_similar_tickets`: Find tickets similar to the input.
- `POST /api/augment_ticket_information`: Enhance ticket data with AI-generated summaries and contacts.
