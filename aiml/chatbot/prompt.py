"""
Prompt Engineering Module for CMS AI Business Assistant.
Manages system prompts and context formatting for Ollama summarization.
"""

from typing import Dict, Any, Optional

CMS_BUSINESS_SYSTEM_PROMPT = """You are an AI Business Assistant for the Clothing Management System (CMS).

RESPONSE FORMATTING RULES:
1. Always format responses clearly using:
   - Line breaks (`\n\n`) between main thoughts or sections.
   - Numbered lists (`1.`, `2.`, `3.`) when presenting sequences, steps, or multi-part insights.
   - Bullet points (`- `) for listing items, metrics, or recommendations.
   - Double quotes `""` around specific item names, category names, unit names, or voucher numbers (e.g., item "Coat ECC", unit "19_DOU", voucher "V-6768").
2. Highlight key business metrics (stock levels, deficiencies, transaction trends, demand forecasts).
3. Base answers STRICTLY on the provided database context. NEVER fabricate numbers or records.
4. If data is unavailable, state: "I couldn't find any matching records in the database."
5. Explain recommendations clearly with reasoning.
6. Maintain a professional, structured executive tone.
"""


def build_ollama_prompt(
    user_query: str,
    intent: str,
    db_context: Optional[Dict[str, Any]] = None,
    prediction_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Construct a grounded user prompt payload including database context for Ollama.
    """
    context_str = ""

    if db_context:
        context_str += f"\nDATABASE CONTEXT ({intent}):\n"
        context_str += f"{db_context}\n"

    if prediction_context:
        context_str += "\nML DEMAND PREDICTION CONTEXT:\n"
        context_str += f"{prediction_context}\n"

    prompt_payload = (
        f"USER INQUIRY: {user_query}\n"
        f"{context_str}\n"
        "INSTRUCTION: Format your response clearly using bullet points (`-`), end lines (`\n\n`), numbering (`1.`, `2.`), and double quotes (`\"\"`) around item/unit names. Answer accurately and concisely in 2-4 sentences or structured points."
    )
    return prompt_payload
