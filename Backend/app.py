"""Flask application for Azure OpenAI Service integration."""

import os
import logging
import uuid
import random
from azure.monitor.opentelemetry import configure_azure_monitor

# Configure Azure Monitor before importing Flask
connection_string = os.getenv("APPLICATION_INSIGHTS_CONNECTION_STRING")
if connection_string:
    configure_azure_monitor(connection_string=connection_string)

from flask import Flask, request, jsonify, session
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from opentelemetry import trace
from opentelemetry.trace import get_tracer_provider
from azure.appconfiguration.provider import AzureAppConfigurationProvider
from azure.identity import DefaultAzureCredential
from featuremanagement import FeatureManager, TargetingContext
from azure_open_ai_service import AzureOpenAIService
from models import ChatRequest, ChatbotMessage, db, Users


app = Flask(__name__)
bcrypt = Bcrypt(app)

# Set up session secret key for storing user IDs
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

tracer = trace.get_tracer(__name__, tracer_provider=get_tracer_provider())

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

# Azure App Configuration setup
app_config_endpoint = os.getenv("AZURE_APP_CONFIGURATION_ENDPOINT")
if not app_config_endpoint:
    raise ValueError("AZURE_APP_CONFIGURATION_ENDPOINT environment variable is required")

credential = DefaultAzureCredential()

# Initialize Azure App Configuration provider with refresh enabled for feature flags
config = AzureAppConfigurationProvider(
    endpoint=app_config_endpoint,
    credential=credential,
    refresh_on=[
        {"key": "*", "refresh_interval": 30}  # Refresh all feature flags every 30 seconds
    ]
)

# Update Flask config with App Configuration values
app.config.update(config)

# Targeting context accessor for feature management
class UserTargetingContextAccessor:
    def get_targeting_context(self):
        from flask import session, g
        user_id = getattr(g, 'user_id', None)
        if user_id:
            return TargetingContext(user_id=user_id)
        return TargetingContext()

# Initialize Feature Manager
targeting_accessor = UserTargetingContextAccessor()
feature_manager = FeatureManager(config, targeting_context_accessor=targeting_accessor)

# Configure refresh success callback
def on_refresh_success():
    global feature_manager
    feature_manager = FeatureManager(config, targeting_context_accessor=targeting_accessor)

config.on_refresh_success = on_refresh_success

@login_manager.user_loader
def loader_user(user_id):
    """Load user by ID for Flask-Login."""
    return Users.query.get(user_id)


@app.before_request
def before_request():
    """Handle request setup including config refresh and user ID assignment."""
    from flask import g
    
    # Refresh configuration
    config.refresh()
    
    # Assign user ID for targeting
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    g.user_id = session['user_id']


with app.app_context():
    db.create_all()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AI service (will be configured per request based on feature flags)
ai_endpoint = config.get("ai_endpoint", os.getenv("AZURE_OPENAI_ENDPOINT"))
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

        # Get agent variant from feature flags
        agent_variant = feature_manager.get_variant("Agent")
        agent_id = None
        agent_name = "oldAgent"  # default
        
        if agent_variant:
            agent_id = agent_variant.configuration.get("agent_id")
            agent_name = agent_variant.name if hasattr(agent_variant, 'name') else "newAgent"
        
        # Fallback to environment variable if no variant
        if not agent_id:
            agent_id = os.getenv("ASSISTANT_ID")

        response = openai_service.get_response(message, agent_id)
        
        # Track telemetry
        track_agent_metrics(agent_name)
        
        return jsonify(response), 200

    except Exception as ex:
        logger.error("Error processing chat request: %s", ex)
        return (
            jsonify({"error": "An error occurred while processing your request"}),
            500,
        )


def track_agent_metrics(agent_name):
    """Track agent metrics telemetry."""
    try:
        # Generate CSAT value based on agent type
        if agent_name == "newAgent":
            csat_value = random.uniform(2.5, 5.0)
        else:  # oldAgent
            csat_value = random.uniform(1.0, 3.0)
        
        metrics = {
            "agent_name": agent_name,
            "csat": csat_value
        }
        
        # Track the event
        config.track_event("agent_metrics", metrics)
        
    except Exception as ex:
        logger.warning("Failed to track agent metrics: %s", ex)


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
