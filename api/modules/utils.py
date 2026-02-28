import re

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
