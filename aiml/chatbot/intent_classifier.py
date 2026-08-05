"""
Intent Classifier Module for CMS AI Business Assistant.
Classifies user queries into specific business intents before routing.
"""

import re
from typing import Dict, Any

# Supported Intents
INTENT_INVENTORY = "Inventory"
INTENT_SALES = "Sales"
INTENT_ORDERS = "Orders"
INTENT_SUPPLIERS = "Suppliers"
INTENT_CUSTOMERS = "Customers"
INTENT_PRODUCTS = "Products"
INTENT_DASHBOARD_INSIGHTS = "Dashboard Insights"
INTENT_DEMAND_PREDICTION = "Demand Prediction"
INTENT_LOW_STOCK = "Low Stock Detection"
INTENT_GENERAL = "General Conversation"

# Intent keyword rules ordered by priority (high-specificity first)
INTENT_PATTERNS = [
    (
        INTENT_LOW_STOCK,
        [
            r"low.*stock", r"low in stock", r"out of stock", r"deficienc", r"below auth",
            r"run out", r"restock needed", r"need restocking", r"shortage",
            r"depleted"
        ]
    ),
    (
        INTENT_DEMAND_PREDICTION,
        [
            r"predict", r"forecast", r"next month", r"future demand",
            r"popular next month", r"what will sell", r"demand prediction",
            r"restock prediction", r"trend prediction"
        ]
    ),
    (
        INTENT_INVENTORY,
        [
            r"inventory summary", r"show inventory", r"inventory level", r"reserve stock", r"ser stock",
            r"pws stock", r"available stock", r"stock level", r"stock count", r"inventory"
        ]
    ),
    (
        INTENT_SALES,
        [
            r"sale", r"sold", r"transaction", r"issued item", r"distribution",
            r"issued to unit", r"today'?s sales", r"monthly sales", r"top-selling",
            r"top selling", r"best selling"
        ]
    ),
    (
        INTENT_ORDERS,
        [
            r"order", r"request", r"item request", r"pending request",
            r"approval", r"priority request", r"requisition", r"item_request"
        ]
    ),
    (
        INTENT_SUPPLIERS,
        [
            r"supplier", r"vendor", r"fod stock", r"depo", r"local purchase",
            r"lp source", r"voucher", r"supply chain"
        ]
    ),
    (
        INTENT_CUSTOMERS,
        [
            r"customer", r"unit strength", r"personnel", r"army personnel",
            r"posted strength", r"authorized strength", r"purchase statistics",
            r"unit statistic"
        ]
    ),
    (
        INTENT_DASHBOARD_INSIGHTS,
        [
            r"dashboard insight", r"overview", r"highest profit",
            r"top margin", r"business summary", r"inventory turnover",
            r"performance overview", r"key metrics"
        ]
    ),
    (
        INTENT_PRODUCTS,
        [
            r"product catalog", r"garment catalog", r"category distribution", r"clothing type",
            r"catalog", r"ecc item", r"scme item", r"denim", r"product"
        ]
    ),
]


def classify_intent(prompt: str, memory_context: Dict[str, Any] = None) -> str:
    """
    Classify the prompt string into one of the supported intents.
    Takes conversation memory into account for follow-up questions.
    """
    clean_prompt = prompt.lower().strip()

    # Direct pattern matching with prioritized rules
    for intent, patterns in INTENT_PATTERNS:
        for pattern in patterns:
            if re.search(r"\b" + pattern, clean_prompt):
                return intent

    # Follow-up context check (e.g. User: "Show low stock", then "Only shirts")
    if memory_context and memory_context.get("last_intent"):
        words = clean_prompt.split()
        if len(words) <= 5 and any(kw in clean_prompt for kw in ["only", "just", "show", "filter", "which"]):
            return memory_context["last_intent"]

    return INTENT_GENERAL
