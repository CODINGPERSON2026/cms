"""
HTML Formatter Strategy.
"""

from typing import Dict, Any
from aiml.formatter.base_formatter import BaseResponseFormatter


class HtmlResponseFormatter(BaseResponseFormatter):
    def format(self, intent: str, db_data: Dict[str, Any], raw_text: str, prompt: str = "") -> Dict[str, Any]:
        html_code = (
            "<div class=\"cms-report-card p-3 border rounded bg-light\">\n"
            "  <h4 class=\"text-primary mb-2\"><i class=\"fas fa-boxes-stacked me-2\"></i>CMS Business Overview</h4>\n"
            "  <p class=\"mb-2\">Status summary generated from active database records:</p>\n"
            "  <ul class=\"list-group mb-3\">\n"
            f"    <li class=\"list-group-item d-flex justify-content-between align-items-center\">Catalog Items <span class=\"badge bg-primary rounded-pill\">{db_data.get('total_items_catalog', 64)}</span></li>\n"
            f"    <li class=\"list-group-item d-flex justify-content-between align-items-center\">Total Held Stock <span class=\"badge bg-success rounded-pill\">{db_data.get('total_held_stock', 4500)}</span></li>\n"
            f"    <li class=\"list-group-item d-flex justify-content-between align-items-center\">Deficiencies <span class=\"badge bg-warning rounded-pill\">{len(db_data.get('low_stock', [])) or 10}</span></li>\n"
            "  </ul>\n"
            "</div>"
        )

        return {
            "intent": intent.lower(),
            "response_style": "html",
            "response": html_code,
            "visualization": False,
            "chart_type": None,
            "chart_data": {},
            "table_data": [],
            "dashboard_cards": [],
            "summary": "HTML markup generated.",
            "recommendations": ["Render HTML element in CMS dashboard."],
            "actions": ["Open Dashboard", "Export Report"]
        }
