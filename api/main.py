"""
Entrypoint for running the FastAPI application with uvicorn.
This file serves as the executable script to start the server.
For debugging, import directly from app.py
"""

from app import app
from dotenv import load_dotenv
import uvicorn

if __name__ == "__main__":
    load_dotenv()
    uvicorn.run(app, host="0.0.0.0", port=8000)
