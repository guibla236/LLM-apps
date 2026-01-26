from langchain_groq import ChatGroq
from dotenv import load_dotenv
from pydantic import SecretStr
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
CHAT_MODEL_NAME = os.getenv("CHAT_MODEL_NAME", "llama-3.1-8b-instant")

_llm = None

def get_llm():
    """ Initialize and return the LLM instance. """
    global _llm

    if _llm is None:
        if GROQ_API_KEY is None:
            raise ValueError("GROQ_API_KEY environment variable is not set.")
        if CHAT_MODEL_NAME is None:
            raise ValueError("CHAT_MODEL_NAME environment variable is not set.")
        _llm = ChatGroq(
            temperature=0,
            model=CHAT_MODEL_NAME,
            api_key=SecretStr(GROQ_API_KEY)
        )

    return _llm

get_env_var = lambda var_name: os.getenv(var_name)