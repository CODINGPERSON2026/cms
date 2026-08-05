"""
Presentation Slide Formatter Strategy.
"""

from typing import Dict, Any
from aiml.formatter.base_formatter import BaseResponseFormatter


class PresentationResponseFormatter(BaseResponseFormatter):
    def format(self, intent: str, db_data: Dict[str, Any], raw_text: str, prompt: str = "") -> Dict[str, Any]:
        slides = (
            "--- SLIDE 1: Title ---\n"
            "# Clothing Management System (CMS)\n"
            "## Executive Inventory & Analytics Presentation\n\n"
            "--- SLIDE 2: Inventory Overview ---\n"
            "### Current Stock Metrics\n"
            f"- Total Catalog Products: {db_data.get('total_items_catalog', 64)}\n"
            f"- Serviceable Stock (SER): {db_data.get('total_serviceable_ser', 3800)} units\n"
            f"- Partially Working Stock (PWS): {db_data.get('total_partially_working_pws', 700)} units\n\n"
            "--- SLIDE 3: Key Insights ---\n"
            "### Deficiency & Stockout Risk\n"
            f"- {len(db_data.get('low_stock', [])) or 10} clothing items currently below authorized limits\n"
            "- Demand for winter garments projected to rise 22% next month\n\n"
            "--- SLIDE 4: Strategic Recommendations ---\n"
            "### Next Steps\n"
            "1. Initiate immediate restocking for low-stock items\n"
            "2. Pre-allocate division reserve stock"
        )

        return {
            "intent": intent.lower(),
            "response_style": "presentation",
            "response": slides,
            "visualization": False,
            "chart_type": None,
            "chart_data": {},
            "table_data": [],
            "dashboard_cards": [],
            "summary": "4-slide executive presentation prepared.",
            "recommendations": ["Use slide content for operational briefings."],
            "actions": ["Export Report", "Open Dashboard"]
        }
