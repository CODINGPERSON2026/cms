"""
Abstract Base Formatter Strategy interface for CMS AI Assistant.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseResponseFormatter(ABC):
    """
    Abstract Strategy Interface for all 15 response formatters.
    """

    @abstractmethod
    def format(
        self,
        intent: str,
        db_data: Dict[str, Any],
        raw_text: str,
        prompt: str = ""
    ) -> Dict[str, Any]:
        """
        Formats response payload into structured metadata for the specific style.
        """
        pass
