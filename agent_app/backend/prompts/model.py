from enum import Enum

class PromptFileNames(str, Enum):
    SYSTEM_PROMPT = "system_prompt"
    SUMMARY_PROMPT = "summary_prompt"
    ANALYZE_PROMPT = "analyze_prompt"
    EVALUATE_PROMPT = "evaluate_prompt"
    REFINE_PROMPT = "refine_prompt"
    GENERATE_PROMPT = "generate_prompt"
