import os
from langchain_openai import ChatOpenAI
from pinecone import Pinecone
from dotenv import load_dotenv
from typing import Any, List, Optional
from langchain_ollama import OllamaEmbeddings
from langchain_pinecone import PineconeVectorStore
from openai import OpenAI
from .utils import get_model_details


load_dotenv()

_DEFAULT_CHAT_MODEL_NAME = os.getenv("DEFAULT_CHAT_MODEL_NAME")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

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


class OpenRouterEmbeddings:
    """Minimal embeddings client for OpenRouter-hosted models.

    Implements the LangChain Embeddings interface (`embed_documents` /
    `embed_query`) so it can be used anywhere `embeddings_model` is expected
    (PineconeVectorStore, ingest script).

    Why not `OpenAIEmbeddings`: langchain-openai >= 1.x tokenizes the input
    with tiktoken and sends *token arrays* to the endpoint. VoyageAI models
    (e.g. voyage-4-lite) reject token arrays — they only accept strings or
    string arrays (HTTP 400). The raw OpenAI client sends strings, which
    works with every OpenRouter embedding model.
    """

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def _embed(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._embed([text])[0]

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Async variant — PineconeVectorStore.asimilarity_search uses this."""
        return self._embed(texts)

    async def aembed_query(self, text: str) -> List[float]:
        """Async variant — PineconeVectorStore.asimilarity_search uses this."""
        return self._embed([text])[0]


def get_embeddings_model(model_name: Optional[str] = None) -> Any:
    """Returns the embeddings client for the configured model.

    Resolution order:
    1. Explicit `model_name` argument (highest priority).
    2. `EMBEDDINGS_MODEL` env var — an OpenRouter-hosted model
       (e.g. `voyage-4-lite`), served via the OpenAI-compatible endpoint.
    3. Fallback: local Ollama embeddings with `OLLAMA_EMBEDDINGS_MODEL`
       (default `all-minilm:22m`) — preserves the pre-M4 behavior.
    """
    model = model_name or os.getenv("EMBEDDINGS_MODEL")
    if model:
        return OpenRouterEmbeddings(
            model=model,
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
        )
    ollama_model = os.getenv("OLLAMA_EMBEDDINGS_MODEL", "all-minilm:22m")
    return OllamaEmbeddings(model=ollama_model)


# Default instance — backward compatible (Ollama local unless EMBEDDINGS_MODEL is set)
embeddings_model = get_embeddings_model()

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