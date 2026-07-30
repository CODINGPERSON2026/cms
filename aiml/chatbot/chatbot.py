"""
Main Chatbot Orchestrator Module for CMS AI Business Assistant.
Integrates Intent Classifier, Conversation Memory, Business Logic,
Demand Prediction, Chart Generator, Ollama Summarization, and Structured Response Formatter.
"""

import json
import os
import ollama
from flask import Response, jsonify, stream_with_context
from dotenv import load_dotenv

from aiml.chatbot.intent_classifier import (
    classify_intent, INTENT_INVENTORY, INTENT_SALES, INTENT_ORDERS,
    INTENT_SUPPLIERS, INTENT_CUSTOMERS, INTENT_PRODUCTS,
    INTENT_DASHBOARD_INSIGHTS, INTENT_DEMAND_PREDICTION, INTENT_LOW_STOCK,
    INTENT_GENERAL
)
from aiml.chatbot.memory import ConversationMemory
from aiml.chatbot.business_logic import (
    query_low_stock_items, query_inventory_summary, query_sales_and_issues,
    query_item_requests, query_supplier_and_fod_info, query_customer_unit_stats,
    query_dashboard_insights
)
from aiml.chatbot.prediction import predict_demand
from aiml.chatbot.chart_generator import generate_chart_data
from aiml.chatbot.prompt import CMS_BUSINESS_SYSTEM_PROMPT, build_ollama_prompt
from aiml.chatbot.response_formatter import build_structured_response

load_dotenv()

CMS_REFUSAL_MESSAGE = (
    "I am a dedicated AI Business Assistant for the Clothing Management System (CMS).\n\n"
    "I can only assist with CMS inventory, stock tracking, sales trends, demand predictions, and system workflows."
)

