"""
Executive Summary Formatter Strategy.
"""

from typing import Dict, Any
from aiml.formatter.base_formatter import BaseResponseFormatter


class SummaryResponseFormatter(BaseResponseFormatter):
    def format(self, intent: str, db_data: Dict[str, Any], raw_text: str, prompt: str = "") -> Dict[str, Any]:
        summary_text = (
            "Executive Summary:\n\n"
            "The Clothing Management System is maintaining steady operational inventory levels. "
            "Currently, 85% of held inventory is fully serviceable (SER), while 10 items have active deficiencies requiring replenishment. "
            "Demand for winter garments is projected to rise 22% next month, making pre-allocation of division reserve stock a key priority."
        )

        return {
            "intent": intent.lower(),
            "response_style": "summary",
            "response": summary_text,
            "visualization": False,
            "chart_type": None,
            "chart_data": {},
            "table_data": [],
            "dashboard_cards": [],
            "summary": summary_text,
            "recommendations": ["Focus replenishment on items with active deficiency."],
            "actions": ["Open Dashboard", "View Inventory"]
        }
