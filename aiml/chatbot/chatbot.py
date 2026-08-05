"""
Main Chatbot Orchestrator Module for CMS AI Assistant.
Integrates Authorization, Intent Parser, Memory, Tool Router, Ollama Client,
Plotly Visualization Generator, and Selection Menus (Graph, Analytics, Export).
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
from aiml.chatbot.chart_generator import (
    is_menu_trigger_request,
    build_selection_menu_payload,
    resolve_menu_choice,
    transform_dataset,
    generate_advanced_chart_spec
)

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
    "report", "summary", "availability", "helmet", "sweater", "table", "bar", "pie", "line", "export",
    "excel", "pdf", "analytics", "analysis", "1", "2", "3", "4"
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
    Handles interactive selection menus (Graph, Analytics, Export), option choices (1, 2, 3, 4),
    Plotly graph generation from session memory, and SSE token streaming.
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
    cached_dataset = ConversationMemory.get_dataset(session_id)

    # 2. Check for Off-topic rejection
    if is_offtopic(clean_prompt) and not is_menu_trigger_request(prompt) and not cached_dataset.get("pending_menu"):
        payload = build_structured_response(CMS_REFUSAL_MESSAGE, "GENERAL", prompt=prompt)
        ConversationMemory.update_session(session_id, prompt, "GENERAL", CMS_REFUSAL_MESSAGE)

        @stream_with_context
        def generate_refusal():
            yield f"data: {json.dumps({'token': CMS_REFUSAL_MESSAGE})}\n\n"
            yield f"data: {json.dumps({'done': True, 'payload': payload})}\n\n"

        return Response(generate_refusal(), mimetype="text/event-stream")

    # 3. FAST PATH A: User asks for Selection Menu ("Show graph", "Show analytics", "Export data")
    if cached_dataset and cached_dataset.get("records"):
        menu_trigger = is_menu_trigger_request(prompt)
        if menu_trigger:
            ConversationMemory.set_pending_menu(session_id, menu_trigger)
            menu_payload = build_selection_menu_payload(menu_trigger)

            payload = build_structured_response(
                response_text=menu_payload["text"],
                intent="DYNAMIC_CHART",
                prompt=prompt
            )
            payload["menu_choices"] = menu_payload["choices"]
            payload["pending_menu"] = menu_trigger

            reply_text = menu_payload["text"]

            @stream_with_context
            def generate_menu_fast():
                yield f"data: {json.dumps({'token': reply_text})}\n\n"
                yield f"data: {json.dumps({'done': True, 'payload': payload})}\n\n"

            return Response(generate_menu_fast(), mimetype="text/event-stream")

    # 4. FAST PATH B: User selects an Option ("1", "2", "3", "4", "Bar Chart", "Top 10", "Excel", etc.)
    if cached_dataset and cached_dataset.get("records"):
        pending_menu = ConversationMemory.get_pending_menu(session_id)
        action_kind, choice_val = resolve_menu_choice(prompt, pending_menu)

        if action_kind in ("graph", "analytics", "export"):
            records = cached_dataset["records"]
            columns = cached_dataset.get("columns") or list(records[0].keys())
            user_q = cached_dataset.get("user_question") or "CMS Inventory Data"

            ConversationMemory.clear_pending_menu(session_id)

            if action_kind == "graph":
                chart_metadata = generate_advanced_chart_spec(
                    chart_type=choice_val,
                    records=records,
                    columns=columns,
                    title=f"CMS Graph ({user_q})"
                )
                ConversationMemory.store_dataset(
                    session_id=session_id,
                    records=records,
                    chart_type=choice_val,
                    chart_data=chart_metadata
                )

                reply_text = f"Rendered **{choice_val.replace('_', ' ').title()}** visualization using cached dataset."
                payload = build_structured_response(
                    response_text=reply_text,
                    intent="DYNAMIC_CHART",
                    chart_metadata=chart_metadata,
                    db_data={"records": records, "columns": columns},
                    prompt=prompt
                )
                payload["actions"] = ["Open in New Tab"]

                @stream_with_context
                def generate_graph_fast():
                    yield f"data: {json.dumps({'token': reply_text})}\n\n"
                    yield f"data: {json.dumps({'done': True, 'payload': payload})}\n\n"

                return Response(generate_graph_fast(), mimetype="text/event-stream")

            elif action_kind == "analytics":
                transformed_records, text_note = transform_dataset(records, choice_val)
                chart_metadata = generate_advanced_chart_spec(
                    chart_type="bar",
                    records=transformed_records,
                    columns=columns,
                    title=f"CMS Analytics ({user_q})"
                )
                ConversationMemory.store_dataset(
                    session_id=session_id,
                    records=transformed_records,
                    aggregation=choice_val,
                    chart_data=chart_metadata
                )

                reply_text = text_note or f"Generated **{choice_val.title()}** analysis using cached dataset."
                payload = build_structured_response(
                    response_text=reply_text,
                    intent="DYNAMIC_CHART",
                    chart_metadata=chart_metadata,
                    db_data={"records": transformed_records, "columns": columns},
                    prompt=prompt
                )
                payload["table_data"] = transformed_records

                @stream_with_context
                def generate_ana_fast():
                    yield f"data: {json.dumps({'token': reply_text})}\n\n"
                    yield f"data: {json.dumps({'done': True, 'payload': payload})}\n\n"

                return Response(generate_ana_fast(), mimetype="text/event-stream")

            elif action_kind == "export":
                fmt = choice_val if choice_val in ["excel", "pdf", "csv"] else "excel"
                reply_text = f"Generated **{fmt.upper()}** export payload. Click below to download file."
                payload = build_structured_response(
                    response_text=reply_text,
                    intent="DYNAMIC_CHART",
                    prompt=prompt
                )
                payload["export_url"] = f"/chatbot/export-data?session_id={session_id}&format={fmt}"
                payload["export_format"] = fmt

                @stream_with_context
                def generate_exp_fast():
                    yield f"data: {json.dumps({'token': reply_text})}\n\n"
                    yield f"data: {json.dumps({'done': True, 'payload': payload})}\n\n"

                return Response(generate_exp_fast(), mimetype="text/event-stream")

    # 5. Intent Detection & Entity Parameter Parsing with Memory Context
    intent, entities = parse_intent_and_entities(prompt, memory_context=session_mem)

    # 6. Dispatch natural language request through Tool Router
    tool_result = ToolRouter.route_and_execute(intent=intent, entities=entities, prompt=prompt)

    # Handle fast greeting / chat tool responses
    if intent in (INTENT_GREETING, INTENT_HELP) and tool_result.get("chat_response"):
        reply_text = tool_result["chat_response"]
        payload = build_structured_response(reply_text, intent, prompt=prompt)
        ConversationMemory.update_session(session_id, prompt, intent, reply_text)

        @stream_with_context
        def generate_fast():
            yield f"data: {json.dumps({'token': reply_text})}\n\n"
            yield f"data: {json.dumps({'done': True, 'payload': payload})}\n\n"

        return Response(generate_fast(), mimetype="text/event-stream")

    # 7. Extract query summary text & structured data
    db_data = tool_result.get("db_data", {})
    summary_text = tool_result.get("summary_text", "")

    records = []
    if isinstance(db_data, dict):
        if "records" in db_data and isinstance(db_data["records"], list):
            records = db_data["records"]
        elif "low_stock" in db_data:
            records = db_data["low_stock"]
        elif "top_issued_items" in db_data:
            records = db_data["top_issued_items"]
        elif "top_deficiencies" in db_data:
            records = db_data["top_deficiencies"]
    elif isinstance(db_data, list):
        records = db_data

    columns = []
    if records and len(records) > 0 and isinstance(records[0], dict):
        columns = list(records[0].keys())

    # Cache dataset in session memory (DO NOT automatically generate chart or action buttons)
    if records:
        ConversationMemory.store_dataset(
            session_id=session_id,
            records=records,
            columns=columns,
            sql_query=db_data.get("sql_query"),
            user_question=prompt,
            summary_text=summary_text,
            pending_menu=None
        )

    # Build Ollama prompt payload
    ollama_user_prompt = build_ollama_prompt(
        user_query=prompt,
        intent=intent,
        db_context=db_data,
        chart_request=tool_result.get("chart_request")
    )

    # Build structured output payload (Initial DB response: text and table data only, no auto buttons/charts)
    payload = build_structured_response(
        response_text=summary_text,
        intent=intent,
        chart_metadata=None,
        db_data=db_data,
        prompt=prompt
    )

    if records:
        payload["table_data"] = records

    if tool_result.get("report_data"):
        payload["report_data"] = tool_result["report_data"]

    extracted_filter = entities.get("item_filter") or entities.get("category_filter") or entities.get("unit_filter")
    ConversationMemory.update_session(session_id, prompt, intent, summary_text, extracted_filter)

    # 8. Stream token response via Ollama Client (with fallback to summary_text)
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