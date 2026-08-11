"""
Table Formatter Strategy.
"""

from typing import Dict, Any, List
from aiml.formatter.base_formatter import BaseResponseFormatter


class TableResponseFormatter(BaseResponseFormatter):
    def format(self, intent: str, db_data: Dict[str, Any], raw_text: str, prompt: str = "") -> Dict[str, Any]:
        table_rows = []
        md_table_lines = []

        records = (
            db_data.get("records") or
            db_data.get("units") or
            db_data.get("comparison") or
            db_data.get("authorizations") or
            db_data.get("items") or
            db_data.get("sample_users")
        )

        if records and isinstance(records, list) and len(records) > 0 and isinstance(records[0], dict):
            keys = list(records[0].keys())
            headers = [k.replace("_", " ").title() for k in keys]
            md_table_lines.append("| " + " | ".join(headers) + " |")
            md_table_lines.append("|" + "|".join(["---"] * len(keys)) + "|")

            for rec in records:
                row_vals = [str(rec.get(k, "")) for k in keys]
                md_table_lines.append("| " + " | ".join(row_vals) + " |")
                table_rows.append(rec)

        elif "low_stock" in db_data:
            md_table_lines = [
                "| Product / Item | Unit | Held | Auth | Status |",
                "|---|---|---|---|---|"
            ]
            for item in db_data["low_stock"][:6]:
                row = {
                    "product": item.get("item_name", "Item"),
                    "unit": item.get("unit_name", "N/A"),
                    "held": item.get("held", 0),
                    "auth": item.get("auth", 0),
                    "status": "Low" if item.get("held", 0) < item.get("auth", 0) else "Good"
                }
                table_rows.append(row)
                md_table_lines.append(f"| {row['product']} | {row['unit']} | {row['held']} | {row['auth']} | {row['status']} |")

        elif "top_issued_items" in db_data:
            md_table_lines = [
                "| Product / Item | Issued Quantity | Category |",
                "|---|---|---|"
            ]
            for item in db_data["top_issued_items"][:6]:
                row = {
                    "product": item.get("item_name", "Item"),
                    "issued_qty": item.get("issued_qty", item.get("qty", 0)),
                    "category": "Clothing"
                }
                table_rows.append(row)
                md_table_lines.append(f"| {row['product']} | {row['issued_qty']} | {row['category']} |")

        else:
            md_table_lines = [
                "| Metric | Value | Status |",
                "|---|---|---|",
                f"| Inventory Items | {db_data.get('total_items_catalog', 64)} | Active |",
                f"| Total Held Stock | {db_data.get('total_held_stock', 5000)} | Operational |"
            ]
            table_rows = [
                {"metric": "Inventory Items", "value": db_data.get("total_items_catalog", 64), "status": "Active"},
                {"metric": "Total Held Stock", "value": db_data.get("total_held_stock", 5000), "status": "Operational"}
            ]

        formatted_md = "\n".join(md_table_lines)

        return {
            "intent": intent.lower(),
            "response_style": "table",
            "response": formatted_md,
            "visualization": False,
            "chart_type": None,
            "chart_data": {},
            "table_data": table_rows,
            "dashboard_cards": [],
            "summary": raw_text[:120],
            "recommendations": ["Filter table columns on the inventory dashboard."],
            "actions": ["Export Report", "View Inventory", "Create Purchase Order"]
        }
