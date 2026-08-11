"""
Prompt Engineering Module for CMS AI Assistant.
Manages LangChain system prompts, domain terminology, and context formatting for Ollama integration.
Enforces strict anti-hallucination, read-only database grounding, and professional response guidelines.
"""

from typing import Dict, Any, Optional

CMS_SYSTEM_PROMPT = (
    "You are an AI Assistant for the Clothing Management System (CMS).\n"
    "RULES:\n"
    "1. Base answers STRICTLY on the provided CMS database context. Do NOT fabricate numbers.\n"
    "2. When database context contains specific records (e.g., unit names, posted strength, authorized strength, stock quantities), list the exact numbers and details.\n"
    "3. If no data exists, state 'No matching records were found.'\n"
    "4. Keep answers short and concise. Use double quotes around item/unit names (e.g. \"Unit 1\").\n"
    "5. Do NOT explain internal SQL or technical implementation details."
)


def build_ollama_prompt(
    user_query: str,
    intent: str,
    db_context: Optional[Dict[str, Any]] = None,
    chart_request: Optional[Dict[str, Any]] = None
) -> str:
    """
    Construct concise grounded user prompt payload including database context for Ollama.
    """
    parts = [f"USER QUESTION: {user_query}"]

    if db_context:
        parts.append(f"DATABASE CONTEXT ({intent}): {db_context}")

    parts.append("INSTRUCTION: Provide the exact details and numbers from the database context provided above.")
    return "\n".join(parts)

