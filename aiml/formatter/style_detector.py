"""
Response Style Detection Layer for CMS AI Assistant.
Detects explicit style requests and prioritizes specific user formats.
"""

import re
from typing import Tuple, Optional

# Supported Styles
STYLE_NORMAL = "normal"
STYLE_BULLET = "bullet"
STYLE_TABLE = "table"
STYLE_CHART = "chart"
STYLE_DASHBOARD = "dashboard"
STYLE_REPORT = "report"
STYLE_SUMMARY = "summary"
STYLE_STEPS = "steps"
STYLE_JSON = "json"
STYLE_CSV = "csv"
STYLE_MARKDOWN = "markdown"
STYLE_HTML = "html"
STYLE_EMAIL = "email"
STYLE_PRESENTATION = "presentation"
STYLE_RECOMMENDATION = "recommendation"

STYLE_PATTERNS = [
    (STYLE_CSV, [r"export as csv", r"csv format", r"\bcsv\b"]),
    (STYLE_JSON, [r"return json", r"json format", r"\bjson\b"]),
    (STYLE_EMAIL, [r"write an email", r"email format", r"\bemail\b"]),
    (STYLE_PRESENTATION, [r"prepare presentation", r"presentation", r"slides", r"slide deck"]),
    (STYLE_TABLE, [r"in a table", r"tabular format", r"show as table", r"\btable\b"]),
    (STYLE_DASHBOARD, [r"show dashboard", r"dashboard cards", r"\bkpi\b"]),
    (STYLE_CHART, [r"chart", r"graph", r"visualize", r"plot", r"analytics"]),
    (STYLE_REPORT, [r"detailed report", r"full report", r"comprehensive report"]),
    (STYLE_SUMMARY, [r"executive summary", r"summarize", r"summary"]),
    (STYLE_STEPS, [r"explain step by step", r"step by step", r"\bsteps\b"]),
    (STYLE_RECOMMENDATION, [r"recommendation", r"recommendations", r"suggested action"]),
    (STYLE_HTML, [r"html format", r"\bhtml\b"]),
    (STYLE_MARKDOWN, [r"markdown format", r"\bmarkdown\b", r"\bmd\b"]),
    (STYLE_BULLET, [r"bullet points", r"bullets", r"key points", r"\blist\b"]),
]


def detect_response_style(prompt: str, intent: str = "general") -> Tuple[str, Optional[str]]:
    """
    Detect primary and secondary response style from prompt text.
    Priority Order:
    1. User explicitly requested format.
    2. Best format for intent/data.
    3. Default normal response.
    """
    clean_prompt = prompt.lower().strip()

    matches = []
    for style, patterns in STYLE_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, clean_prompt):
                matches.append(style)
                break

    if matches:
        primary = matches[0]
        secondary = matches[1] if len(matches) > 1 else None
        return primary, secondary

    # Intent-inferred fallbacks if user didn't specify explicit style
    if intent in ("sales", "sales_issuance", "category_comparison", "dynamic_chart"):
        return STYLE_CHART, None

    return STYLE_NORMAL, None
