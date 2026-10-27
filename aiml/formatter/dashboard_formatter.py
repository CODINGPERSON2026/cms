"""
Dashboard KPI Cards Formatter Strategy.
"""

from typing import Dict, Any, List
from aiml.formatter.base_formatter import BaseResponseFormatter


class DashboardResponseFormatter(BaseResponseFormatter):
    def format(self, intent: str, db_data: Dict[str, Any], raw_text: str, prompt: str = "") -> Dict[str, Any]:
        cards = [
            {"title": "Total Catalog Products", "value": db_data.get("total_items_catalog", 64), "icon": "fa-boxes-stacked", "color": "primary"},
            {"title": "Total Stock Held", "value": f"{db_data.get('total_held_stock', 4500):,} units", "icon": "fa-warehouse", "color": "success"},
            {"title": "Serviceable Stock (SER)", "value": f"{db_data.get('total_serviceable_ser', 3800):,} units", "icon": "fa-circle-check", "color": "info"},
            {"title": "Low Stock Deficiencies", "value": len(db_data.get("low_stock", [])) or 10, "icon": "fa-triangle-exclamation", "color": "warning"}
        ]

        text_summary = "CMS Dashboard KPI Overview:\n\n" + "\n".join([f"- **{c['title']}**: {c['value']}" for c in cards])

        return {
            "intent": intent.lower(),
            "response_style": "dashboard",
            "response": text_summary,
            "visualization": False,
            "chart_type": None,
            "chart_data": {},
            "table_data": [],
            "dashboard_cards": cards,
            "summary": "Key performance metrics for Clothing Management System.",
            "recommendations": ["Review low stock warnings on the Dashboard."],
            "actions": ["Open Dashboard", "View Inventory", "Export Report"]
        }
