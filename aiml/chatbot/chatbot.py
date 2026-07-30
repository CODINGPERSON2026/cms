import json
import ollama
from flask import Response, jsonify, stream_with_context

# --- SYSTEM PROMPT EXCLUSIVELY FOR CLOTHING MANAGEMENT SYSTEM (CMS) ---
SYSTEM_PROMPT = (
    "You are an AI Assistant EXCLUSIVELY dedicated to the Clothing Management System (CMS).\n"
    "STRICT BOUNDARY INSTRUCTIONS:\n"
    "- You MUST ONLY answer questions, provide insights, and assist with topics related to the Clothing Management System (CMS).\n"
    "- If a user asks a general knowledge, non-CMS, off-topic, or unrelated question (such as general programming, weather, sports, recipes, history, movies, jokes, etc.), you MUST politely decline with: 'I am a dedicated AI Assistant for the Clothing Management System (CMS). I can only assist with CMS project-related queries, inventory insights, stock tracking, and system workflows.'\n"
    "- Do not fulfill off-topic requests under any circumstances.\n\n"
    "CMS DOMAIN KNOWLEDGE & INSIGHTS:\n"
    "1. **Core Purpose**: CMS manages clothing items, unit demands, stock tracking, and SCME equipment distributions across military hierarchy.\n"
    "2. **Hierarchy & User Roles**:\n"
    "   - **ORD (Super Admin)**: Manages organization tree (ORD ➔ Division ➔ Brigade ➔ Unit), creates users, and views top-level analytics.\n"
    "   - **Division Admin**: Oversees subordinate units, manages Reserve Stock (Res SER & Res PWS), issues items to subordinate units, and tracks Total Stock Held.\n"
    "   - **Brigade Admin**: Monitors brigade-level unit strengths and inventory status.\n"
    "   - **Unit Dashboard**: Displays unit equipment inventory, personnel strength, deficiency, and generates item requests.\n"
    "   - **SCME**: Handles catalog items, stock additions, issuing stock to divisions/units, and monthly ECC stock statements.\n"
    "3. **Stock Terminology**:\n"
    "   - **AUTH**: Authorized limit for an item/unit.\n"
    "   - **Res (Reserve Stock)**: Available stock at DOU/Division, split into Res SER (Serviceable) and Res PWS (Partially Working).\n"
    "   - **Stock Held**: Current held/issued inventory, split into SER and PWS.\n"
    "   - **Total Stock**: Sum of Reserve (SER + PWS) and Stock Held (SER + PWS).\n"
    "   - **Deficiency (DEFI)**: Calculated as AUTH minus Stock Held.\n\n"
    "RESPONSE RULES:\n"
    "- Answer concisely in 2-4 short sentences max.\n"
    "- Use markdown formatting and bullet points for clarity.\n"
    "- Be professional, direct, helpful, and insightful on all CMS queries."
)

FAST_RESPONSES = {
    # Greetings
    "hi": "Hello! I am your dedicated AI Assistant for the Clothing Management System (CMS). How can I assist you with CMS inventory, stock tracking, or unit requests today?",
    "hello": "Hello! How can I help you with your Clothing Management System (CMS) today?",
    "hey": "Hey there! How can I assist you with CMS stock management or unit insights today?",
    "hi hello": "Hello! How can I assist you with the Clothing Management System today?",
    "hi there": "Hello! How can I help you with the Clothing Management System?",
    "good morning": "Good morning! How can I assist you with the Clothing Management System today?",
    "good afternoon": "Good afternoon! How can I help you with CMS today?",
    "good evening": "Good evening! How can I assist you with CMS today?",

    # Persona & Purpose
    "who are you": "I am your dedicated AI Assistant for the Clothing Management System (CMS), built to help you manage clothing items, unit demands, stock tracking, and inventory insights.",
    "what is cms": "CMS stands for Clothing Management System—an enterprise platform built to manage clothing demands, unit stock levels, reserve inventory, and SCME equipment distributions.",
    "what does cms stand for": "CMS stands for Clothing Management System.",
    "cms": "CMS stands for Clothing Management System, managing clothing demands, stock tracking, and organization hierarchy.",
    "what can you do": "I provide insights and help you navigate CMS functions, including item requests, division reserve stock tracking (Res SER/PWS), unit equipment status, and SCME operations.",
    "help": "I'm here to help with CMS! Ask me about generating item requests, division reserve stock, unit strength updates, organization hierarchy, or SCME tracking.",
    "thanks": "You're welcome! Let me know if you need any more insights on the Clothing Management System.",
    "thank you": "You're very welcome! Happy to help with CMS.",
    "bye": "Goodbye! Have a great day managing your CMS workflows.",

    # FAQ Responses
    "how to request items": "To request items: Navigate to your Dashboard ➔ Click 'Generate Request' ➔ Select Item, Quantity, Reason & Priority ➔ Click Submit.",
    "how to request items?": "To request items: Navigate to your Dashboard ➔ Click 'Generate Request' ➔ Select Item, Quantity, Reason & Priority ➔ Click Submit.",
    "how to request equipment": "To request items: Navigate to your Dashboard ➔ Click 'Generate Request' ➔ Select Item, Quantity, Reason & Priority ➔ Click Submit.",
    "who can create users": "Only ORD (Super Admin) can create users (Division Admin, Brigade Admin, and Unit) and configure organization hierarchy nodes.",
    "who can create users?": "Only ORD (Super Admin) can create users (Division Admin, Brigade Admin, and Unit) and configure organization hierarchy nodes.",
    "organization tree info": "The Organization Tree maps the military structure (ORD ➔ Division ➔ Brigade ➔ Unit), displaying parent-child relationships and posted personnel strength.",
    "what is scme tracking": "SCME manages clothing items, stock additions, issuing stock to divisions/units, and tracking monthly ECC stock statements.",
    "what is ser and pws": "SER stands for Serviceable stock (fully operational), while PWS stands for Partially Working Stock (partially operational equipment needing repair or maintenance).",
    "what is reserve stock": "Reserve stock (Res) represents stock held at Division/DOU available to issue to subordinate units, split into Res SER and Res PWS.",
}

# Common off-topic triggers to reject instantly
OFFTOPIC_KEYWORDS = [
    "python code", "write a code", "write a script", "recipe", "cook", "weather",
    "movie", "film", "capital of", "who won", "football", "cricket", "joke",
    "tell me a story", "song", "lyrics", "president of", "prime minister"
]


def chat(data):
    prompt = (data.get("prompt") or "").strip()

    if not prompt:
        return jsonify({"success": False, "message": "Prompt cannot be empty."}), 400

    clean_prompt = prompt.lower().strip(" .!?,")

    # 1. Fast match for common greetings and FAQs
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

    # 2. Fast rejection for obvious off-topic prompts
    if any(kw in clean_prompt for kw in OFFTOPIC_KEYWORDS):
        offtopic_reply = "I am a dedicated AI Assistant for the Clothing Management System (CMS). I can only assist with CMS project-related queries, inventory insights, stock tracking, and system workflows."

        @stream_with_context
        def generate_offtopic():
            yield f"data: {json.dumps({'token': offtopic_reply})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"

        return Response(
            generate_offtopic(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    # 3. Stream from Ollama with strict CMS domain system prompt
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
                    "num_predict": 180,   # hard cap on output tokens
                    "temperature": 0.3,   # low temperature for focused domain responses
                    "top_p": 0.85,
                    "num_ctx": 2048,
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
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )