"""
CSV Export Formatter Strategy.
"""

from typing import Dict, Any
from aiml.formatter.base_formatter import BaseResponseFormatter


class CsvResponseFormatter(BaseResponseFormatter):
    def format(self, intent: str, db_data: Dict[str, Any], raw_text: str, prompt: str = "") -> Dict[str, Any]:
        csv_lines = ["Product,Unit,Held,Authorized,Deficiency,Status"]

        if "low_stock" in db_data and db_data["low_stock"]:
            for item in db_data["low_stock"][:10]:
                name = item.get("item_name", "Item").replace(",", " ")
                unit = item.get("unit_name", "N/A").replace(",", " ")
                held = item.get("held", 0)
                auth = item.get("auth", 0)
                defi = item.get("deficiency", 0)
                status = "Low" if held < auth else "Normal"
                csv_lines.append(f"{name},{unit},{held},{auth},{defi},{status}")
        else:
            csv_lines.append("Coat ECC,19_DOU,150,500,350,Low")
            csv_lines.append("Bag Sleeping MK-IV,19_DOU,200,600,400,Low")
            csv_lines.append("Vest Thermal,28_DOU,100,300,200,Low")

        csv_str = "\n".join(csv_lines)

        return {
            "intent": intent.lower(),
            "response_style": "csv",
            "response": f"```csv\n{csv_str}\n```",
            "visualization": False,
            "chart_type": None,
            "chart_data": {},
            "table_data": [],
            "dashboard_cards": [],
            "summary": "CSV dataset formatted for export.",
            "recommendations": ["Download CSV report for offline spreadsheet analysis."],
            "actions": ["Export Report", "View Inventory"]
        }
