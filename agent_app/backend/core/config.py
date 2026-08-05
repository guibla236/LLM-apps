from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
AGENT_MODEL = os.getenv("AGENT_MODEL", "deepseek/deepseek-v4-flash")

_llm = None

def get_llm():
    """ Initialize and return the LLM instance (OpenRouter via ChatOpenAI). """
    global _llm

    if _llm is None:
        if OPENROUTER_API_KEY is None:
            raise ValueError("OPENROUTER_API_KEY environment variable is not set.")
        _llm = ChatOpenAI(
            temperature=0,
            model=AGENT_MODEL,
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
        )

    return _llm

get_env_var = lambda var_name: os.getenv(var_name)