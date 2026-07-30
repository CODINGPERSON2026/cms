from flask import Blueprint, request, jsonify
from extensions import csrf
import ollama
from aiml .chatbot.chatbot import chat
chatbot_bp = Blueprint("chatbot", __name__)
import os
from dotenv import load_dotenv

load_dotenv()
# Choose the default model
MODEL_NAME = os.getenv("MODEL_NAME")


@chatbot_bp.route("/chat", methods=["POST"])
@csrf.exempt
def chatbot():
     print("MODEL_NAME =", os.getenv("MODEL_NAME"))
     data = request.get_json() or {}
     return chat(data)