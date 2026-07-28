from flask import Blueprint, request, jsonify
from extensions import csrf
import ollama
from aiml .chatbot.chatbot import chat
chatbot_bp = Blueprint("chatbot", __name__)

# Choose the default model
MODEL_NAME = "llama3.2:3b"


@chatbot_bp.route("/chat", methods=["POST"])
@csrf.exempt
def chatbot():
     data = request.get_json() or {}
     return chat(data)