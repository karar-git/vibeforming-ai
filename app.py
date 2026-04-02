import os
import uuid
import json
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from ai_features import ChatBot

app = Flask(__name__)
CORS(app)

# Database config - use PostgreSQL on Railway or SQLite locally
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///chat.db")
# Railway uses postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Keep ChatBot instances in memory (for conversation context with Gemini)
bot_instances: dict[str, ChatBot] = {}


# Database Models
class Chat(db.Model):
    __tablename__ = "chats"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(256), nullable=False, default="New Chat")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    messages = db.relationship(
        "Message",
        backref="chat",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(36), db.ForeignKey("chats.id"), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    search_queries = db.Column(db.Text, nullable=True)  # JSON array
    sources = db.Column(db.Text, nullable=True)  # JSON array
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Create tables
with app.app_context():
    db.create_all()


def get_bot(chat_id: str) -> ChatBot:
    """Get or create a ChatBot instance for a chat."""
    if chat_id not in bot_instances:
        bot_instances[chat_id] = ChatBot()

        # Rebuild conversation history from DB
        chat = Chat.query.get(chat_id)
        if chat:
            for msg in chat.messages:
                bot_instances[chat_id].add_to_history(msg.role, msg.content)

    return bot_instances[chat_id]


# API Routes


@app.route("/api/chats", methods=["GET"])
def get_chats():
    """Get all chats."""
    chats = Chat.query.order_by(Chat.updated_at.desc()).all()
    return jsonify(
        {
            "chats": [
                {
                    "id": c.id,
                    "title": c.title,
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat(),
                    "message_count": len(c.messages),
                }
                for c in chats
            ]
        }
    )


@app.route("/api/chats", methods=["POST"])
def create_chat():
    """Create a new chat."""
    chat = Chat()
    db.session.add(chat)
    db.session.commit()

    return jsonify(
        {"id": chat.id, "title": chat.title, "created_at": chat.created_at.isoformat()}
    )


@app.route("/api/chats/<chat_id>", methods=["GET"])
def get_chat(chat_id: str):
    """Get a chat with all messages."""
    chat = Chat.query.get(chat_id)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    return jsonify(
        {
            "id": chat.id,
            "title": chat.title,
            "created_at": chat.created_at.isoformat(),
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "search_queries": json.loads(m.search_queries)
                    if m.search_queries
                    else [],
                    "sources": json.loads(m.sources) if m.sources else [],
                    "created_at": m.created_at.isoformat(),
                }
                for m in chat.messages
            ],
        }
    )


@app.route("/api/chats/<chat_id>", methods=["DELETE"])
def delete_chat(chat_id: str):
    """Delete a chat."""
    chat = Chat.query.get(chat_id)
    if chat:
        db.session.delete(chat)
        db.session.commit()

        # Clean up bot instance
        if chat_id in bot_instances:
            del bot_instances[chat_id]

    return jsonify({"status": "ok"})


@app.route("/api/chats/<chat_id>/messages", methods=["POST"])
def send_message(chat_id: str):
    """Send a message and get a response."""
    payload = request.get_json(silent=True) or {}
    prompt = payload.get("prompt")
    new_preferred = payload.get("new_preferred", [])  # New preferred websites
    new_prohibited = payload.get("new_prohibited", [])  # New prohibited websites

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    # Get or create chat
    chat = Chat.query.get(chat_id)
    if not chat:
        chat = Chat(id=chat_id)
        db.session.add(chat)

    # Update title if first message
    if len(chat.messages) == 0:
        chat.title = prompt[:50] + ("..." if len(prompt) > 50 else "")

    # Save user message (store original prompt without preferences appended)
    user_msg = Message(chat_id=chat_id, role="user", content=prompt)
    db.session.add(user_msg)

    # Get bot response (pass new preferences to append to message)
    bot = get_bot(chat_id)
    result = bot.chat(
        prompt, new_preferred=new_preferred, new_prohibited=new_prohibited
    )

    # Save assistant message
    assistant_msg = Message(
        chat_id=chat_id,
        role="assistant",
        content=result["text"],
        search_queries=json.dumps(result["search_queries"])
        if result["search_queries"]
        else None,
        sources=json.dumps(result["sources"]) if result["sources"] else None,
    )
    db.session.add(assistant_msg)
    db.session.commit()

    return jsonify(
        {
            "user_message": {
                "id": user_msg.id,
                "role": "user",
                "content": prompt,
                "created_at": user_msg.created_at.isoformat(),
            },
            "assistant_message": {
                "id": assistant_msg.id,
                "role": "assistant",
                "content": result["text"],
                "search_queries": result["search_queries"],
                "sources": result["sources"],
                "created_at": assistant_msg.created_at.isoformat(),
            },
        }
    )


@app.route("/health")
@app.route("/")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
