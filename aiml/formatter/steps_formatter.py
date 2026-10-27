"""
Step-by-Step Formatter Strategy.
"""

from typing import Dict, Any
from aiml.formatter.base_formatter import BaseResponseFormatter


class StepsResponseFormatter(BaseResponseFormatter):
    def format(self, intent: str, db_data: Dict[str, Any], raw_text: str, prompt: str = "") -> Dict[str, Any]:
        steps = [
            "1. Retrieve live inventory records from CMS database.",
            "2. Compare current held stock (SER + PWS) against authorized limit (AUTH).",
            "3. Identify shortages, deficiencies, and stockout horizons.",
            "4. Generate purchase requisitions or reserve stock transfer requests.",
            "5. Monitor monthly ECC stock statements for fulfillment status."
        ]
        formatted_steps = "\n".join(steps)

        return {
            "intent": intent.lower(),
            "response_style": "steps",
            "response": formatted_steps,
            "visualization": False,
            "chart_type": None,
            "chart_data": {},
            "table_data": [],
            "dashboard_cards": [],
            "summary": raw_text[:120],
            "recommendations": ["Follow step-by-step procedure for stock replenishment."],
            "actions": ["Create Purchase Order", "View Item Requests"]
        }
