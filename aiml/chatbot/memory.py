"""
Conversation Memory Module for CMS AI Assistant.
Tracks user session context, short-term turn history, and filters across turns.
"""

from typing import Dict, Any, List, Optional
import time

_MEMORY_STORE: Dict[str, Dict[str, Any]] = {}
MAX_SESSION_AGE_SECONDS = 3600  # 1 hour memory retention


class ConversationMemory:
    """Session-based memory store for AI assistant sessions."""

    @staticmethod
    def get_session(session_id: str = "default_user") -> Dict[str, Any]:
        """Retrieve memory context for a given session."""
        now = time.time()
        if session_id in _MEMORY_STORE:
            session = _MEMORY_STORE[session_id]
            if now - session.get("last_updated", 0) < MAX_SESSION_AGE_SECONDS:
                return session

        # Initialize fresh session context
        new_session = {
            "session_id": session_id,
            "turns": [],
            "last_intent": None,
            "last_query": None,
            "last_response": None,
            "last_filter": None,
            "last_sql_query": None,
            "last_dataframe": [],
            "last_columns": [],
            "last_filters": None,
            "last_chart_type": "bar",
            "last_chart_data": None,
            "last_aggregation": None,
            "last_user_question": None,
            "last_summary_text": None,
            "last_pending_menu": None,
            "last_updated": now,
        }
        _MEMORY_STORE[session_id] = new_session
        return new_session

    @staticmethod
    def update_session(
        session_id: str,
        user_prompt: str,
        intent: str,
        bot_response: str,
        extracted_filter: Optional[str] = None
    ):
        """Update session state with latest conversation turn."""
        session = ConversationMemory.get_session(session_id)
        session["turns"].append({
            "user": user_prompt,
            "bot": bot_response,
            "intent": intent,
            "timestamp": time.time()
        })
        # Retain last 5 turns
        if len(session["turns"]) > 5:
            session["turns"] = session["turns"][-5:]

        session["last_intent"] = intent
        session["last_query"] = user_prompt
        session["last_response"] = bot_response
        if extracted_filter:
            session["last_filter"] = extracted_filter
        session["last_updated"] = time.time()

    @staticmethod
    def store_dataset(
        session_id: str,
        records: List[Dict[str, Any]],
        columns: Optional[List[str]] = None,
        sql_query: Optional[str] = None,
        filters: Optional[Any] = None,
        chart_type: Optional[str] = None,
        chart_data: Optional[Dict[str, Any]] = None,
        user_question: Optional[str] = None,
        summary_text: Optional[str] = None,
        aggregation: Optional[str] = None,
        pending_menu: Optional[str] = None
    ):
        """Store structured dataset and chart metadata in session memory."""
        session = ConversationMemory.get_session(session_id)
        if records is not None:
            session["last_dataframe"] = records
        if columns is not None:
            session["last_columns"] = columns
        elif records and len(records) > 0 and isinstance(records[0], dict):
            session["last_columns"] = list(records[0].keys())
        
        if sql_query is not None:
            session["last_sql_query"] = sql_query
        if filters is not None:
            session["last_filters"] = filters
        if chart_type is not None:
            session["last_chart_type"] = chart_type
        if chart_data is not None:
            session["last_chart_data"] = chart_data
        if user_question is not None:
            session["last_user_question"] = user_question
        if summary_text is not None:
            session["last_summary_text"] = summary_text
        if aggregation is not None:
            session["last_aggregation"] = aggregation
        if pending_menu is not None:
            session["last_pending_menu"] = pending_menu

        session["last_updated"] = time.time()

    @staticmethod
    def set_pending_menu(session_id: str, menu_type: Optional[str]):
        """Set active pending menu type (GRAPH_MENU, ANALYTICS_MENU, EXPORT_MENU)."""
        session = ConversationMemory.get_session(session_id)
        session["last_pending_menu"] = menu_type
        session["last_updated"] = time.time()

    @staticmethod
    def get_pending_menu(session_id: str) -> Optional[str]:
        """Get active pending menu type."""
        session = ConversationMemory.get_session(session_id)
        return session.get("last_pending_menu")

    @staticmethod
    def clear_pending_menu(session_id: str):
        """Clear active pending menu state."""
        session = ConversationMemory.get_session(session_id)
        session["last_pending_menu"] = None

    @staticmethod
    def get_dataset(session_id: str) -> Dict[str, Any]:
        """Retrieve stored dataset and visualization context."""
        session = ConversationMemory.get_session(session_id)
        return {
            "records": session.get("last_dataframe", []),
            "columns": session.get("last_columns", []),
            "sql_query": session.get("last_sql_query"),
            "filters": session.get("last_filters"),
            "chart_type": session.get("last_chart_type", "bar"),
            "chart_data": session.get("last_chart_data"),
            "user_question": session.get("last_user_question"),
            "summary_text": session.get("last_summary_text"),
            "aggregation": session.get("last_aggregation"),
            "pending_menu": session.get("last_pending_menu")
        }

    @staticmethod
    def extract_contextual_filter(user_prompt: str, last_filter: Optional[str] = None) -> Optional[str]:
        """
        Extract item/category/unit filter from follow-up prompts.
        Example: "Only Jackets" -> returns "jacket"
        """
        clean = user_prompt.lower().strip()
        
        if "only " in clean:
            return clean.split("only ")[-1].strip(" .!?,")
        if "just " in clean:
            return clean.split("just ")[-1].strip(" .!?,")
        if "filter by " in clean:
            return clean.split("filter by ")[-1].strip(" .!?,")
        
        words = clean.split()
        if len(words) <= 4 and last_filter:
            return last_filter

        return last_filter
