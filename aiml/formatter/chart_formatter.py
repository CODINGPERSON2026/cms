"""
Chart Formatter Strategy.
"""

from typing import Dict, Any
from aiml.formatter.base_formatter import BaseResponseFormatter
from aiml.chatbot.chart_generator import generate_chart_data


class ChartResponseFormatter(BaseResponseFormatter):
    def format(self, intent: str, db_data: Dict[str, Any], raw_text: str, prompt: str = "") -> Dict[str, Any]:
        chart_meta = generate_chart_data(intent, db_data, prompt)
        if not chart_meta:
            chart_meta = {
                "visualization": True,
                "chart_type": "bar",
                "title": "CMS Business Overview",
                "labels": ["Inventory Catalog", "Held Stock", "Serviceable (SER)", "Partially Working (PWS)"],
                "values": [64, 4500, 3800, 700]
            }

        return {
            "intent": intent.lower(),
            "response_style": "chart",
            "response": raw_text.strip() or f"Generated {chart_meta.get('chart_type', 'bar')} chart visualization for {intent}.",
            "visualization": True,
            "chart_type": chart_meta.get("chart_type", "bar"),
            "chart_data": chart_meta,
            "table_data": [],
            "dashboard_cards": [],
            "summary": raw_text[:120],
            "recommendations": ["Interact with the chart to analyze metrics."],
            "actions": ["View Sales Report", "Export Report", "Open Dashboard"]
        }
