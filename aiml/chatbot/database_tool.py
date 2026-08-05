"""
Database Tool Module for CMS AI Assistant.
Executes safe SQLAlchemy database queries via query_builder functions based on intent and entities.
Never executes arbitrary raw SQL strings.
"""

from typing import Dict, Any, Optional
from aiml.chatbot.query_builder import (
    query_products_catalog, query_product_availability, query_unit_deficiencies,
    query_category_comparison, query_issuance_and_issues, query_inventory_summary,
    query_unit_and_dou_info, query_users_info, query_authorization_details,
    query_reserve_stock, query_inventory_report, query_unit_comparison
)


class DatabaseTool:
    """Executes safe SQLAlchemy queries based on intent and extracted parameters."""

    @staticmethod
    def execute(intent: str, entities: Dict[str, Any], prompt: str = "") -> Dict[str, Any]:
        item_filter = entities.get("item_filter")
        category_filter = entities.get("category_filter")
        unit_filter = entities.get("unit_filter")

        if intent == "PRODUCT_INFO":
            if item_filter:
                data = query_product_availability(item_filter)
            else:
                data = query_products_catalog(category_filter=category_filter)

        elif intent == "CATEGORY_COMPARISON":
            data = query_category_comparison()

        elif intent == "LOW_STOCK_DEFICIENCY":
            data = query_unit_deficiencies(unit_filter=unit_filter)

        elif intent == "SALES_ISSUANCE":
            data = query_issuance_and_issues(item_filter=item_filter)

        elif intent == "INVENTORY_SUMMARY":
            data = query_inventory_summary()

        elif intent in ("UNIT_INFO", "DOU_INFO"):
            if "compare" in prompt.lower():
                data = query_unit_comparison()
            else:
                data = query_unit_and_dou_info(unit_name=unit_filter)

        elif intent == "USER_INFO":
            data = query_users_info()

        elif intent == "AUTHORIZATION_INFO":
            data = query_authorization_details(unit_filter=unit_filter)

        elif intent == "RESERVE_STOCK":
            data = query_reserve_stock()

        elif intent == "REPORT_GEN":
            data = query_inventory_report()

        else:
            # Fallback general query
            data = query_inventory_summary()

        return {
            "tool": "DatabaseTool",
            "intent": intent,
            "data": data
        }
