"""Shared helpers for the multi-step diagnosis agent nodes."""
import json
import re
from typing import Any, Dict, List, Tuple


def extract_json(text: str) -> Dict[str, Any]:
    """Best-effort extraction of a JSON object from an LLM response.

    Tries: (1) the first {...} block found (with or without markdown fences),
    (2) a raw json.loads of the trimmed text.
    """
    if not text:
        return {}
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {}


def extract_ticket_ids(context: str) -> set:
    """Extract all ticket IDs present in accumulated context strings.

    Ticket blocks are formatted as `[n] ID: <ticketId>` by the search tool.
    """
    if not context:
        return set()
    return set(re.findall(r"ID:\s*(\S+)", context))


def parse_search_blocks(result_str: str) -> List[Tuple[str, str]]:
    """Split a search tool result into (ticket_id, block_text) pairs.

    The tool formats results as:
        [1] ID: SE-XXX\nContent: ...\n\n --- \n[2] ID: SE-YYY\n...
    """
    blocks: List[Tuple[str, str]] = []
    for part in result_str.split(" --- "):
        part = part.strip()
        if not part:
            continue
        m = re.search(r"ID:\s*(\S+)", part)
        if m:
            blocks.append((m.group(1), part))
    return blocks


def last_human_message(messages) -> str:
    """Return the content of the most recent human message."""
    for m in reversed(messages):
        if getattr(m, "type", "") == "human" and getattr(m, "content", None):
            return str(m.content)
    return ""
