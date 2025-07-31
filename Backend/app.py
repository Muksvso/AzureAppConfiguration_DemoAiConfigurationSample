"""Flask application for Azure OpenAI Service integration."""

import os
import logging
import uuid
import random
from flask import request, jsonify, session
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user, login_user, login_required
from azure.identity import DefaultAzureCredential
from azure.appconfiguration.provider import load
from azure.monitor.opentelemetry import configure_azure_monitor
from featuremanagement import FeatureManager, TargetingContext
from featuremanagement.azuremonitor import track_event, publish_telemetry
from opentelemetry import trace
from opentelemetry.trace import get_tracer_provider
from azure_open_ai_service import AzureOpenAIService
from models import ChatRequest, ChatbotMessage, db, Users


configure_azure_monitor(connection_string=os.getenv("APPLICATION_INSIGHTS_CONNECTION_STRING"))

from flask import Flask

app = Flask(__name__)
app.secret_key = os.urandom(24)
bcrypt = Bcrypt(app)

tracer = trace.get_tracer(__name__, tracer_provider=get_tracer_provider())

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Global variables for configuration and feature management
CONFIG = None
FEATURE_MANAGER = None
OPENAI_SERVICE = None


def targeting_accessor():
    """Targeting accessor to identify users for feature flag targeting."""
    # Extract user information from request header
    return TargetingContext(user_id=session["user_id"])


def initialize_app_configuration():
    """Initialize Azure App Configuration and Feature Management."""
    global CONFIG, FEATURE_MANAGER, OPENAI_SERVICE

    try:
        # Get App Configuration endpoint from environment variable
        app_config_endpoint = os.getenv("AZURE_APPCONFIGURATION_ENDPOINT")
        if not app_config_endpoint:
            raise ValueError("AZURE_APPCONFIGURATION_ENDPOINT environment variable is required")

        # Load configuration with refresh enabled for feature flags
        CONFIG = load(
            endpoint=app_config_endpoint,
            credential=DefaultAzureCredential(),
            feature_flag_enabled=True,
            feature_flag_refresh_enabled=True,
        )
        # Get AI endpoint from Azure App Configuration
        ai_endpoint = CONFIG.get("ai_endpoint")
        if not ai_endpoint:
            raise ValueError("ai_endpoint configuration is required in Azure App Configuration")

        # Initialize feature manager
        FEATURE_MANAGER = FeatureManager(
            CONFIG, targeting_context_accessor=targeting_accessor, on_feature_evaluated=publish_telemetry
        )

        # Initialize OpenAI service with endpoint from configuration
        OPENAI_SERVICE = AzureOpenAIService(ai_endpoint)

        logger.info("Azure App Configuration and Feature Management initialized successfully")

    except Exception as ex:
        logger.error("Failed to initialize Azure App Configuration: %s", ex)
        raise SystemExit("Application failed to start due to configuration error")


# Initialize configuration on startup
initialize_app_configuration()

app.config.update(CONFIG)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def loader_user(user_id):
    """Load user by ID for Flask-Login."""
    return Users.query.get(user_id)


with app.app_context():
    db.create_all()

@app.before_request
def assign_session_id():
    """Assign a unique session ID if not already set, or use logged-in user id."""
    if current_user.is_authenticated:
        session["user_id"] = current_user.username
    elif "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())

@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    """Endpoint to handle chat requests."""
    global CONFIG

    CONFIG.refresh()
    try:
        data = request.get_json()

        # Convert history from list of dicts to list of ChatbotMessage objects
        if "history" in data:
            data["history"] = [ChatbotMessage(**message) for message in data["history"]]

        message = ChatRequest(**data)

        if not message:
            return jsonify({"error": "Message cannot be empty"}), 400

        # Get Agent variant from feature flags
        agent_variant = FEATURE_MANAGER.get_variant("Agent")
        agent_id = agent_variant.configuration if agent_variant else None

        if not agent_id:
            logger.error("Missing required configuration: agent_id")
            return jsonify({"error": "Service configuration error"}), 500

        # Get response using the selected agent
        response = OPENAI_SERVICE.get_response(message, agent_id)
        metrics = {}
        if agent_variant.name == "newAgent":
            metrics = {"agent_name": response.agent_name, "CSAT": round(random.uniform(2.5, 5), 1)}
        else:
            metrics = {"agent_name": response.agent_name, "CSAT": round(random.uniform(1, 3), 1)}
        track_event("agent_metrics", session["user_id"], metrics)
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
