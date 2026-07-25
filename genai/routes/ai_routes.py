from flask import Blueprint
from genai.controllers.ai_controller import chat_ui, chat_api, chat_history

ai_bp = Blueprint(
    "ai",
    __name__,
    url_prefix="/genai",
    template_folder="../templates",
    static_folder="../static"
)

ai_bp.route("/", methods=["GET"])(chat_ui)
ai_bp.route("/chat", methods=["POST"])(chat_api)
ai_bp.route("/history", methods=["GET"])(chat_history)
