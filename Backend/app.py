"""Flask application for Azure OpenAI Service integration."""

import os
import logging
from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, login_required
from opentelemetry import trace
from opentelemetry.trace import get_tracer_provider
from azure_open_ai_service import AzureOpenAIService
from models import ChatRequest, ChatbotMessage, db, Users


app = Flask(__name__)
bcrypt = Bcrypt(app)

tracer = trace.get_tracer(__name__, tracer_provider=get_tracer_provider())

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def loader_user(user_id):
    """Load user by ID for Flask-Login."""
    return Users.query.get(user_id)


with app.app_context():
    db.create_all()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Register services
ai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
assistant_id = os.getenv("ASSISTANT_ID")

openai_service = AzureOpenAIService(ai_endpoint, assistant_id)

@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    """Endpoint to handle chat requests."""
    try:
        data = request.get_json()

        # Convert history from list of dicts to list of ChatbotMessage objects
        if "history" in data:
            data["history"] = [ChatbotMessage(**message) for message in data["history"]]

        message = ChatRequest(**data)

        if not message:
            return jsonify({"error": "Message cannot be empty"}), 400

        response = openai_service.get_response(message)
        return jsonify(response), 200

    except Exception as ex:
        logger.error("Error processing chat request: %s", ex)
        return (
            jsonify({"error": "An error occurred while processing your request"}),
            500,
        )


# --- Authentication Endpoints ---
@app.route("/api/login", methods=["POST"])
def login():
    """Login user and return JWT token."""
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    user = Users.query.filter_by(username=username).first()
    if user and bcrypt.check_password_hash(user.password_hash, password):
        login_user(user)
        return jsonify({"success": True, "username": user.username}), 200
    return jsonify({"success": False, "error": "Invalid username or password"}), 401


@app.route("/api/create_account", methods=["POST"])
def create_account():
    """Create a new user account."""
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400
    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
    user = Users(username, hashed_password)
    try:
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return jsonify({"success": True, "username": user.username}), 201
    except Exception:
        return jsonify({"success": False, "error": "Username already exists"}), 409


if __name__ == "__main__":
    app.run()
