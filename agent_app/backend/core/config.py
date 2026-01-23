from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
CHAT_MODEL_NAME = os.getenv("CHAT_MODEL_NAME", "llama-3.1-8b-instant")

# Initialize LLM
llm = ChatGroq(
    temperature=0,
    model_name=CHAT_MODEL_NAME,
    api_key=GROQ_API_KEY
)

get_llm = lambda: llm