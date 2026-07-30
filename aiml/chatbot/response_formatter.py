"""
Response Formatter Module for CMS AI Business Assistant.
Integrates Adaptive Response Styles strategy pattern and style detection.
"""

from typing import Dict, Any, List, Optional
from aiml.formatter.style_detector import detect_response_style
from aiml.formatter.style_factory import StyleFormatterFactory
from aiml.chatbot.intent_classifier import (
    INTENT_INVENTORY, INTENT_SALES, INTENT_ORDERS, INTENT_SUPPLIERS,
    INTENT_CUSTOMERS, INTENT_PRODUCTS, INTENT_DASHBOARD_INSIGHTS,
    INTENT_DEMAND_PREDICTION, INTENT_LOW_STOCK, INTENT_GENERAL
)

SUGGESTED_ACTIONS = {
    INTENT_LOW_STOCK: ["Create Purchase Order", "Contact Supplier", "View Inventory", "Open Dashboard"],
    INTENT_DEMAND_PREDICTION: ["Restock Immediately", "Create Purchase Order", "Contact Supplier", "Export Report"],
    INTENT_INVENTORY: ["Open Dashboard", "View Inventory", "Export Report"],
    INTENT_SALES: ["View Sales Report", "Export Report", "Open Dashboard"],
    INTENT_ORDERS: ["Create Purchase Order", "View Item Requests", "Open Dashboard"],
    INTENT_SUPPLIERS: ["Contact Supplier", "View FOD Stock", "Create Purchase Order"],
    INTENT_CUSTOMERS: ["View Unit Strengths", "Open Dashboard"],
    INTENT_DASHBOARD_INSIGHTS: ["Open Dashboard", "Export Report", "View Sales Report"],
    INTENT_PRODUCTS: ["View Inventory", "Open Dashboard"],
    INTENT_GENERAL: ["Open Dashboard", "View Inventory"]
}


def build_structured_response(
    response_text: str,
    intent: str,
    chart_metadata: Optional[Dict[str, Any]] = None,
    custom_recommendations: Optional[List[str]] = None,
    custom_actions: Optional[List[str]] = None,
    db_data: Optional[Dict[str, Any]] = None,
    prompt: str = ""
) -> Dict[str, Any]:
    """
    Format final JSON payload using Adaptive Response Style strategy pattern.
    """
    db_data = db_data or {}
    primary_style, secondary_style = detect_response_style(prompt, intent)

    formatter = StyleFormatterFactory.get_formatter(primary_style)
    payload = formatter.format(intent, db_data, response_text, prompt)

    # Attach chart metadata if visualization requested or generated
    if chart_metadata and chart_metadata.get("visualization"):
        payload["visualization"] = True
        payload["chart_type"] = chart_metadata.get("chart_type")
        payload["chart_data"] = chart_metadata

    # Override recommendations & actions if custom supplied
    if custom_recommendations:
        payload["recommendations"] = custom_recommendations
    if custom_actions:
        payload["actions"] = custom_actions
    elif not payload.get("actions"):
        payload["actions"] = SUGGESTED_ACTIONS.get(intent, ["Open Dashboard"])

    payload["response_style"] = primary_style
    return payload
