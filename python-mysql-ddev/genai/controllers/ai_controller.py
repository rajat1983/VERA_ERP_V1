from flask import render_template, request, jsonify
from genai.services.ai_service import get_ai_response
from db import get_db_connection

def chat_ui():
    return render_template("ai_chat.html")

def chat_api():
    user_input = request.json.get("message")
    ai_reply = get_ai_response(user_input)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO ai_chat_history (user_input, ai_response) VALUES (%s, %s)",
        (user_input, ai_reply)
    )
    conn.commit()

    return jsonify({"reply": ai_reply})

def chat_history():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM ai_chat_history ORDER BY id DESC")
    rows = cursor.fetchall()
    return jsonify(rows)
