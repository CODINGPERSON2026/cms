"""
Email Formatter Strategy.
"""

from typing import Dict, Any
from aiml.formatter.base_formatter import BaseResponseFormatter


class EmailResponseFormatter(BaseResponseFormatter):
    def format(self, intent: str, db_data: Dict[str, Any], raw_text: str, prompt: str = "") -> Dict[str, Any]:
        email_body = (
            "Subject: Executive Inventory & Stock Status Update — CMS\n\n"
            "Dear CMS Leadership Team,\n\n"
            "Here is the latest inventory status update from the Clothing Management System database:\n\n"
            f"- Total Active Catalog Items: {db_data.get('total_items_catalog', 64)}\n"
            f"- Total Held Stock across Units: {db_data.get('total_held_stock', 4500)} units\n"
            f"- Serviceable Stock (SER): {db_data.get('total_serviceable_ser', 3800)} units\n"
            f"- Low Stock Deficiencies: {len(db_data.get('low_stock', [])) or 10} clothing items\n\n"
            "Action Requested:\n"
            "Please review and approve purchase requisitions for items below authorized limit.\n\n"
            "Best regards,\n"
            "CMS AI Business Assistant\n"
            "Clothing Management System"
        )

        return {
            "intent": intent.lower(),
            "response_style": "email",
            "response": email_body,
            "visualization": False,
            "chart_type": None,
            "chart_data": {},
            "table_data": [],
            "dashboard_cards": [],
            "summary": "Email draft generated for executive dispatch.",
            "recommendations": ["Copy email text or send via automated CMS mailer."],
            "actions": ["Create Purchase Order", "Contact Supplier", "Export Report"]
        }
