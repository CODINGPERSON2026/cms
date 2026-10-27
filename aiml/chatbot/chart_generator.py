"""
Chart Generator & Data Analysis Module for CMS AI Business Assistant.
Supports Plotly visualizations, interactive selection menus (Graph, Analytics, Export),
and fast-path dataset transformations from session memory.
"""

import math
from typing import Dict, Any, List, Optional, Tuple


MENU_GRAPH_TRIGGERS = [
    "show graph", "graph", "chart", "visualization", "visualize", "draw graph", "draw chart"
]

MENU_ANALYTICS_TRIGGERS = [
    "show analytics", "analytics", "analysis", "show analysis", "analyze"
]

MENU_EXPORT_TRIGGERS = [
    "export data", "export the data", "export", "report", "download"
]


def is_menu_trigger_request(prompt: str) -> Optional[str]:
    """Check if prompt is asking for a graph/analytics/export selection menu."""
    clean = prompt.lower().strip()
    if clean in MENU_GRAPH_TRIGGERS or any(t == clean for t in MENU_GRAPH_TRIGGERS):
        return "GRAPH_MENU"
    if clean in MENU_ANALYTICS_TRIGGERS or any(t == clean for t in MENU_ANALYTICS_TRIGGERS):
        return "ANALYTICS_MENU"
    if clean in MENU_EXPORT_TRIGGERS or any(t == clean for t in MENU_EXPORT_TRIGGERS):
        return "EXPORT_MENU"
    return None


def build_selection_menu_payload(menu_type: str) -> Dict[str, Any]:
    """Constructs interactive selection menu prompt text and choice buttons."""
    if menu_type == "GRAPH_MENU":
        text = "Choose a graph type:\n\n📊 **Graph Options**\n1. Bar Chart (Recommended)\n2. Pie Chart\n3. Line Chart\n4. Horizontal Bar Chart"
        choices = [
            {"label": "1. Bar Chart", "val": "1"},
            {"label": "2. Pie Chart", "val": "2"},
            {"label": "3. Line Chart", "val": "3"},
            {"label": "4. Horizontal Bar Chart", "val": "4"}
        ]
    elif menu_type == "ANALYTICS_MENU":
        text = "Choose an analysis type:\n\n📈 **Analytics Options**\n1. Top 10 Items\n2. Category Comparison\n3. Trend Summary"
        choices = [
            {"label": "1. Top 10", "val": "1"},
            {"label": "2. Category Comparison", "val": "2"},
            {"label": "3. Trend Summary", "val": "3"}
        ]
    else:  # EXPORT_MENU
        text = "Choose an export format:\n\n📄 **Export Options**\n1. Excel (.xlsx)\n2. PDF Report"
        choices = [
            {"label": "1. Excel (.xlsx)", "val": "1"},
            {"label": "2. PDF Report", "val": "2"}
        ]

    return {
        "menu_type": menu_type,
        "text": text,
        "choices": choices
    }


def resolve_menu_choice(prompt: str, pending_menu: Optional[str] = None) -> Tuple[str, str]:
    """
    Resolves user selection prompt ("1", "2", "3", "4", "Bar Chart", "Top 10", "Excel", etc.)
    Returns tuple of (action_kind, resolved_choice).
    action_kind: "graph", "analytics", "export", or "unknown"
    """
    clean = prompt.lower().strip()

    # 1. Resolve numeric or direct choice under pending GRAPH_MENU
    if pending_menu == "GRAPH_MENU" or "graph" in clean or "chart" in clean or clean in ["1", "2", "3", "4"]:
        if clean in ["1", "bar", "bar chart", "1. bar chart"]:
            return "graph", "bar"
        if clean in ["2", "pie", "pie chart", "2. pie chart"]:
            return "graph", "pie"
        if clean in ["3", "line", "line chart", "3. line chart"]:
            return "graph", "line"
        if clean in ["4", "horizontal bar", "horizontal bar chart", "4. horizontal bar chart", "hbar"]:
            return "graph", "horizontal_bar"

    # 2. Resolve numeric or direct choice under pending ANALYTICS_MENU
    if pending_menu == "ANALYTICS_MENU" or "analytic" in clean or "compare" in clean or "top 10" in clean:
        if clean in ["1", "top 10", "top 10 items", "1. top 10"]:
            return "analytics", "top 10"
        if clean in ["2", "compare", "category comparison", "2. category comparison"]:
            return "analytics", "compare"
        if clean in ["3", "trend", "trend summary", "3. trend summary"]:
            return "analytics", "trends"

    # 3. Resolve numeric or direct choice under pending EXPORT_MENU
    if pending_menu == "EXPORT_MENU" or "excel" in clean or "pdf" in clean or "csv" in clean:
        if clean in ["1", "excel", "xlsx", "excel (.xlsx)", "1. excel"]:
            return "export", "excel"
        if clean in ["2", "pdf", "pdf report", "2. pdf report"]:
            return "export", "pdf"
        if clean in ["csv", "download csv"]:
            return "export", "csv"

    # Direct fallback matching
    if "bar" in clean:
        return "graph", "bar"
    if "pie" in clean:
        return "graph", "pie"
    if "line" in clean:
        return "graph", "line"
    if "horizontal bar" in clean:
        return "graph", "horizontal_bar"
    if "scatter" in clean:
        return "graph", "scatter"
    if "donut" in clean or "doughnut" in clean:
        return "graph", "donut"
    if "top 10" in clean:
        return "analytics", "top 10"
    if "compare" in clean:
        return "analytics", "compare"
    if "trend" in clean:
        return "analytics", "trends"
    if "excel" in clean:
        return "export", "excel"
    if "pdf" in clean:
        return "export", "pdf"

    return "unknown", clean


