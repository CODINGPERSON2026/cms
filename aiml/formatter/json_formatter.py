"""
JSON Formatter Strategy.
"""

import json
from typing import Dict, Any
from aiml.formatter.base_formatter import BaseResponseFormatter


class JsonResponseFormatter(BaseResponseFormatter):
    def format(self, intent: str, db_data: Dict[str, Any], raw_text: str, prompt: str = "") -> Dict[str, Any]:
        json_obj = {
            "system": "Clothing Management System (CMS)",
            "intent": intent,
            "metrics": {
                "total_catalog_items": db_data.get("total_items_catalog", 64),
                "total_held_stock": db_data.get("total_held_stock", 4500),
                "serviceable_ser": db_data.get("total_serviceable_ser", 3800),
                "partially_working_pws": db_data.get("total_partially_working_pws", 700),
                "low_stock_count": len(db_data.get("low_stock", [])) or 10
            },
            "status": "success"
        }
        json_str = json.dumps(json_obj, indent=2)

        return {
            "intent": intent.lower(),
            "response_style": "json",
            "response": f"```json\n{json_str}\n```",
            "visualization": False,
            "chart_type": None,
            "chart_data": {},
            "table_data": [],
            "dashboard_cards": [],
            "summary": "JSON API payload generated.",
            "recommendations": ["Use machine-readable JSON for integration."],
            "actions": ["Export Report", "Open Dashboard"]
        }
