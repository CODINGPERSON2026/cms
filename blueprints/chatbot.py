import os
from flask import Blueprint, request, jsonify
from extensions import csrf
from dotenv import load_dotenv
from aiml.chatbot.chatbot import chat
from aiml.chatbot.auth import require_chatbot_access

load_dotenv()

chatbot_bp = Blueprint("chatbot", __name__)


@chatbot_bp.route("/chat", methods=["POST"])
@csrf.exempt
@require_chatbot_access
def chatbot():
    data = request.get_json() or {}
    return chat(data)