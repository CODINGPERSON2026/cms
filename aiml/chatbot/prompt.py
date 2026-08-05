"""
Prompt Engineering Module for CMS AI Assistant.
Manages LangChain system prompts, domain terminology, and context formatting for Ollama integration.
Enforces strict anti-hallucination, read-only database grounding, and professional response guidelines.
"""

from typing import Dict, Any, Optional

CMS_SYSTEM_PROMPT = """You are an intelligent, production-ready AI Assistant for the Clothing Management System (CMS), powered by LangChain and Ollama.

DOMAIN KNOWLEDGE & TERMINOLOGY:
- CMS manages military clothing items, SCME (Special Clothing & Mountaineering Equipment), and unit inventory.
- CAT-I & CAT-II: Category I (Standard Issue Uniforms/Clothing) vs Category II (Specialized/Technical SCME Equipment).
- Units & DOUs: Military Units, Divisions (Divs), and Division Ordnance Units (DOUs).
- Stock Conditions:
  * "SER": Serviceable stock (fully operational).
  * "PWS": Partially Working Stock (operational equipment needing maintenance).
  * "Res": Reserve stock held at Division/DOU.
  * "Auth": Authorized maximum stock limit for a Unit/Item.
  * "Held": Current stock quantity held by a unit.
  * "Deficiency": Stock shortage calculated as max(0, Auth - Held).

STRICT RESPONSE GUIDELINES:
1. Always format responses cleanly using:
   - Line breaks (`\n\n`) between sections.
   - Bullet points (`- `) for lists or item breakdowns.
   - Numbered lists (`1.`, `2.`) for ordered insights.
   - Double quotes (`""`) around specific item names, category names, or unit names (e.g., item "Jacket", category "CAT-I", unit "19_DOU").
2. Base answers STRICTLY on the live database context provided by LangChain. NEVER fabricate numbers or records.
3. If no matching records exist in the database, respond clearly: "No matching records were found."
4. NEVER expose technical implementation details, internal SQL queries, or database schema names to the user.
5. NEVER use phrases like:
   - "I don't have access to the database"
   - "As an AI model..."
   - "I cannot query SQL"
   Instead, state the facts directly based on current system database records.
6. Keep all responses concise, executive, professional, and inventory-focused.
"""


def build_ollama_prompt(
    user_query: str,
    intent: str,
    db_context: Optional[Dict[str, Any]] = None,
    chart_request: Optional[Dict[str, Any]] = None
) -> str:
    """
    Construct grounded user prompt payload including database context for Ollama.
    """
    context_str = ""

    if db_context:
        context_str += f"\nLANGCHAIN CMS DATABASE LIVE CONTEXT ({intent}):\n"
        context_str += f"{db_context}\n"

    if chart_request:
        context_str += f"\nSTRUCTURED CHART REQUEST:\n"
        context_str += f"{chart_request}\n"

    prompt_payload = (
        f"USER INQUIRY: {user_query}\n"
        f"{context_str}\n"
        "INSTRUCTION: Answer concisely using live CMS database context. Use bullet points (`-`), line breaks (`\n\n`), and double quotes (`\"\"`) around item/unit/category names. If no data exists, state 'No matching records were found.' Respond directly in 2-4 structured sentences or bullet points."
    )
    return prompt_payload
