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
    """
    Gets the Pinecone index for tickets.
    """
    pinecone_index_string = os.getenv("PINECONE_INDEX_NAME")
    if pinecone_index_string is None:
        raise ValueError("PINECONE_INDEX_NAME is not defined in the env vars.")
    else:
        return pinecone_client.Index(pinecone_index_string)
        
# --- Configuración separada para el índice Knowledge Base (KB) ---
KB_INDEX_ENV_VAR = "PINECONE_KB_INDEX_NAME"

def get_kb_pinecone_index() -> Any:
    """Gets the Pinecone index for Knowledge Base.

    The `PINECONE_KB_INDEX_NAME` environment variable is required. If not
    defined, an exception is raised to avoid unexpected behavior.
    """
    pinecone_index_string = os.getenv(KB_INDEX_ENV_VAR)
    if pinecone_index_string is None:
        raise ValueError(f"{KB_INDEX_ENV_VAR} is not defined in the env vars.")
    return pinecone_client.Index(pinecone_index_string)

# Default instance for tickets
vector_store_instance = PineconeVectorStore(embedding=embeddings_model, index=get_pinecone_index())

# Instance for Knowledge Base (KB)
kb_vector_store_instance = PineconeVectorStore(embedding=embeddings_model, index=get_kb_pinecone_index())