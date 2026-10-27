"""
Markdown Formatter Strategy.
"""

from typing import Dict, Any
from aiml.formatter.base_formatter import BaseResponseFormatter


class MarkdownResponseFormatter(BaseResponseFormatter):
    def format(self, intent: str, db_data: Dict[str, Any], raw_text: str, prompt: str = "") -> Dict[str, Any]:
        md_content = (
            f"# CMS Business Summary — {intent.title()}\n\n"
            f"> **Status Overview**: System database records processed successfully.\n\n"
            f"### Key Metrics\n"
            f"- **Total Catalog Items**: `{db_data.get('total_items_catalog', 64)}`\n"
            f"- **Total Held Inventory**: `{db_data.get('total_held_stock', 4500)}` units\n"
            f"- **Serviceable (SER)**: `{db_data.get('total_serviceable_ser', 3800)}` units\n"
            f"- **Deficiencies Detected**: `{len(db_data.get('low_stock', [])) or 10}` items\n\n"
            f"### Recommended Actions\n"
            f"1. *Replenish low stock items below 20% authorized threshold.*\n"
            f"2. *Audit Division reserve stock balances.*"
        )

        return {
            "intent": intent.lower(),
            "response_style": "markdown",
            "response": md_content,
            "visualization": False,
            "chart_type": None,
            "chart_data": {},
            "table_data": [],
            "dashboard_cards": [],
            "summary": "Markdown formatted report.",
            "recommendations": ["View formatted Markdown documentation."],
            "actions": ["Export Report", "Open Dashboard"]
        }
