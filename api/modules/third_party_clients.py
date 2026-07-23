import os
from langchain_openai import ChatOpenAI
from pinecone import Pinecone
from dotenv import load_dotenv
from typing import Any
from langchain_ollama import OllamaEmbeddings
from langchain_pinecone import PineconeVectorStore
from .utils import get_model_details


load_dotenv()

_DEFAULT_CHAT_MODEL_NAME = os.getenv("DEFAULT_CHAT_MODEL_NAME")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

if not _DEFAULT_CHAT_MODEL_NAME:
    raise ValueError("DEFAULT_CHAT_MODEL_NAME must be defined in the environment variables.")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY must be defined in the environment variables.")
else:
    default_chat_client = ChatOpenAI(
        model=_DEFAULT_CHAT_MODEL_NAME,
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
    )


def get_chat_client(model_name: str) -> ChatOpenAI:
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY must be defined in the environment variables.")
    model_details = get_model_details(model_name)
    if model_details is None:
        raise ValueError(f"The specified model '{model_name}' is not available or it is disabled. Please check the model configuration.")
    if not model_details.get("enabled", False):
        raise ValueError(f"The specified model '{model_name}' is currently disabled. Please try with another model.")
    return ChatOpenAI(
        model=model_name,
        api_key=OPENROUTER_API_KEY,
        base_url=OPENROUTER_BASE_URL,
    )

pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

TOKENIZER_MODEL_NAME = "all-minilm:22m"

embeddings_model = OllamaEmbeddings(model=TOKENIZER_MODEL_NAME)

# Namespace where the SE corpus vectors live. The PineconeVectorStore default
# is the '' namespace (legacy synthetic tickets) — the SE ingestion writes to
# 'kb-se-all', so the retriever must query that namespace explicitly.
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE")

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
vector_store_instance = PineconeVectorStore(
    embedding=embeddings_model,
    index=get_pinecone_index(),
    namespace=PINECONE_NAMESPACE,
)

# Instance for Knowledge Base (KB)
kb_vector_store_instance = PineconeVectorStore(embedding=embeddings_model, index=get_kb_pinecone_index())

def get_default_chat_model_name():
    """Returns the default chat model name from environment variables."""
    if not _DEFAULT_CHAT_MODEL_NAME:
        raise ValueError("DEFAULT_CHAT_MODEL_NAME must be defined in the environment variables.")
    return _DEFAULT_CHAT_MODEL_NAME