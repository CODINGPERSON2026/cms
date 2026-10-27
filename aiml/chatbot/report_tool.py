"""
Report Tool Module for CMS AI Assistant.
Generates structured inventory, deficiency, authorization, and stock reports.
"""

from typing import Dict, Any, Optional


class ReportTool:
    """Aggregates and formats executive reports based on CMS live data."""

    @staticmethod
    def execute(intent: str, db_data: Dict[str, Any], prompt: str = "") -> Dict[str, Any]:
        report_title = "CMS Executive Inventory Report"

        if "deficiency" in prompt.lower() or intent == "LOW_STOCK_DEFICIENCY":
            report_title = "CMS Unit Deficiency & Shortage Summary Report"
        elif "cat" in prompt.lower() or intent == "CATEGORY_COMPARISON":
            report_title = "CMS Category Distribution & Stock Comparison Report"
        elif "issue" in prompt.lower() or intent == "SALES_ISSUANCE":
            report_title = "CMS Monthly Sales & Issuance Activity Report"
        elif "reserve" in prompt.lower() or intent == "RESERVE_STOCK":
            report_title = "CMS Reserve & FOD Stock Report"

        sections = []

        if "total_items_catalog" in db_data:
            sections.append({
                "heading": "Catalog Overview",
                "content": f"Total Catalog Items: {db_data.get('total_items_catalog')}, Total Held Stock: {db_data.get('total_held_stock')} units."
            })

        if "top_deficiencies" in db_data:
            defs = db_data.get("top_deficiencies", [])
            sections.append({
                "heading": "Top Unit Deficiencies",
                "items": [f"Unit '{d['unit_name']}' - Item '{d['item_name']}': Auth {d['auth']}, Held {d['held']}, Shortage {d['deficiency']}" for d in defs[:5]]
            })

        if "comparison" in db_data:
            comp = db_data.get("comparison", {})
            sections.append({
                "heading": "Category Breakdown",
                "items": [f"Category '{cat}': {data['catalog_items']} items, {data['held_stock']} held, {data['issued_stock']} issued" for cat, data in comp.items()]
            })

        return {
            "tool": "ReportTool",
            "report_title": report_title,
            "sections": sections,
            "data": db_data
        }
