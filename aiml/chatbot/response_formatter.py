"""
Response Formatter Module for CMS AI Assistant.
Formats structured response payloads, integrating dynamic styles (Tables, Lists, Markdown)
and chart request structures.
"""

from typing import Dict, Any, List, Optional
from aiml.formatter.style_detector import detect_response_style
from aiml.formatter.style_factory import StyleFormatterFactory

SUGGESTED_ACTIONS = {
    "LOW_STOCK_DEFICIENCY": ["Create Purchase Order", "Contact Supplier", "View Inventory", "Open Dashboard"],
    "INVENTORY_SUMMARY": ["Open Dashboard", "View Inventory", "Export Report"],
    "SALES_ISSUANCE": ["View Sales Report", "Export Report", "Open Dashboard"],
    "CATEGORY_COMPARISON": ["View Category Details", "Export Report", "Open Dashboard"],
    "DYNAMIC_CHART": ["Interact with Chart", "Export Chart", "Open Dashboard"],
    "PRODUCT_INFO": ["View Product Catalog", "Check Stock Levels", "Open Dashboard"],
    "UNIT_INFO": ["View Unit Strengths", "Open Dashboard"],
    "GREETING": ["Open Dashboard", "View Inventory Summary", "Compare Categories"],
    "HELP": ["View Examples", "Open Dashboard"]
}


def build_structured_response(
    response_text: str,
    intent: str,
    chart_metadata: Optional[Dict[str, Any]] = None,
    chart_request: Optional[Dict[str, Any]] = None,
    custom_recommendations: Optional[List[str]] = None,
    custom_actions: Optional[List[str]] = None,
    db_data: Optional[Dict[str, Any]] = None,
    prompt: str = ""
) -> Dict[str, Any]:
    """
    Constructs the final JSON payload sent over Server-Sent Events (SSE) or REST endpoint.
    """
    db_data = db_data or {}
    primary_style, _ = detect_response_style(prompt, intent.lower())

    formatter = StyleFormatterFactory.get_formatter(primary_style)
    payload = formatter.format(intent, db_data, response_text, prompt)

    # Attach chart request & visualization metadata
    if chart_metadata and chart_metadata.get("visualization"):
        payload["visualization"] = True
        payload["chart_type"] = chart_metadata.get("chart_type", "bar")
        payload["chart_data"] = chart_metadata
        if chart_request:
            payload["chart_request"] = chart_request
        elif chart_metadata.get("chart_request"):
            payload["chart_request"] = chart_metadata.get("chart_request")
    elif chart_request:
        payload["chart_request"] = chart_request

    # Actions and recommendations
    if custom_recommendations:
        payload["recommendations"] = custom_recommendations
    if custom_actions:
        payload["actions"] = custom_actions
    elif not payload.get("actions"):
        payload["actions"] = SUGGESTED_ACTIONS.get(intent, ["Open Dashboard", "View Inventory"])

    payload["intent"] = intent.lower()
    payload["response_style"] = primary_style
    return payload