FAST_RESPONSES = {
    # Greetings
    "hi": "Hello!\n\nI am your AI Business Assistant for the Clothing Management System (CMS).\n\nHow can I assist you today?\n- Check Low Stock Items\n- View Sales Trends\n- Demand Forecasts",
    "hello": "Hello!\n\nHow can I help you with your Clothing Management System (CMS) today?",
    "hey": "Hey there!\n\nHow can I assist you with CMS stock management or inventory insights today?",
    "hi hello": "Hello!\n\nHow can I assist you with the Clothing Management System today?",
    "hi there": "Hello!\n\nHow can I help you with the Clothing Management System?",
    "good morning": "Good morning!\n\nHow can I assist you with the Clothing Management System today?",
    "good afternoon": "Good afternoon!\n\nHow can I help you with CMS today?",
    "good evening": "Good evening!\n\nHow can I assist you with CMS today?",

    # Persona & Purpose
    "who are you": "I am your AI Business Assistant for the Clothing Management System (CMS).\n\nKey Capabilities:\n1. Analyze live inventory and stock deficiencies\n2. Track sales trends and item distributions\n3. Predict next month demand with ML models\n4. Deliver actionable restocking insights",
    "what is cms": "CMS stands for Clothing Management System—an enterprise platform built to manage clothing demands, unit stock levels, reserve inventory, and SCME equipment distributions.",
    "what does cms stand for": "CMS stands for Clothing Management System.",
    "cms": "CMS stands for Clothing Management System, managing clothing demands, stock tracking, and organization hierarchy.",
    "what can you do": "I can assist you with:\n1. Live Inventory Tracking (SER vs PWS stock)\n2. Low Stock Alerts & Deficiency Reports\n3. Sales Trend Analysis & Chart Visualizations\n4. Next Month Demand Predictions",
    "help": "I'm here to help with CMS!\n\nTry asking:\n- \"Which products are low in stock?\"\n- \"Show monthly sales\"\n- \"Predict next month's demand\"\n- \"Show inventory summary\"",
    "thanks": "You're welcome!\n\nLet me know if you need any more insights on the Clothing Management System.",
    "thank you": "You're very welcome!\n\nHappy to help with CMS business insights.",
    "bye": "Goodbye!\n\nHave a great day managing your CMS workflows.",

    # FAQ Responses
    "how to request items": "To request items:\n1. Navigate to your Dashboard\n2. Click \"Generate Request\"\n3. Select Item, Quantity, Reason & Priority\n4. Click Submit",
    "who can create users": "Only \"ORD\" (Super Admin) can create users (\"Division Admin\", \"Brigade Admin\", and \"Unit\") and configure organization hierarchy nodes.",
    "what is ser and pws": "Stock Conditions:\n1. \"SER\": Serviceable stock (fully operational)\n2. \"PWS\": Partially Working Stock (operational equipment needing maintenance)",
    "what is reserve stock": "Reserve stock (\"Res\") represents stock held at Division/DOU available to issue to subordinate units, split into \"Res SER\" and \"Res PWS\".",
}

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
    "admin", "super admin", "catalog", "user", "supplier", "sale", "predict"
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
    prompt = (data.get("prompt") or "").strip()
    session_id = data.get("session_id", "default_user")

    if not prompt:
        return jsonify({"success": False, "message": "Prompt cannot be empty."}), 400

    clean_prompt = prompt.lower().strip(" .!?,")

    # 1. Conversation Memory retrieval
    session_mem = ConversationMemory.get_session(session_id)

    # 2. Fast responses for greetings
    if clean_prompt in FAST_RESPONSES:
        reply_text = FAST_RESPONSES[clean_prompt]
        payload = build_structured_response(reply_text, INTENT_GENERAL)
        ConversationMemory.update_session(session_id, prompt, INTENT_GENERAL, reply_text)

        @stream_with_context
        def generate_fast():
            yield f"data: {json.dumps({'token': reply_text})}\n\n"
            yield f"data: {json.dumps({'done': True, 'payload': payload})}\n\n"

        return Response(generate_fast(), mimetype="text/event-stream")

    # 3. Off-topic rejection
    if is_offtopic(clean_prompt):
        payload = build_structured_response(CMS_REFUSAL_MESSAGE, INTENT_GENERAL)
        ConversationMemory.update_session(session_id, prompt, INTENT_GENERAL, CMS_REFUSAL_MESSAGE)

        @stream_with_context
        def generate_refusal():
            yield f"data: {json.dumps({'token': CMS_REFUSAL_MESSAGE})}\n\n"
            yield f"data: {json.dumps({'done': True, 'payload': payload})}\n\n"

        return Response(generate_refusal(), mimetype="text/event-stream")

    # 4. Intent Classification & Context Extraction
    intent = classify_intent(prompt, session_mem)
    item_filter = ConversationMemory.extract_contextual_filter(prompt, session_mem.get("last_filter"))

    # 5. Execute Business Database Queries or Predictions
    db_data = {}
    prediction_data = None
    structured_text = ""

    try:
        if intent == INTENT_LOW_STOCK:
            low_items = query_low_stock_items(item_filter)
            db_data = {"low_stock": low_items}
            if not low_items:
                structured_text = "I couldn't find any matching records in the database for low stock items."
            else:
                top_items_list = "\n".join([f"- Item \"{item['item_name']}\" (Unit: \"{item['unit_name']}\"): Held {item['held']} / Auth {item['auth']} (Deficiency: {item['deficiency']})" for item in low_items[:5]])
                structured_text = f"Found {len(low_items)} low stock items in CMS database.\n\nKey items below authorized limit:\n{top_items_list}"

        elif intent == INTENT_INVENTORY:
            db_data = query_inventory_summary()
            structured_text = (
                f"CMS Inventory Summary:\n\n"
                f"1. Total Catalog Items: {db_data.get('total_items_catalog', 0)}\n"
                f"2. Total Held Stock: {db_data.get('total_held_stock', 0)} units\n"
                f"3. Stock Condition: {db_data.get('total_serviceable_ser', 0)} \"SER\" (Serviceable) / {db_data.get('total_partially_working_pws', 0)} \"PWS\" (Partially Working)\n"
                f"4. Reserve Stock: {db_data.get('total_reserve_stock', 0)} units"
            )

        elif intent == INTENT_SALES:
            db_data = query_sales_and_issues(item_filter)
            top_sales = db_data.get("top_issued_items", [])
            top_items_str = "\n".join([f"- Item \"{i['item_name']}\": {i['qty']} units issued" for i in top_sales[:4]])
            structured_text = (
                f"Sales & Issuance Insights:\n\n"
                f"1. Total Transactions: {db_data.get('total_transactions', 0)}\n"
                f"2. Total Issued Stock: {db_data.get('total_issued_qty', 0)} units\n\n"
                f"Top Issued Products:\n{top_items_str or '- No transactions recorded yet.'}"
            )

        elif intent == INTENT_ORDERS:
            db_data = query_item_requests()
            structured_text = (
                f"Item Request Status Overview:\n\n"
                f"1. Pending Requests: {db_data.get('pending', 0)}\n"
                f"2. Approved Requests: {db_data.get('approved', 0)}\n"
                f"3. Rejected Requests: {db_data.get('rejected', 0)}"
            )

        elif intent == INTENT_SUPPLIERS:
            db_data = query_supplier_and_fod_info(item_filter)
            sources_str = "\n".join([f"- \"{s}\"" for s in db_data.get('suppliers_sources', [])])
            structured_text = (
                f"Supplier & FOD Stock Distribution:\n\n"
                f"1. Central Ordnance Depo Stock (COD): {db_data.get('depo_stock_qty', 0)} units\n"
                f"2. Local Purchase Stock (LP): {db_data.get('lp_stock_qty', 0)} units\n\n"
                f"Primary Supply Sources:\n{sources_str}"
            )

        elif intent == INTENT_CUSTOMERS:
            db_data = query_customer_unit_stats()
            structured_text = (
                f"Unit Customer Statistics:\n\n"
                f"1. Total Military Units Tracked: {db_data.get('units_count', 0)}\n"
                f"2. Total Posted Personnel: {db_data.get('total_posted_strength', 0)}\n"
                f"3. Total Authorized Strength: {db_data.get('total_auth_strength', 0)}"
            )

        elif intent == INTENT_DASHBOARD_INSIGHTS:
            db_data = query_dashboard_insights()
            takeaways = "\n".join([f"- {t}" for t in db_data.get("key_takeaways", [])])
            structured_text = (
                f"CMS Executive Insights:\n\n"
                f"Key Highlights:\n{takeaways}"
            )

        elif intent == INTENT_DEMAND_PREDICTION:
            prediction_data = predict_demand(item_filter)
            db_data = prediction_data
            recs = prediction_data.get("restock_recommended", [])
            rec_list = "\n".join([f"1. Item \"{r['item_name']}\" (Unit: \"{r['unit_name']}\") ➔ Restock +{r['recommended_quantity']} units ({r['reason']})" for r in recs[:4]])
            structured_text = (
                f"ML Demand Prediction Forecast:\n\n"
                f"Restocking Priorities:\n{rec_list or '- All items are currently well stocked.'}"
            )

    except Exception as e:
        print(f"Error executing business logic for intent {intent}: {e}")
        structured_text = "I couldn't find any matching records in the database."

    # 6. Generate Chart Metadata
    chart_metadata = generate_chart_data(intent, db_data, prompt)

    # 7. Synthesize Response with Ollama (or fallback structured text)
    model_name = os.getenv("MODEL_NAME", "llama3.2:latest")
    ollama_prompt = build_ollama_prompt(prompt, intent, db_data, prediction_data)

    payload = build_structured_response(
        response_text=structured_text,
        intent=intent,
        chart_metadata=chart_metadata,
        db_data=db_data,
        prompt=prompt
    )

    ConversationMemory.update_session(session_id, prompt, intent, structured_text, item_filter)

    @stream_with_context
    def generate():
        full_text = ""
        try:
            stream = ollama.chat(
                model=model_name,
                messages=[
                    {"role": "system", "content": CMS_BUSINESS_SYSTEM_PROMPT},
                    {"role": "user", "content": ollama_prompt},
                ],
                stream=True,
                options={
                    "num_predict": 250,
                    "temperature": 0.1,
                    "top_p": 0.7,
                    "repeat_penalty": 1.1,
                    "num_ctx": 2048,
                },
            )

            for chunk in stream:
                token = chunk.get("message", {}).get("content", "")
                if token:
                    full_text += token
                    yield f"data: {json.dumps({'token': token})}\n\n"

            # Update final payload text
            if full_text.strip():
                payload["response"] = full_text.strip()
                ConversationMemory.update_session(session_id, prompt, intent, full_text.strip(), item_filter)

            yield f"data: {json.dumps({'done': True, 'payload': payload})}\n\n"

        except Exception as e:
            # If Ollama is offline or streaming fails, return structured summary cleanly
            yield f"data: {json.dumps({'token': structured_text})}\n\n"
            yield f"data: {json.dumps({'done': True, 'payload': payload})}\n\n"

    return Response(generate(), mimetype="text/event-stream")