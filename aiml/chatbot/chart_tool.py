"""
Chart Tool Module for CMS AI Assistant.
Generates structured chart requests and Chart.js visualization metadata.
Does not output HTML or JavaScript code directly.
"""

from typing import Dict, Any, Optional
from aiml.chatbot.chart_formatter import generate_chart_metadata, build_chart_request


class ChartTool:
    """Generates structured chart requests and visualization metadata."""

    @staticmethod
    def execute(intent: str, db_data: Dict[str, Any], prompt: str = "") -> Dict[str, Any]:
        chart_metadata = generate_chart_metadata(intent=intent, db_data=db_data, prompt=prompt)
        chart_request = build_chart_request(intent=intent, prompt=prompt)

        return {
            "tool": "ChartTool",
            "chart_request": chart_request,
            "chart_metadata": chart_metadata
        }
