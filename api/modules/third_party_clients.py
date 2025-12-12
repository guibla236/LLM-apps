import os
from groq import Groq
from pinecone import Pinecone
from dotenv import load_dotenv
from typing import Any
from langchain_ollama import OllamaEmbeddings
from langchain_pinecone import PineconeVectorStore


load_dotenv()
groq_llm_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

TOKENIZER_MODEL_NAME = "all-minilm:22m"

embeddings_model = OllamaEmbeddings(model=TOKENIZER_MODEL_NAME)

def get_pinecone_index() -> Any:
    pinecone_index_string = os.getenv("PINECONE_INDEX_NAME")
    if pinecone_index_string is None:
        raise ValueError("PINECONE_INDEX_NAME no está definido en las variables de entorno")
    else:
        test = pinecone_client.Index(pinecone_index_string)
        return pinecone_client.Index(pinecone_index_string)
        
vector_store_instance = PineconeVectorStore(embedding=embeddings_model, index=get_pinecone_index())