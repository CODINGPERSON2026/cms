from flask import Blueprint, request, jsonify
from extensions import csrf
import ollama

chatbot_bp = Blueprint("chatbot", __name__)

# Choose the default model
MODEL_NAME = "llama3.2"


@chatbot_bp.route("/chat", methods=["POST"])
@csrf.exempt
def chat():
    try:
        data = request.get_json() or {}

        user_input = data.get("user_input", "").strip()

        if not user_input:
            return jsonify({
                "success": False,
                "message": "Prompt cannot be empty."
            }), 400

        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": user_input
                }
            ]
        )

        return jsonify({
            "success": True,
            "response": response["message"]["content"]
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500