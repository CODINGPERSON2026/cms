"""
Response Formatter Module for CMS AI Assistant.
Formats structured response payloads for natural text, data tables, Plotly visualizations,
and interactive selection menus.
"""

from typing import Dict, Any, List, Optional
from aiml.formatter.style_detector import detect_response_style
from aiml.formatter.style_factory import StyleFormatterFactory


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

    # Attach chart request & visualization metadata ONLY if explicitly generated
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

    payload["intent"] = intent.lower()
    payload["response_style"] = primary_style
    return payload
