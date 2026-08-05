"""
Main Chatbot Orchestrator Module for CMS AI Assistant.
Integrates Authorization, Intent Parser, Memory, Tool Router, Ollama Client, and Response Formatter.
"""

import json
import os
from flask import Response, jsonify, session, stream_with_context
from dotenv import load_dotenv

from aiml.chatbot.auth import is_role_authorized
from aiml.chatbot.memory import ConversationMemory
from aiml.chatbot.intent_parser import parse_intent_and_entities, INTENT_GREETING, INTENT_HELP
from aiml.chatbot.router import ToolRouter
from aiml.chatbot.ollama_client import OllamaClient
from aiml.chatbot.prompt import CMS_SYSTEM_PROMPT, build_ollama_prompt
from aiml.chatbot.response_formatter import build_structured_response

load_dotenv()

CMS_REFUSAL_MESSAGE = (
    "I am a dedicated AI Assistant for the Clothing Management System (CMS).\n\n"
    "I can only assist with CMS clothing inventory, stock tracking, unit deficiencies, categories (CAT-I vs CAT-II), authorizations, reports, and system workflows."
)

OFFTOPIC_PATTERNS = [
    "python code", "write a script", "write code", "recipe", "cook", "weather",
    "movie", "actor", "capital of", "who won", "football", "cricket", "joke",
    "tell me a story", "song", "lyrics", "president of", "math solve", "physics"
]

CMS_KEYWORDS = [
    "cms", "clothing", "management", "system", "inventory", "stock", "unit", "demand", "res", "ser", "pws",
    "auth", "defi", "deficiency", "reserve", "scme", "ord", "division", "brigade", "ecc", "equipment",
    "size", "dashboard", "hierarchy", "strength", "personnel", "item", "garment", "uniform", "boot",
    "jacket", "trouser", "beret", "badge", "issue", "request", "dou", "held", "total stock", "role",
    "admin", "super admin", "catalog", "user", "supplier", "sale", "cat-i", "cat-ii", "graph", "chart",
    "report", "summary", "availability", "helmet", "sweater"
]


def is_offtopic(clean_prompt: str) -> bool:
    """Check if query is off-topic."""
    if any(pat in clean_prompt for pat in OFFTOPIC_PATTERNS):
        return True
    words = clean_prompt.split()
    if len(words) >= 4:
        has_cms_kw = any(kw in clean_prompt for kw in CMS_KEYWORDS)
        if not has_cms_kw:
            return True
    return False


def chat(data: dict):
    """
    Main Flask API endpoint handler for /chatbot/chat.
    """
    user_role = session.get("role") or data.get("user_role") or "Guest"

    # Enforce role-based access check
    if not is_role_authorized(user_role):
        return jsonify({
            "success": False,
            "message": "Access denied. AI Assistant access is currently restricted to Super Admin and Admin roles."
        }), 403

    prompt = (data.get("prompt") or "").strip()
    session_id = data.get("session_id") or session.get("user_id") or "default_user"

    if not prompt:
        return jsonify({"success": False, "message": "Prompt cannot be empty."}), 400

    clean_prompt = prompt.lower().strip(" .!?,")

    # 1. Retrieve session memory
    session_mem = ConversationMemory.get_session(session_id)

    # 2. Check for Off-topic rejection
    if is_offtopic(clean_prompt):
        payload = build_structured_response(CMS_REFUSAL_MESSAGE, "GENERAL", prompt=prompt)
        ConversationMemory.update_session(session_id, prompt, "GENERAL", CMS_REFUSAL_MESSAGE)

        @stream_with_context
        def generate_refusal():
            yield f"data: {json.dumps({'token': CMS_REFUSAL_MESSAGE})}\n\n"
            yield f"data: {json.dumps({'done': True, 'payload': payload})}\n\n"

        return Response(generate_refusal(), mimetype="text/event-stream")

    # 3. Intent Detection & Entity Parameter Parsing with Memory Context
    intent, entities = parse_intent_and_entities(prompt, memory_context=session_mem)

    # 4. Dispatch natural language request through Tool Router
    tool_result = ToolRouter.route_and_execute(intent=intent, entities=entities, prompt=prompt)

    # Handle fast greeting / chat tool responses without waiting for Ollama model stream
    if intent in (INTENT_GREETING, INTENT_HELP) and tool_result.get("chat_response"):
        reply_text = tool_result["chat_response"]
        payload = build_structured_response(reply_text, intent, prompt=prompt)
        ConversationMemory.update_session(session_id, prompt, intent, reply_text)

        @stream_with_context
        def generate_fast():
            yield f"data: {json.dumps({'token': reply_text})}\n\n"
            yield f"data: {json.dumps({'done': True, 'payload': payload})}\n\n"

        return Response(generate_fast(), mimetype="text/event-stream")

    # 5. Extract query summary text & structured data
    db_data = tool_result.get("db_data", {})
    summary_text = tool_result.get("summary_text", "")
    chart_request = tool_result.get("chart_request")
    chart_metadata = tool_result.get("chart_metadata")

    # Build Ollama prompt payload
    ollama_user_prompt = build_ollama_prompt(
        user_query=prompt,
        intent=intent,
        db_context=db_data,
        chart_request=chart_request
    )

    # Build structured output payload
    payload = build_structured_response(
        response_text=summary_text,
        intent=intent,
        chart_metadata=chart_metadata,
        chart_request=chart_request,
        db_data=db_data,
        prompt=prompt
    )

    if tool_result.get("report_data"):
        payload["report_data"] = tool_result["report_data"]

    extracted_filter = entities.get("item_filter") or entities.get("category_filter") or entities.get("unit_filter")
    ConversationMemory.update_session(session_id, prompt, intent, summary_text, extracted_filter)

    # 6. Stream token response via Ollama Client (with fallback to summary_text)
    @stream_with_context
    def generate():
        full_text = ""
        try:
            tokens_generator = OllamaClient.generate_stream(
                system_prompt=CMS_SYSTEM_PROMPT,
                user_prompt=ollama_user_prompt,
                temperature=0.1
            )

            for token in tokens_generator:
                if token:
                    full_text += token
                    yield f"data: {json.dumps({'token': token})}\n\n"

            if full_text.strip():
                payload["response"] = full_text.strip()
                ConversationMemory.update_session(session_id, prompt, intent, full_text.strip(), extracted_filter)

            yield f"data: {json.dumps({'done': True, 'payload': payload})}\n\n"

        except Exception as e:
            # Fallback if Ollama model is offline or streaming encounters an error
            print(f"Ollama stream notice: {e}. Yielding structured tool summary fallback.")
            yield f"data: {json.dumps({'token': summary_text})}\n\n"
            yield f"data: {json.dumps({'done': True, 'payload': payload})}\n\n"

    return Response(generate(), mimetype="text/event-stream")