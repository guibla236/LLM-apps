import re
import os
import json
from functools import lru_cache

# load available models once at import time
_models_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "available_models.json")
try:
    with open(_models_path, "r", encoding="utf-8") as _f:
        _AVAILABLE_MODELS = json.load(_f)
except Exception:
    # If the file cannot be read or parsed, fall back to empty list
    _AVAILABLE_MODELS = []

# create index for quick lookup by id
# m.get("id") may return None; only include entries with a string id to
# satisfy the annotated type.
_MODEL_INDEX: dict[str, dict] = {
    id_val: m
    for m in _AVAILABLE_MODELS if isinstance(m, dict) and m.get("id")
    for id_val in (m.get("id"),) if isinstance(id_val, str)
}

def extract_json_from_llm_response(raw_content: str) -> str:
    """
    Cleans the LLM response from markdown and extracts the JSON block.
    Covers the cases:
        1. Pure JSON:            {"summary": ...}
        2. JSON with language:  ```json\n{...}\n```
        3. JSON without language:  ```\n{...}\n```
        4. JSON with text before: "Here is the result:\n{...}"
    """
    # Case 2 and 3: Extract from markdown code block
    match = re.search(r"```[(?:json)?\s*(\{.*?\})\s*]```", raw_content, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Case 4: Search for the first '{' and the last '}' in case there is loose text
    start = raw_content.find('{')
    end = raw_content.rfind('}')
    if start != -1 and end != -1 and end > start:
        return raw_content[start:end + 1].strip()
    
    # Case 1 or fallback: Return as is
    return raw_content.strip()

def list_models():
    """Helper to list available models from the API."""
    # Ensure we always return a consistent JSON shape for the frontend.
    # Normalize environment-provided model names into objects with `id` and `name`.
    clean = [m for m in AVAILABLE_CHAT_MODELS if m]
    models = [{"id": str(m), "name": str(m)} for m in clean]
    return {"models": models}

@lru_cache(maxsize=10)
def load_prompt(prompt_filename: str) -> str:
    """
    Load the required prompt file from the prompts folder.
    """
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", f"{prompt_filename}")
    try:
        with open(prompt_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"System prompt file not found at {prompt_path}")
