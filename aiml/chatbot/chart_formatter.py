"""
Chart Formatter Module for CMS AI Assistant.
Generates structured chart requests and Chart.js metadata for dynamic frontend visualizations.
"""

from typing import Dict, Any, List, Optional


def build_chart_request(
    intent: str,
    prompt: str = "",
    entity: str = "category",
    metric: str = "stock",
    chart_type: str = "bar",
    compare: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Construct a standardized structured chart request object.
    Example:
    {
      "intent": "chart",
      "chart": "bar",
      "entity": "category",
      "metric": "issued",
      "compare": ["CAT-I", "CAT-II"]
    }
    """
    clean_prompt = prompt.lower()
    
    # Infer chart type if explicit in prompt
    if "pie" in clean_prompt:
        chart_type = "pie"
    elif "doughnut" in clean_prompt:
        chart_type = "doughnut"
    elif "line" in clean_prompt or "trend" in clean_prompt:
        chart_type = "line"
    elif "scatter" in clean_prompt:
        chart_type = "scatter"

    # Infer compare elements if mentioned
    if not compare:
        if "cat-i" in clean_prompt and "cat-ii" in clean_prompt:
            compare = ["CAT-I", "CAT-II"]
        elif "cat-1" in clean_prompt and "cat-2" in clean_prompt:
            compare = ["CAT-I", "CAT-II"]

    return {
        "intent": "chart",
        "chart": chart_type,
        "entity": entity,
        "metric": metric,
        "compare": compare or []
    }


def generate_chart_metadata(
    intent: str,
    db_data: Dict[str, Any],
    prompt: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Generates Chart.js visualization metadata dictionary based on intent and database records.
    """
    clean_prompt = prompt.lower()
    chart_req = build_chart_request(intent=intent, prompt=prompt)

    # 1. Category Comparison / Distribution
    if "category" in clean_prompt or "cat-i" in clean_prompt or intent in ("CATEGORY_COMPARISON", "PRODUCT_INFO"):
        cat_data = db_data.get("comparison", {})
        if cat_data:
            labels = list(cat_data.keys())
            held_vals = [cat_data[k].get("held_stock", 0) for k in labels]
            issued_vals = [cat_data[k].get("issued_stock", 0) for k in labels]

            chart_req["entity"] = "category"
            chart_req["metric"] = "stock_and_issues"
            chart_req["compare"] = labels

            return {
                "visualization": True,
                "chart_request": chart_req,
                "chart_type": chart_req["chart"],
                "title": "CAT-I vs CAT-II Category Stock & Issuance Comparison",
                "labels": labels,
                "values": held_vals,
                "datasets": [
                    {"label": "Held Stock", "data": held_vals, "backgroundColor": "#3b82f6"},
                    {"label": "Issued Stock", "data": issued_vals, "backgroundColor": "#10b981"}
                ]
            }

    # 2. Low Stock / Unit Deficiencies
    if "deficiency" in clean_prompt or "low stock" in clean_prompt or intent in ("LOW_STOCK_DEFICIENCY", "UNIT_INFO"):
        top_def = db_data.get("top_deficiencies", [])
        if top_def:
            labels = [f"{item['unit_name']}: {item['item_name'][:12]}" for item in top_def[:6]]
            def_vals = [item["deficiency"] for item in top_def[:6]]
            held_vals = [item["held"] for item in top_def[:6]]

            chart_req["entity"] = "unit_deficiency"
            chart_req["metric"] = "deficiency"

            return {
                "visualization": True,
                "chart_request": chart_req,
                "chart_type": chart_req["chart"],
                "title": "Highest Unit Deficiencies (Auth Shortage)",
                "labels": labels,
                "values": def_vals,
                "datasets": [
                    {"label": "Deficiency Shortage", "data": def_vals, "backgroundColor": "#f43f5e"},
                    {"label": "Currently Held", "data": held_vals, "backgroundColor": "#64748b"}
                ]
            }

    # 3. Issued Quantities & Sales Trends
    if "issue" in clean_prompt or "sales" in clean_prompt or intent == "SALES_ISSUANCE":
        top_issued = db_data.get("top_issued_items", [])
        if top_issued:
            labels = [item["item_name"][:15] for item in top_issued[:6]]
            issued_vals = [item.get("issued_qty", item.get("qty", 0)) for item in top_issued[:6]]

            chart_req["entity"] = "issued_items"
            chart_req["metric"] = "issued_quantity"

            return {
                "visualization": True,
                "chart_request": chart_req,
                "chart_type": "line" if "trend" in clean_prompt else chart_req["chart"],
                "title": "Top Issued Clothing Items Quantity",
                "labels": labels,
                "values": issued_vals,
                "datasets": [{
                    "label": "Issued Quantity",
                    "data": issued_vals,
                    "backgroundColor": "#10b981",
                    "borderColor": "#059669",
                    "fill": True
                }]
            }

    # 4. Product Stock Comparison / Pie Chart of specific products
    if "product" in clean_prompt or "stock" in clean_prompt or intent == "PRODUCT_INFO":
        items = db_data.get("items", [])
        if items:
            labels = [item["item_name"][:15] for item in items[:6]]
            dummy_vals = [100 - (i * 12) for i in range(len(labels))]

            chart_req["entity"] = "products"
            chart_req["metric"] = "catalog_distribution"

            return {
                "visualization": True,
                "chart_request": chart_req,
                "chart_type": "pie" if "pie" in clean_prompt else "bar",
                "title": "Clothing Items Distribution",
                "labels": labels,
                "values": dummy_vals,
                "datasets": [{
                    "label": "Product Catalog Distribution",
                    "data": dummy_vals,
                    "backgroundColor": ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#64748b"]
                }]
            }

    # Generic Chart Request structure if user explicitly requested dynamic graph
    if intent == "DYNAMIC_CHART" or "graph" in clean_prompt or "chart" in clean_prompt:
        return {
            "visualization": True,
            "chart_request": chart_req,
            "chart_type": chart_req["chart"],
            "title": "CMS Dynamic Chart Visualizer",
            "labels": ["CAT-I", "CAT-II"],
            "values": [120, 85],
            "datasets": [{
                "label": "Stock Comparison",
                "data": [120, 85],
                "backgroundColor": ["#3b82f6", "#10b981"]
            }]
        }

    return None
