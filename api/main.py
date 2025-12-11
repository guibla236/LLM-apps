"""
Punto de entrada para ejecutar la aplicación FastAPI con uvicorn.
Este archivo sirve como script ejecutable para iniciar el servidor.
Para debugging, importa directamente desde app.py
"""

from app import app
from dotenv import load_dotenv
import uvicorn

if __name__ == "__main__":
    load_dotenv()
    uvicorn.run(app, host="0.0.0.0", port=8000)
