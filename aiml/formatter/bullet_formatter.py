"""
Bullet List Formatter Strategy.
"""

from typing import Dict, Any
from aiml.formatter.base_formatter import BaseResponseFormatter


class BulletResponseFormatter(BaseResponseFormatter):
    def format(self, intent: str, db_data: Dict[str, Any], raw_text: str, prompt: str = "") -> Dict[str, Any]:
        bullets = []

        if "low_stock" in db_data:
            for item in db_data["low_stock"][:6]:
                bullets.append(f"• {item.get('item_name', 'Item')} — Held: {item.get('held', 0)} / Auth: {item.get('auth', 0)}")
        elif "top_issued_items" in db_data:
            for item in db_data["top_issued_items"][:6]:
                bullets.append(f"• {item.get('item_name', 'Item')} — Issued: {item.get('qty', 0)} units")
        elif "categories_breakdown" in db_data:
            for cat, count in list(db_data["categories_breakdown"].items())[:6]:
                bullets.append(f"• {cat} — {count} items")

        if not bullets:
            # Fallback formatting raw text lines as bullets
            lines = [l.strip(" •-*1234567890.") for l in raw_text.split("\n") if l.strip()]
            bullets = [f"• {l}" for l in lines[:6]]

        formatted_text = "\n".join(bullets)

        return {
            "intent": intent.lower(),
            "response_style": "bullet",
            "response": formatted_text,
            "visualization": False,
            "chart_type": None,
            "chart_data": {},
            "table_data": [],
            "dashboard_cards": [],
            "summary": raw_text[:120],
            "recommendations": ["Review bulleted metrics for unit allocation."],
            "actions": ["View Inventory", "Export Report"]
        }
