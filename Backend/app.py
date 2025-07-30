"""Flask application for Azure OpenAI Service integration with Azure App Configuration."""

import os
import logging
import uuid
import random
from azure.monitor.opentelemetry import configure_azure_monitor

# Configure Azure Monitor BEFORE importing Flask
connection_string = os.getenv("APPLICATION_INSIGHTS_CONNECTION_STRING")
if connection_string:
    configure_azure_monitor(connection_string=connection_string)

from flask import Flask, request, jsonify, session
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user
from azure.appconfiguration.provider import AzureAppConfigurationProvider
from azure.identity import DefaultAzureCredential
from featuremanagement import FeatureManager
from featuremanagement.targeting import TargetingContextAccessor
from opentelemetry import trace
from opentelemetry.trace import get_tracer_provider
from azure_open_ai_service import AzureOpenAIService
from models import ChatRequest, ChatbotMessage, db, Users


# Create Azure App Configuration provider
config_endpoint = os.getenv("AZURE_APP_CONFIGURATION_ENDPOINT")
if not config_endpoint:
    raise ValueError("AZURE_APP_CONFIGURATION_ENDPOINT environment variable is required")

app_config_provider = AzureAppConfigurationProvider.load(
    endpoint=config_endpoint,
    credential=DefaultAzureCredential(),
    feature_flag_enabled=True,
    feature_flag_refresh_enabled=True
)

def on_refresh_success(successful_refresh):
    """Callback for successful refresh of app configuration."""
    if successful_refresh:
        feature_manager.update_configuration(app_config_provider)

app_config_provider.on_refresh_success = on_refresh_success


class RequestTargetingContextAccessor(TargetingContextAccessor):
    """Targeting context accessor for feature management."""
    
    def get_user_id(self):
        """Get user ID for targeting."""
        if current_user and current_user.is_authenticated:
            return str(current_user.id)
        return session.get('user_id', 'anonymous')
    
    def get_groups(self):
        """Get user groups for targeting."""
        return []


# Initialize Feature Manager
from featuremanagement.azuremonitor import publish_telemetry

def on_feature_evaluated(evaluation_event):
    """Callback for when a feature is evaluated - sends telemetry to Azure Monitor."""
    publish_telemetry(evaluation_event)

feature_manager = FeatureManager(
    app_config_provider,
    targeting_context_accessor=RequestTargetingContextAccessor(),
    on_feature_evaluated=on_feature_evaluated
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-this")
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


@app.before_request
def before_request():
    """Handle pre-request setup for anonymous users and configuration refresh."""
    # Assign UUID to anonymous users
    if 'user_id' not in session and (not current_user or not current_user.is_authenticated):
        session['user_id'] = str(uuid.uuid4())
    
    # Refresh app configuration for latest feature flags
    app_config_provider.refresh()


with app.app_context():
    db.create_all()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get configurations from Azure App Configuration
ai_endpoint = app_config_provider.get("ai_endpoint")
if not ai_endpoint:
    raise ValueError("ai_endpoint configuration is required in Azure App Configuration")

openai_service = AzureOpenAIService(ai_endpoint)


@app.route("/api/chat", methods=["POST"])
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

        # Get agent variant from feature management
        agent_variant = feature_manager.get_variant("Agent", request=request)
        agent_id = agent_variant.configuration if agent_variant else None
        
        if not agent_id:
            return jsonify({"error": "Agent configuration not available"}), 500

        response = openai_service.get_response(message, agent_id)
        
        # Track telemetry
        track_agent_metrics(agent_variant.name if agent_variant else "unknown")
        
        return jsonify(response), 200

    except Exception as ex:
        logger.error("Error processing chat request: %s", ex)
        return (
            jsonify({"error": "An error occurred while processing your request"}),
            500,
        )


def track_agent_metrics(agent_name):
    """Track agent metrics with random CSAT values."""
    # Generate CSAT based on agent
    if agent_name == "newAgent":
        csat = round(random.uniform(2.5, 5.0), 2)
    elif agent_name == "oldAgent":
        csat = round(random.uniform(1.0, 3.0), 2)
    else:
        csat = round(random.uniform(1.0, 5.0), 2)
    
    metrics = {
        "agent_name": agent_name,
        "csat": csat
    }
    
    app_config_provider.track_event("agent_metrics", metrics)


# --- Authentication Endpoints ---
@app.route("/api/login", methods=["POST"])
def login():
    """Login user and return JWT token."""
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    user = Users.query.filter_by(username=username).first()
    if user and bcrypt.check_password_hash(user.password_hash, password):
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
        return jsonify({"success": True, "username": user.username}), 201
    except Exception:
        return jsonify({"success": False, "error": "Username already exists"}), 409


if __name__ == "__main__":
    app.run()
