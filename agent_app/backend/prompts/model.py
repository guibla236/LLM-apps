from enum import Enum

class PromptFileNames(str, Enum):
    SYSTEM_PROMPT = "system_prompt"
    SUMMARY_PROMPT = "summary_prompt"
