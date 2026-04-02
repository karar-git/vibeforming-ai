import uuid
from flask import Flask, jsonify, request, render_template
from ai_features import ChatBot

app = Flask(__name__)

# Store sessions in memory (for demo - sessions reset on server restart)
sessions: dict[str, ChatBot] = {}


def get_or_create_session(session_id: str = None) -> tuple[str, ChatBot]:
    """Get existing session or create a new one."""
    if session_id and session_id in sessions:
        return session_id, sessions[session_id]

    new_id = str(uuid.uuid4())
    sessions[new_id] = ChatBot()
    return new_id, sessions[new_id]


@app.route("/")
def index():
    """Serve the chat UI."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """Send a message and get a response."""
    payload = request.get_json(silent=True) or {}
    prompt = payload.get("prompt")
    session_id = payload.get("session_id")

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    session_id, bot = get_or_create_session(session_id)
    result = bot.chat(prompt)

    return jsonify(
        {
            "session_id": session_id,
            "response": result["text"],
            "search_queries": result["search_queries"],
            "sources": result["sources"],
        }
    )


@app.route("/api/session/new", methods=["POST"])
def new_session():
    """Create a new chat session."""
    session_id, _ = get_or_create_session()
    return jsonify({"session_id": session_id})


@app.route("/api/session/<session_id>/history", methods=["GET"])
def get_history(session_id: str):
    """Get chat history for a session."""
    if session_id not in sessions:
        return jsonify({"error": "session not found"}), 404

    return jsonify(
        {"session_id": session_id, "messages": sessions[session_id].get_history()}
    )


@app.route("/api/session/<session_id>", methods=["DELETE"])
def delete_session(session_id: str):
    """Delete a chat session."""
    if session_id in sessions:
        del sessions[session_id]
    return jsonify({"status": "ok"})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True)
