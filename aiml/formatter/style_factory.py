"""
Style Factory Module for CMS AI Assistant Adaptive Response Styles.
Uses Factory Pattern to instantiate the corresponding response strategy.
"""

from typing import Dict, Type
from aiml.formatter.base_formatter import BaseResponseFormatter
from aiml.formatter.normal_formatter import NormalResponseFormatter
from aiml.formatter.bullet_formatter import BulletResponseFormatter
from aiml.formatter.table_formatter import TableResponseFormatter
from aiml.formatter.chart_formatter import ChartResponseFormatter
from aiml.formatter.dashboard_formatter import DashboardResponseFormatter
from aiml.formatter.report_formatter import ReportResponseFormatter
from aiml.formatter.summary_formatter import SummaryResponseFormatter
from aiml.formatter.steps_formatter import StepsResponseFormatter
from aiml.formatter.json_formatter import JsonResponseFormatter
from aiml.formatter.csv_formatter import CsvResponseFormatter
from aiml.formatter.markdown_formatter import MarkdownResponseFormatter
from aiml.formatter.html_formatter import HtmlResponseFormatter
from aiml.formatter.email_formatter import EmailResponseFormatter
from aiml.formatter.presentation_formatter import PresentationResponseFormatter
from aiml.formatter.recommendation_formatter import RecommendationResponseFormatter

# Registry mapping style names to strategy classes
FORMATTER_REGISTRY: Dict[str, Type[BaseResponseFormatter]] = {
    "normal": NormalResponseFormatter,
    "bullet": BulletResponseFormatter,
    "table": TableResponseFormatter,
    "chart": ChartResponseFormatter,
    "dashboard": DashboardResponseFormatter,
    "report": ReportResponseFormatter,
    "summary": SummaryResponseFormatter,
    "steps": StepsResponseFormatter,
    "json": JsonResponseFormatter,
    "csv": CsvResponseFormatter,
    "markdown": MarkdownResponseFormatter,
    "html": HtmlResponseFormatter,
    "email": EmailResponseFormatter,
    "presentation": PresentationResponseFormatter,
    "recommendation": RecommendationResponseFormatter,
}


class StyleFormatterFactory:
    """
    Factory pattern class to instantiate formatters dynamically.
    """

    @staticmethod
    def get_formatter(style: str) -> BaseResponseFormatter:
        """
        Get strategy formatter instance for the given style name.
        """
        formatter_cls = FORMATTER_REGISTRY.get(style.lower(), NormalResponseFormatter)
        return formatter_cls()
