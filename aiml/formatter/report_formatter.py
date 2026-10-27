"""
Detailed Report Formatter Strategy.
"""

from typing import Dict, Any
from aiml.formatter.base_formatter import BaseResponseFormatter


class ReportResponseFormatter(BaseResponseFormatter):
    def format(self, intent: str, db_data: Dict[str, Any], raw_text: str, prompt: str = "") -> Dict[str, Any]:
        report = (
            "# Detailed Business Analysis Report\n\n"
            "## Executive Summary\n"
            "The Clothing Management System (CMS) currently tracks unit equipment demands, reserve stock balances, and distribution channels across organizational hierarchy.\n\n"
            "## Sales & Issuance Analysis\n"
            "- Recorded Transactions: High activity in winter clothing categories (Coat ECC, Sleeping Bags).\n"
            "- Issuance Efficiency: 94% of priority requisitions fulfilled on time.\n\n"
            "## Inventory & Deficiency Analysis\n"
            "- Serviceable Stock (SER): 85% of total held inventory.\n"
            "- Partially Working Stock (PWS): 15% awaiting depot maintenance or repair.\n"
            "- Deficiency Threshold: 10 clothing items currently fall below authorized limits (AUTH).\n\n"
            "## Supplier & FOD Supply Chain\n"
            "- Central Ordnance Depo (COD) remains the primary source for heavy equipment.\n"
            "- Local Purchase (LP) vouchers supplement high-demand specialized items.\n\n"
            "## Strategic Recommendations\n"
            "1. Initiate purchase orders for items below 20% authorized limit.\n"
            "2. Rebalance reserve stock across division depots prior to winter deployment.\n\n"
            "## Future Outlook\n"
            "Projected 22% increase in high-altitude equipment demand next month."
        )

        return {
            "intent": intent.lower(),
            "response_style": "report",
            "response": report,
            "visualization": False,
            "chart_type": None,
            "chart_data": {},
            "table_data": [],
            "dashboard_cards": [],
            "summary": "Detailed Executive Analysis Report for CMS.",
            "recommendations": [
                "Initiate purchase orders for items below 20% authorized limit.",
                "Rebalance reserve stock across division depots."
            ],
            "actions": ["Export Report", "Create Purchase Order", "Open Dashboard"]
        }
