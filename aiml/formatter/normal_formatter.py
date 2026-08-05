"""
Normal Conversational Formatter Strategy.
"""

from typing import Dict, Any
from aiml.formatter.base_formatter import BaseResponseFormatter


class NormalResponseFormatter(BaseResponseFormatter):
    def format(self, intent: str, db_data: Dict[str, Any], raw_text: str, prompt: str = "") -> Dict[str, Any]:
        return {
            "intent": intent.lower(),
            "response_style": "normal",
            "response": raw_text.strip(),
            "visualization": False,
            "chart_type": None,
            "chart_data": {},
            "table_data": [],
            "dashboard_cards": [],
            "summary": "",
            "recommendations": ["Monitor stock levels on the CMS dashboard."],
            "actions": ["Open Dashboard", "View Inventory"]
        }
