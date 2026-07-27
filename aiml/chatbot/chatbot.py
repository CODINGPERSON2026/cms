import ollama
from flask import jsonify


def chat(request):
    try:
        data = request.get_json() or {}

        user_prompt = data.get("user_input", "").strip()

        if not user_prompt:
            return jsonify({
                "success": False,
                "message": "Prompt cannot be empty."
            }), 400

        response = ollama.chat(
            model="llama3.2",
            messages=[
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        )

        return jsonify({
            "success": True,
            "Promt": user_prompt,
            "response": response["message"]["content"]
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500