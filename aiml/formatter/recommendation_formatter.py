"""
Business Recommendation Formatter Strategy.
Formats recommendations with Reason, Impact, Priority, and Suggested Action.
"""

from typing import Dict, Any
from aiml.formatter.base_formatter import BaseResponseFormatter


class RecommendationResponseFormatter(BaseResponseFormatter):
    def format(self, intent: str, db_data: Dict[str, Any], raw_text: str, prompt: str = "") -> Dict[str, Any]:
        recs_list = [
            {
                "recommendation": "Increase stock level of heavy winter garments and sleeping bags.",
                "reason": "Recent transactions show a 35% demand surge and 10 items below authorized limit (AUTH).",
                "priority": "HIGH",
                "impact": "Prevents stockouts during upcoming winter deployment cycles.",
                "action": "Create Purchase Order"
            },
            {
                "recommendation": "Rebalance Reserve Stock (Res SER) across Division Depots.",
                "reason": "Division 19_DOU reserves are depleted by 40% compared to Division 28_DOU.",
                "priority": "MEDIUM",
                "impact": "Ensures equal equipment availability across subordinate military units.",
                "action": "View Inventory"
            }
        ]

        text_output = "Business Recommendations:\n\n"
        for idx, r in enumerate(recs_list, 1):
            text_output += (
                f"{idx}. Recommendation: {r['recommendation']}\n"
                f"   - Reason: {r['reason']}\n"
                f"   - Priority: [{r['priority']}]\n"
                f"   - Expected Impact: {r['impact']}\n"
                f"   - Suggested Action: {r['action']}\n\n"
            )

        return {
            "intent": intent.lower(),
            "response_style": "recommendation",
            "response": text_output.strip(),
            "visualization": False,
            "chart_type": None,
            "chart_data": {},
            "table_data": [],
            "dashboard_cards": [],
            "summary": "Structured business recommendations formatted.",
            "recommendations": [r["recommendation"] for r in recs_list],
            "actions": ["Create Purchase Order", "Contact Supplier", "Open Dashboard"]
        }
