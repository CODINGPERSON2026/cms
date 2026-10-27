"""
Intent Parser Module for CMS AI Assistant.
Parses user natural language prompts into standardized internal intents and extracts entity filters.
Supports flexible phrasing, synonym matching, and context-aware follow-ups.
"""

import re
from typing import Dict, Any, Tuple, Optional

# Supported Internal Intents
INTENT_GREETING = "GREETING"
INTENT_HELP = "HELP"
INTENT_CONVERSATION = "CONVERSATION"
INTENT_INVENTORY_SUMMARY = "INVENTORY_SUMMARY"
INTENT_PRODUCT_INFO = "PRODUCT_INFO"
INTENT_UNIT_INFO = "UNIT_INFO"
INTENT_DOU_INFO = "DOU_INFO"
INTENT_CATEGORY_COMPARISON = "CATEGORY_COMPARISON"
INTENT_DYNAMIC_CHART = "DYNAMIC_CHART"
INTENT_LOW_STOCK_DEFICIENCY = "LOW_STOCK_DEFICIENCY"
INTENT_SALES_ISSUANCE = "SALES_ISSUANCE"
INTENT_AUTHORIZATION_INFO = "AUTHORIZATION_INFO"
INTENT_USER_INFO = "USER_INFO"
INTENT_RESERVE_STOCK = "RESERVE_STOCK"
INTENT_REPORT_GEN = "REPORT_GEN"

# Priority Intent Pattern Rules
INTENT_PATTERNS = [
    (
        INTENT_GREETING,
        [r"^\b(hi|hello|hey|good morning|good afternoon|good evening)\b"]
    ),
    (
        INTENT_HELP,
        [r"^\bhelp\b", r"what can you do", r"how to use", r"capabilities", r"instructions", r"guide"]
    ),
    (
        INTENT_DYNAMIC_CHART,
        [
            r"generate graph", r"show graph", r"draw chart", r"pie chart", r"bar chart",
            r"line chart", r"doughnut chart", r"visualize", r"plot", r"graph of", r"chart of",
            r"monthly stock graph", r"monthly issue trend", r"authorization comparison"
        ]
    ),
    (
        INTENT_REPORT_GEN,
        [
            r"generate .* report", r"inventory report", r"monthly report", r"stock report",
            r"deficiency report", r"summary report", r"export report"
        ]
    ),
    (
        INTENT_USER_INFO,
        [
            r"list logged in users", r"logged in users", r"active users", r"user list",
            r"who is logged in", r"show users", r"cms users", r"show all users", r"inactive users"
        ]
    ),
    (
        INTENT_AUTHORIZATION_INFO,
        [
            r"authorization details", r"authorization summary", r"show authorization", r"item auth",
            r"auth limit", r"scale of issue", r"authorized strength", r"unit auth"
        ]
    ),
    (
        INTENT_RESERVE_STOCK,
        [
            r"current reserve stock", r"reserve stock", r"available reserve", r"fod reserve",
            r"res stock", r"depot reserve"
        ]
    ),
    (
        INTENT_CATEGORY_COMPARISON,
        [
            r"cat-i vs cat-ii", r"cat-1 vs cat-2", r"cat i vs cat ii", r"compare categor",
            r"category comparison", r"category wise", r"category distribution", r"cat-i inventory",
            r"cat-ii inventory", r"show cat-i", r"show cat-ii", r"cat-i", r"cat-ii",
            r"compare inventory by category"
        ]
    ),
    (
        INTENT_LOW_STOCK_DEFICIENCY,
        [
            r"deficiency", r"highest deficiency", r"products with highest deficiency",
            r"low stock", r"out of stock", r"shortage", r"below auth", r"restock needed",
            r"depleted", r"unit .* deficiency"
        ]
    ),
    (
        INTENT_SALES_ISSUANCE,
        [
            r"issued items", r"issued count", r"issued quantity", r"issued this month",
            r"monthly issue", r"transactions", r"sales", r"top issued", r"issued product",
            r"received quantity", r"issue trend", r"product movement"
        ]
    ),
    (
        INTENT_PRODUCT_INFO,
        [
            r"how many .* available", r"available stock of", r"stock available",
            r"show .* stock", r"stock of", r"jacket", r"sweater", r"helmet", r"boot",
            r"coat", r"trouser", r"garment", r"jersey", r"glove", r"item count", r"scme item",
            r"clothing item", r"show all products", r"how many products exist", r"serviceable stock"
        ]
    ),
    (
        INTENT_UNIT_INFO,
        [
            r"compare units", r"unit strength", r"posted strength", r"army personnel",
            r"military unit", r"unit stock", r"which unit", r"show unit", r"list all units"
        ]
    ),
    (
        INTENT_DOU_INFO,
        [
            r"dou", r"division ordnance unit", r"division stock", r"ordnance depot", r"list all dous"
        ]
    ),
    (
        INTENT_INVENTORY_SUMMARY,
        [
            r"monthly inventory summary", r"inventory summary", r"total stock", r"overall inventory",
            r"stock summary", r"how much stock", r"ser stock", r"pws stock", r"inventory status",
            r"display monthly inventory", r"show current inventory summary"
        ]
    ),
]


def parse_intent_and_entities(
    prompt: str,
    memory_context: Optional[Dict[str, Any]] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Parse user prompt into an internal intent string and extracted parameters dictionary.
    Takes conversation memory into context for multi-turn conversations.
    """
    clean_prompt = prompt.lower().strip()
    entities: Dict[str, Any] = {
        "item_filter": None,
        "category_filter": None,
        "unit_filter": None
    }

    # 1. Check for Category Filters
    if "cat-i" in clean_prompt or "cat-1" in clean_prompt:
        entities["category_filter"] = "CAT-I"
    elif "cat-ii" in clean_prompt or "cat-2" in clean_prompt:
        entities["category_filter"] = "CAT-II"

    # 2. Check for Specific Items
    common_items = [
        "jacket", "sweater", "helmet", "boot", "coat", "trouser",
        "jersey", "glove", "bag", "cap", "beret", "uniform", "shirt"
    ]
    for item in common_items:
        if item in clean_prompt:
            entities["item_filter"] = item
            break

    # 3. Check for Unit Filters (e.g., "Unit 2", "19_DOU", "19 DOU", "Division 1")
    unit_match = re.search(r"\b(unit\s*\d+|dou|\d+\s*dou|div\s*\d+)\b", clean_prompt)
    if unit_match:
        entities["unit_filter"] = unit_match.group(0).strip()

    # 4. Direct Pattern Matching
    matched_intent = None
    for intent, patterns in INTENT_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, clean_prompt):
                matched_intent = intent
                break
        if matched_intent:
            break

    if matched_intent:
        return matched_intent, entities

    # 5. Context Awareness & Follow-up Check
    if memory_context and memory_context.get("last_intent"):
        words = clean_prompt.split()
        if len(words) <= 6 and any(kw in clean_prompt for kw in ["only", "just", "show", "filter", "what about", "and"]):
            contextual_intent = memory_context["last_intent"]
            if memory_context.get("last_filter") and not entities["category_filter"]:
                last_f = memory_context.get("last_filter")
                if last_f in ("CAT-I", "CAT-II"):
                    entities["category_filter"] = last_f

            if not entities["item_filter"]:
                for word in words:
                    w_clean = word.strip(" .!?,")
                    if w_clean not in ["only", "just", "show", "filter", "the", "products", "items", "what", "about", "and"]:
                        entities["item_filter"] = w_clean
                        break
            return contextual_intent, entities

    return INTENT_CONVERSATION, entities
