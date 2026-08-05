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
    "2. If no data exists, state 'No matching records were found.'\n"
    "3. Keep answers short (2-3 concise bullet points). Use double quotes around item/unit names (e.g. \"Jacket\").\n"
    "4. Do NOT explain internal SQL or technical implementation details."
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

    parts.append("INSTRUCTION: Answer concisely in 2-3 bullet points based on the database context.")
    return "\n".join(parts)

