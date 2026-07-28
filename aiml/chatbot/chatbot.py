import json
import ollama
from flask import Response, jsonify, stream_with_context

SYSTEM_PROMPT = (
    "You are an AI assistant for the Clothing Management System (CMS). "
    "Answer concisely in 2-4 short sentences max. "
    "Use markdown bullets only when listing. No preamble, no repetition, "
    "no restating the question."
)

FAST_RESPONSES = {
    "hi": "Hello! How can I assist you with the Clothing Management System (CMS) today?",
    "hello": "Hello! How can I help you with your Clothing Management System (CMS)?",
    "hey": "Hey there! How can I help you with the Clothing Management System today?",
    "hi hello": "Hello! How can I assist you with the Clothing Management System today?",
    "hi there": "Hello! How can I help you with the Clothing Management System?",
    "good morning": "Good morning! How can I assist you with the Clothing Management System today?",
    "good afternoon": "Good afternoon! How can I help you today?",
    "good evening": "Good evening! How can I assist you today?",
    "who are you": "I am your AI Assistant for the Clothing Management System (CMS), built to help you manage clothing items, unit demands, and inventory.",
    "what is cms": "CMS stands for Clothing Management System, designed to manage clothing demands, unit stock, and equipment tracking.",
    "what does cms stand for": "CMS stands for Clothing Management System.",
    "cms": "CMS stands for Clothing Management System.",
    "what can you do": "I can help answer questions about clothing inventory, unit strength, SCME equipment tracking, and system navigation.",
    "help": "Sure! Ask me anything about unit requests, clothing stock status, organisation hierarchy, or SCME equipment tracking.",
    "thanks": "You're welcome! Let me know if you need anything else.",
    "thank you": "You're very welcome! Happy to help.",
    "bye": "Goodbye! Have a great day ahead.",

    # --- FAQ QUICK RESPONSES ---
    "how to request items": "To request items: Navigate to your Dashboard ➔ Click 'Generate Request' ➔ Select Item, Quantity, Reason & Priority ➔ Click Submit.",
    "how to request items?": "To request items: Navigate to your Dashboard ➔ Click 'Generate Request' ➔ Select Item, Quantity, Reason & Priority ➔ Click Submit.",
    "how to request equipment": "To request items: Navigate to your Dashboard ➔ Click 'Generate Request' ➔ Select Item, Quantity, Reason & Priority ➔ Click Submit.",
    "who can create users": "Only ORD (super_admin) can create users (Division Admin, Brigade Admin, and Unit) along with their parent organisation nodes.",
    "who can create users?": "Only ORD (super_admin) can create users (Division Admin, Brigade Admin, and Unit) along with their parent organisation nodes.",
    "who can create user": "Only ORD (super_admin) can create users (Division Admin, Brigade Admin, and Unit) along with their parent organisation nodes.",
    "organization tree info": "The Organization Tree links ORD ➔ Division ➔ Brigade ➔ Unit nodes, displaying parent-child relationships and hierarchy strength.",
    "how does organization tree work": "The Organization Tree links ORD ➔ Division ➔ Brigade ➔ Unit nodes, displaying parent-child relationships and hierarchy strength.",
    "how does organization tree work?": "The Organization Tree links ORD ➔ Division ➔ Brigade ➔ Unit nodes, displaying parent-child relationships and hierarchy strength.",
    "what is scme tracking": "SCME manages clothing items, stock additions, issuing stock to divisions/units, and tracking monthly ECC stock statements.",
    "what is scme tracking?": "SCME manages clothing items, stock additions, issuing stock to divisions/units, and tracking monthly ECC stock statements.",
    "what is scme equipment tracking": "SCME manages clothing items, stock additions, issuing stock to divisions/units, and tracking monthly ECC stock statements.",
}


def chat(data):
    prompt = (data.get("prompt") or "").strip()

    if not prompt:
        return jsonify({"success": False, "message": "Prompt cannot be empty."}), 400

    clean_prompt = prompt.lower().strip(" .!?,")
    if clean_prompt in FAST_RESPONSES:
        quick_reply = FAST_RESPONSES[clean_prompt]

        @stream_with_context
        def generate_fast():
            yield f"data: {json.dumps({'token': quick_reply})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"

        return Response(
            generate_fast(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    @stream_with_context
    def generate():
        try:
            stream = ollama.chat(
                model="llama3.2:3b",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                stream=True,
                options={
                    "num_predict": 150,   # hard cap on output tokens
                    "temperature": 0.4,   # less rambling
                    "top_p": 0.9,
                    "num_ctx": 2048,      # smaller context = faster
                    "stop": ["\n\n\n"],
                },
            )

            for chunk in stream:
                token = chunk["message"]["content"]
                if token:
                    yield f"data: {json.dumps({'token': token})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # stops nginx from buffering
            "Connection": "keep-alive",
        },
    )