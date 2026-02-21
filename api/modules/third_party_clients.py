import os
from groq import AsyncGroq
from pinecone import Pinecone
from dotenv import load_dotenv
from typing import Any
from langchain_ollama import OllamaEmbeddings
from langchain_pinecone import PineconeVectorStore


load_dotenv()
groq_llm_client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

TOKENIZER_MODEL_NAME = "all-minilm:22m"

embeddings_model = OllamaEmbeddings(model=TOKENIZER_MODEL_NAME)

def get_pinecone_index() -> Any:
    pinecone_index_string = os.getenv("PINECONE_INDEX_NAME")
    if pinecone_index_string is None:
        raise ValueError("PINECONE_INDEX_NAME no está definido en las variables de entorno")
    else:
        return pinecone_client.Index(pinecone_index_string)
        
# --- Configuración separada para el índice Knowledge Base (KB) ---
KB_INDEX_ENV_VAR = "PINECONE_KB_INDEX_NAME"

def get_kb_pinecone_index() -> Any:
    """Obtiene el índice de Pinecone para los Knowledge Base.

    La variable de entorno `PINECONE_KB_INDEX_NAME` es obligatoria. Si no está
    definida se lanza una excepción para evitar comportamientos inesperados.
    """
    pinecone_index_string = os.getenv(KB_INDEX_ENV_VAR)
    if pinecone_index_string is None:
        raise ValueError(f"{KB_INDEX_ENV_VAR} no está definido en las variables de entorno")
    return pinecone_client.Index(pinecone_index_string)

# Instancia por defecto (actual) para tickets
vector_store_instance = PineconeVectorStore(embedding=embeddings_model, index=get_pinecone_index())

# Nueva instancia separada para los Knowledge Base (KB)
kb_vector_store_instance = PineconeVectorStore(embedding=embeddings_model, index=get_kb_pinecone_index())