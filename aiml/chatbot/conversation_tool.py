"""
Conversation Tool Module for CMS AI Assistant.
Handles conversational responses, greetings, capabilities, help guides, and FAQ responses.
"""

from typing import Dict, Any

FAST_RESPONSES = {
    "hi": "Hello!\n\nI am your AI Assistant for the Clothing Management System (CMS).\n\nHow can I help you today?\n- View Inventory Summary\n- Compare CAT-I & CAT-II Categories\n- Check Unit Deficiencies\n- Generate Dynamic Charts",
    "hello": "Hello!\n\nHow can I assist you with your Clothing Management System (CMS) inventory today?",
    "hey": "Hey there!\n\nHow can I help you with CMS stock levels, unit deficiencies, or item distributions today?",
    "good morning": "Good morning!\n\nHow can I assist you with the Clothing Management System today?",
    "good afternoon": "Good afternoon!\n\nHow can I help you with CMS inventory today?",
    "good evening": "Good evening!\n\nHow can I assist you with CMS today?",
    "help": "I am here to assist with CMS Inventory!\n\nTry asking:\n- \"How many Jackets are available?\"\n- \"Show CAT-II products\"\n- \"Which Unit has highest deficiency?\"\n- \"Generate graph between CAT-I and CAT-II\"\n- \"Show monthly issued quantity\"\n- \"List logged in users\"",
    "who are you": "I am the AI Assistant for the Clothing Management System (CMS).\n\nKey Capabilities:\n1. Query live inventory, SER/PWS stock, and unit deficiencies\n2. Provide CAT-I vs CAT-II category distribution\n3. Generate dynamic Chart.js structured visualizations\n4. Format executive reports and summaries",
}


class ChatTool:
    """Handles conversational turns, greetings, help commands, and general CMS FAQs."""

    @staticmethod
    def execute(prompt: str) -> Dict[str, Any]:
        clean_prompt = prompt.lower().strip(" .!?,")
        reply = FAST_RESPONSES.get(clean_prompt)
        if not reply:
            reply = "Hello! I am your CMS AI Assistant. How can I help you with clothing stock, units, or charts today?"
        return {
            "tool": "ChatTool",
            "response": reply,
            "data": {}
        }
