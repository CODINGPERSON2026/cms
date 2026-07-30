"""
Conversation Memory Module for CMS AI Business Assistant.
Tracks user session context, turn history, and filters across turns.
"""

from typing import Dict, Any, List, Optional
import time

_MEMORY_STORE: Dict[str, Dict[str, Any]] = {}
MAX_SESSION_AGE_SECONDS = 3600  # 1 hour memory retention


class ConversationMemory:
    """Session-based memory store for AI chatbot sessions."""

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
        # Keep max 10 turns
        if len(session["turns"]) > 10:
            session["turns"] = session["turns"][-10:]

        session["last_intent"] = intent
        session["last_query"] = user_prompt
        session["last_response"] = bot_response
        if extracted_filter:
            session["last_filter"] = extracted_filter
        session["last_updated"] = time.time()

    @staticmethod
    def extract_contextual_filter(user_prompt: str, last_filter: Optional[str] = None) -> Optional[str]:
        """
        Extract item/category/unit filter from follow-up prompts.
        Example: "Only shirts" -> returns "shirt"
        """
        clean = user_prompt.lower().strip()
        
        # Phrases like "only shirts", "just jacket", "show trousers"
        if "only " in clean:
            return clean.split("only ")[-1].strip(" .!?,")
        if "just " in clean:
            return clean.split("just ")[-1].strip(" .!?,")
        if "filter by " in clean:
            return clean.split("filter by ")[-1].strip(" .!?,")
        
        words = clean.split()
        if len(words) <= 3 and last_filter:
            return clean

        return last_filter