def transform_dataset(records: List[Dict[str, Any]], choice_key: str) -> Tuple[List[Dict[str, Any]], str]:
    """Applies analytics transformations on cached dataset."""
    if not records:
        return records, "No data available."

    numeric_col = None
    for k, v in records[0].items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            numeric_col = k
            break
        try:
            float(v)
            numeric_col = k
            break
        except (ValueError, TypeError):
            pass

    def get_num_val(row, col):
        try:
            return float(row.get(col, 0))
        except (ValueError, TypeError):
            return 0.0

    if choice_key == "top 10":
        if numeric_col:
            sorted_records = sorted(records, key=lambda r: get_num_val(r, numeric_col), reverse=True)
            return sorted_records[:10], f"Displaying **Top 10** items sorted by `{numeric_col}`."
        return records[:10], "Displaying Top 10 items."

    if choice_key == "compare":
        return records, "Showing **Category Comparison** analysis."

    if choice_key == "trends":
        return records, "Showing **Trend Summary** analysis."

    return records, ""


def generate_advanced_chart_spec(
    chart_type: str,
    records: List[Dict[str, Any]],
    columns: Optional[List[str]] = None,
    title: str = "CMS Data Visualization"
) -> Dict[str, Any]:
    """
    Builds professional Plotly specification JSON dictionary for frontend Plotly.js rendering.
    """
    if not isinstance(records, list) or not records:
        return {
            "visualization": True,
            "chart_type": chart_type if isinstance(chart_type, str) else "bar",
            "title": str(title),
            "labels": ["No Data"],
            "values": [0],
            "plotly_data": [],
            "plotly_layout": {}
        }

    if not isinstance(records[0], dict):
        return {
            "visualization": True,
            "chart_type": chart_type if isinstance(chart_type, str) else "bar",
            "title": str(title),
            "labels": [str(r) for r in records],
            "values": [1] * len(records),
            "plotly_data": [],
            "plotly_layout": {}
        }

    columns = columns or list(records[0].keys())

    label_col = columns[0]
    numeric_cols = []
    for c in columns[1:]:
        v = records[0].get(c)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            numeric_cols.append(c)
        else:
            try:
                float(v)
                numeric_cols.append(c)
            except (ValueError, TypeError):
                pass

    if not numeric_cols:
        for c in columns:
            try:
                float(records[0].get(c, 0))
                numeric_cols.append(c)
            except (ValueError, TypeError):
                label_col = c

    if not numeric_cols:
        numeric_cols = [columns[-1]]

    labels = [str(r.get(label_col, f"Item {i+1}"))[:22] for i, r in enumerate(records)]

    colors = [
        "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899",
        "#0ea5e9", "#14b8a6", "#6366f1", "#f43f5e", "#64748b"
    ]

    plotly_traces = []

    if chart_type in ["pie", "donut"]:
        vals = []
        for r in records:
            try:
                vals.append(float(r.get(numeric_cols[0], 0)))
            except (ValueError, TypeError):
                vals.append(0.0)

        plotly_traces.append({
            "type": "pie",
            "labels": labels,
            "values": vals,
            "hole": 0.45 if chart_type == "donut" else 0.0,
            "marker": {"colors": colors[:len(labels)]},
            "textinfo": "label+percent",
            "hoverinfo": "label+value+percent",
            "insidetextorientation": "radial"
        })

    elif chart_type == "horizontal_bar":
        for idx, num_col in enumerate(numeric_cols[:2]):
            vals = []
            for r in records:
                try:
                    vals.append(float(r.get(num_col, 0)))
                except (ValueError, TypeError):
                    vals.append(0.0)

            plotly_traces.append({
                "type": "bar",
                "orientation": "h",
                "y": labels,
                "x": vals,
                "name": str(num_col).replace("_", " ").title(),
                "marker": {"color": colors[idx % len(colors)], "cornerradius": 6}
            })

    elif chart_type == "line":
        for idx, num_col in enumerate(numeric_cols[:2]):
            vals = []
            for r in records:
                try:
                    vals.append(float(r.get(num_col, 0)))
                except (ValueError, TypeError):
                    vals.append(0.0)

            plotly_traces.append({
                "type": "scatter",
                "mode": "lines+markers",
                "x": labels,
                "y": vals,
                "name": str(num_col).replace("_", " ").title(),
                "line": {"color": colors[idx % len(colors)], "width": 3, "shape": "spline"},
                "marker": {"size": 7}
            })

    else:  # Standard Bar Chart
        for idx, num_col in enumerate(numeric_cols[:2]):
            vals = []
            for r in records:
                try:
                    vals.append(float(r.get(num_col, 0)))
                except (ValueError, TypeError):
                    vals.append(0.0)

            plotly_traces.append({
                "type": "bar",
                "x": labels,
                "y": vals,
                "name": str(num_col).replace("_", " ").title(),
                "marker": {
                    "color": colors[idx % len(colors)] if len(numeric_cols) > 1 else colors[:len(vals)],
                    "cornerradius": 6
                }
            })

    # Plotly Layout Object
    plotly_layout = {
        "title": {"text": title, "font": {"size": 15, "color": "#f8fafc", "family": "Segoe UI"}},
        "paper_bgcolor": "transparent",
        "plot_bgcolor": "transparent",
        "font": {"color": "#94a3b8", "family": "Segoe UI"},
        "margin": {"l": 50, "r": 30, "t": 40, "b": 50},
        "showlegend": len(plotly_traces) > 1 or chart_type in ["pie", "donut"],
        "hoverlabel": {"bgcolor": "#1e293b", "font": {"color": "#fff"}},
        "xaxis": {
            "gridcolor": "#334155",
            "tickangle": -20 if len(labels) > 6 else 0,
            "zeroline": False
        },
        "yaxis": {
            "gridcolor": "#334155",
            "zeroline": False
        }
    }

    primary_vals = plotly_traces[0].get("y") or plotly_traces[0].get("x") or plotly_traces[0].get("values") or []

    return {
        "visualization": True,
        "chart_type": chart_type,
        "title": title,
        "labels": labels,
        "values": primary_vals,
        "plotly_data": plotly_traces,
        "plotly_layout": plotly_layout,
        "records": records,
        "columns": columns
    }


