"""
Summary Tool Module for CMS AI Assistant.
Aggregates database query results into structured summary texts.
"""

from typing import Dict, Any


class SummaryTool:
    """Aggregates database query results into structured summary texts."""

    @staticmethod
    def execute(intent: str, db_data: Dict[str, Any]) -> Dict[str, Any]:
        lines = []

        if intent == "PRODUCT_INFO":
            if db_data.get("found"):
                lines.append(f"Product Availability for \"{db_data['item_name']}\":")
                lines.append(f"- Total Available Stock: {db_data['total_available']} units")
                lines.append(f"- Held in Units: {db_data['held_in_units']} (SER: {db_data['ser']}, PWS: {db_data['pws']})")
                lines.append(f"- Reserve Stock: {db_data['reserve_stock']} units")
                lines.append(f"- FOD Depot Stock: {db_data['fod_depot_stock']} units")
            elif "items" in db_data:
                lines.append(f"Catalog Products Breakdown ({db_data.get('category', 'All')}):")
                lines.append(f"- Total Items Found: {db_data.get('total_count', 0)}")
                for item in db_data.get("items", [])[:6]:
                    lines.append(f"- Item \"{item['item_name']}\" (Category: \"{item['category']}\")")
            else:
                lines.append(f"Product Information: {db_data.get('message', 'No records found.')}")

        elif intent == "CATEGORY_COMPARISON":
            comp = db_data.get("comparison", {})
            lines.append("Category Stock & Issuance Comparison:")
            for cat, metrics in comp.items():
                lines.append(f"- \"{cat}\": {metrics['catalog_items']} catalog items | {metrics['held_stock']} held in units | {metrics['issued_stock']} issued")

        elif intent == "LOW_STOCK_DEFICIENCY":
            defs = db_data.get("top_deficiencies", [])
            lines.append(f"Found {len(defs)} unit deficiency records:")
            for item in defs[:5]:
                lines.append(f"- Unit \"{item['unit_name']}\" (Item \"{item['item_name']}\"): Held {item['held']} / Auth {item['auth']} (Deficiency: {item['deficiency']})")

        elif intent == "INVENTORY_SUMMARY":
            lines.append("CMS Overall Inventory Summary:")
            lines.append(f"- Total Catalog Items: {db_data.get('total_items_catalog', 0)}")
            lines.append(f"- Total Held Stock: {db_data.get('total_held_stock', 0)} units")
            lines.append(f"- Serviceable (SER): {db_data.get('serviceable_ser', 0)} | Partially Working (PWS): {db_data.get('partially_working_pws', 0)}")
            lines.append(f"- Reserve Stock: {db_data.get('reserve_stock', 0)} units")

        elif intent == "SALES_ISSUANCE":
            lines.append("Sales & Item Issuance Insights:")
            lines.append(f"- Total Transactions: {db_data.get('total_transactions', 0)}")
            top_items = db_data.get("top_issued_items", [])
            for i in top_items[:5]:
                lines.append(f"- Item \"{i['item_name']}\": {i['issued_qty']} units issued")

        elif intent == "USER_INFO":
            lines.append("CMS User & Access Overview:")
            lines.append(f"- Total Registered Accounts: {db_data.get('total_users', 0)}")
            roles = db_data.get("roles_breakdown", {})
            for r, count in roles.items():
                lines.append(f"- Role \"{r}\": {count} users")

        elif intent == "AUTHORIZATION_INFO":
            lines.append("Unit Authorization & Limits Details:")
            lines.append(f"- Total Authorization Records: {db_data.get('total_records', 0)}")
            records = db_data.get("authorizations", [])
            for rec in records[:5]:
                lines.append(f"- Unit \"{rec['unit_name']}\" (Item \"{rec['item_name']}\"): Auth limit {rec['auth']}")

        elif intent == "RESERVE_STOCK":
            lines.append("CMS Reserve & FOD Depot Stock Summary:")
            lines.append(f"- Total Reserve Stock in Units: {db_data.get('reserve_in_units', 0)} units")
            lines.append(f"- Total FOD Depot Stock: {db_data.get('fod_depot_stock', 0)} units")
            lines.append(f"- Grand Total Reserve Stock: {db_data.get('grand_total_reserve', 0)} units")

        elif intent == "REPORT_GEN":
            lines.append("CMS Executive Inventory Report:")
            lines.append(f"- Total Catalog Products: {db_data.get('catalog_items_count', 0)}")
            lines.append(f"- Total Stock Held: {db_data.get('total_held_stock', 0)} units")
            lines.append(f"- Outstanding Unit Deficiencies: {db_data.get('deficiencies_count', 0)} items")

        else:
            lines.append("CMS Inventory Information:")
            lines.append("- Information fetched successfully from CMS database.")

        summary_text = "\n".join(lines)
        return {
            "tool": "SummaryTool",
            "summary_text": summary_text
        }
