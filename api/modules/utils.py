import re
import os
import json
from functools import lru_cache
from typing import Any
from fastapi import HTTPException

# load available models once at import time
_models_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "available_models.json")
try:
    with open(_models_path, "r", encoding="utf-8") as _f:
        _AVAILABLE_MODELS = json.load(_f)
except Exception:
    # If the file cannot be read or parsed, fall back to empty list
    _AVAILABLE_MODELS = []

_MODEL_INDEX: dict[str, Any] = {
    m["id"]: m 
    for m in _AVAILABLE_MODELS 
    if isinstance(m, dict) and isinstance(m.get("id"), str)
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
    """Return the minimal model list for the frontend.

    This helper no longer reads the JSON file on every call; it uses the
    preloaded ``_AVAILABLE_MODELS`` list. Only entries with ``enabled``
    truthy are included, and the output shape matches the previous
    implementation (`{"models": [{"id": ..., "name": ...}, ...]}`).
    """
    result = []
    for entry in _AVAILABLE_MODELS:
        if entry.get("enabled"):
            result.append({"id": entry.get("id"), "name": entry.get("name")})
    return {"models": result}


def get_model_details(model_id: str) -> dict[str, str | bool] | None:
    """Lookup the full record for a given model id.

    Returns the original dictionary from ``available_models.json`` if the
    identifier is found, otherwise ``None``.
    """
    return _MODEL_INDEX.get(model_id)

def validate_model_name(model_name: str) -> str:
    """Ensure the provided model name exists and is enabled.

    This helper is intended for use in FastAPI endpoints.  It raises an
    ``HTTPException`` with status 400 if the model is unknown or disabled, so
    that clients immediately receive a clear error message about the new
    contract requirement.  The function returns the original name on success,
    which allows it to be convenient as a dependency or inline check.

    Args:
        model_name: Identifier of the LLM model requested by the caller.
    Returns:
        The same ``model_name`` string if validation passes.
    """
    details = get_model_details(model_name)
    if details is None or not details.get("enabled", False):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Model '{model_name}' is not available or is currently disabled. "
                "Use /api/models to see valid options."
            ),
        )
    return model_name


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
