"""
Router Module for CMS AI Assistant.
Routes natural language requests internally using QueryRouter and LangChain Database Agent.
"""

from typing import Dict, Any
from aiml.chatbot.query_router import QueryRouter


class ToolRouter:
    """Dispatches user request parameters internally to the appropriate tool combination."""

    @staticmethod
    def route_and_execute(
        intent: str,
        entities: Dict[str, Any],
        prompt: str
    ) -> Dict[str, Any]:
        """
        Executes internal tool workflow via QueryRouter.
        """
        return QueryRouter.route_query(intent=intent, entities=entities, prompt=prompt)
