"""
Chart Generator Module for CMS AI Business Assistant.
Generates structured metadata for dynamic frontend visualizations (Line, Bar, Pie, Doughnut, Scatter).
"""

from typing import Dict, Any, List, Optional
from aiml.chatbot.intent_classifier import (
    INTENT_INVENTORY, INTENT_SALES, INTENT_ORDERS, INTENT_SUPPLIERS,
    INTENT_CUSTOMERS, INTENT_PRODUCTS, INTENT_DASHBOARD_INSIGHTS,
    INTENT_DEMAND_PREDICTION, INTENT_LOW_STOCK
)


def generate_chart_data(
    intent: str,
    db_data: Dict[str, Any],
    prompt: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Decide optimal chart type and generate structured JSON metadata for Chart.js.
    """
    clean_prompt = prompt.lower()

    # 1. Low Stock & Deficiency Comparison -> Bar Chart or Scatter
    if intent == INTENT_LOW_STOCK or "low stock" in clean_prompt:
        low_items = db_data.get("low_stock", []) if isinstance(db_data, dict) else db_data
        if not low_items:
            return None

        labels = [item.get("item_name", "Item")[:15] for item in low_items[:6]]
        held_vals = [item.get("held", 0) for item in low_items[:6]]
        auth_vals = [item.get("auth", 0) for item in low_items[:6]]

        # Scatter chart if user asks for correlation
        if "correlation" in clean_prompt or "scatter" in clean_prompt:
            scatter_points = [{"x": item.get("auth", 0), "y": item.get("held", 0)} for item in low_items[:8]]
            return {
                "visualization": True,
                "chart_type": "scatter",
                "title": "Auth vs Held Stock Correlation",
                "labels": [item.get("item_name", "")[:12] for item in low_items[:8]],
                "datasets": [{
                    "label": "Stock Items",
                    "data": scatter_points,
                    "backgroundColor": "#6366f1"
                }]
            }

        return {
            "visualization": True,
            "chart_type": "bar",
            "title": "Low Stock Items (Held vs Auth Limit)",
            "labels": labels,
            "values": held_vals,
            "datasets": [
                {"label": "Held Quantity", "data": held_vals, "backgroundColor": "#f43f5e"},
                {"label": "Auth Limit", "data": auth_vals, "backgroundColor": "#3b82f6"}
            ]
        }

    # 2. Sales & Monthly Trend -> Line Chart
    if intent == INTENT_SALES or "sales" in clean_prompt or "trend" in clean_prompt:
        top_items = db_data.get("top_issued_items", [])
        if top_items:
            labels = [item["item_name"][:15] for item in top_items]
            values = [item["qty"] for item in top_items]
            return {
                "visualization": True,
                "chart_type": "line",
                "title": "Top Issued Clothing Items Trend",
                "labels": labels,
                "values": values,
                "datasets": [{
                    "label": "Quantity Issued",
                    "data": values,
                    "borderColor": "#10b981",
                    "backgroundColor": "rgba(16, 185, 129, 0.15)",
                    "fill": True,
                    "tension": 0.3
                }]
            }

    # 3. Category Distribution -> Pie / Doughnut Chart
    if intent in (INTENT_INVENTORY, INTENT_PRODUCTS) or "category" in clean_prompt or "distribution" in clean_prompt:
        categories = db_data.get("categories_breakdown", {})
        if not categories and "category_sales" in db_data:
            categories = db_data["category_sales"]

        if categories:
            labels = list(categories.keys())[:6]
            values = [categories[k] for k in labels]
            chart_kind = "doughnut" if "doughnut" in clean_prompt else "pie"

            return {
                "visualization": True,
                "chart_type": chart_kind,
                "title": "Inventory Category Distribution",
                "labels": labels,
                "values": values,
                "datasets": [{
                    "label": "Item Count",
                    "data": values,
                    "backgroundColor": [
                        "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#64748b"
                    ]
                }]
            }

    # 4. Demand Prediction -> Line or Bar Chart
    if intent == INTENT_DEMAND_PREDICTION:
        predictions = db_data.get("predictions", [])
        if predictions:
            labels = [p["item_name"][:15] for p in predictions[:5]]
            curr_vals = [p["current_held"] for p in predictions[:5]]
            proj_vals = [p["projected_next_month_demand"] for p in predictions[:5]]

            return {
                "visualization": True,
                "chart_type": "bar",
                "title": "Next Month Demand Prediction vs Current Stock",
                "labels": labels,
                "values": proj_vals,
                "datasets": [
                    {"label": "Current Stock", "data": curr_vals, "backgroundColor": "#0ea5e9"},
                    {"label": "Projected Demand", "data": proj_vals, "backgroundColor": "#8b5cf6"}
                ]
            }

    # 5. Customer Unit Strengths -> Bar Chart
    if intent == INTENT_CUSTOMERS:
        units = db_data.get("units_list", [])
        if units:
            labels = [u["name"][:12] for u in units[:6]]
            posted = [u["posted"] for u in units[:6]]
            auth = [u["auth"] for u in units[:6]]
            return {
                "visualization": True,
                "chart_type": "bar",
                "title": "Unit Authorized vs Posted Personnel Strength",
                "labels": labels,
                "values": posted,
                "datasets": [
                    {"label": "Posted Strength", "data": posted, "backgroundColor": "#10b981"},
                    {"label": "Auth Strength", "data": auth, "backgroundColor": "#6366f1"}
                ]
            }

    return None
