
def get_system_prompt() -> str:
    """Helper to read markdown file with the system prompt."""
    # TODO: If any other prompts for the future, change this function to be able to retrieve any prompt from the prompts directory.
    try:
        with open("prompts/system_prompt.md", "r") as f:
            return f.read()
    except Exception:
        pass
    return None