def generate_chart_data(arg1: Any, arg2: Any = "bar", arg3: Any = "CMS Data Visualization") -> Dict[str, Any]:
    """
    Polymorphic chart data generator function supporting both:
    1. generate_chart_data(intent_str, db_data_dict, prompt_str) -> called by ChartResponseFormatter
    2. generate_chart_data(records_list, chart_type_str, title_str) -> called directly
    """
    records = []
    chart_type = "bar"
    title = "CMS Data Visualization"

    if isinstance(arg1, str):
        # Signature 1: (intent, db_data, prompt)
        intent = arg1
        db_data = arg2 if isinstance(arg2, (dict, list)) else {}
        prompt = arg3 if isinstance(arg3, str) else ""

        if isinstance(db_data, dict):
            records = db_data.get("records") or db_data.get("table_data") or db_data.get("unit_deficiencies") or db_data.get("top_deficiencies") or []
        elif isinstance(db_data, list):
            records = db_data

        chart_type = parse_chart_type_from_prompt(prompt) if prompt else "bar"
        title = prompt.strip().title() if prompt else f"CMS {intent.replace('_', ' ').title()} Visualization"
    else:
        # Signature 2: (records, chart_type, title)
        records = arg1 if isinstance(arg1, list) else []
        chart_type = arg2 if isinstance(arg2, str) else "bar"
        title = arg3 if isinstance(arg3, str) else "CMS Data Visualization"

    return generate_advanced_chart_spec(chart_type=chart_type, records=records, title=title)


def parse_chart_type_from_prompt(prompt: str) -> str:
    """Helper mapping prompt text to internal chart type key."""
    clean = prompt.lower().strip()
    if "horizontal" in clean or "hbar" in clean:
        return "horizontal_bar"
    if "pie" in clean:
        return "pie"
    if "donut" in clean or "doughnut" in clean:
        return "donut"
    if "line" in clean:
        return "line"
    return "bar"
