"""Flask application for Azure OpenAI Service integration."""

import os
import logging
import uuid
from flask import Flask, request, jsonify, session
from azure_open_ai_service import AzureOpenAIService
from models import ChatRequest, ChatbotMessage
from azure.appconfiguration.provider import SettingSelector, WatchKey, AzureAppConfigurationProvider
from azure.identity import DefaultAzureCredential
from featuremanagement import FeatureManager, TargetingContext
from azure.monitor.opentelemetry import configure_azure_monitor

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set secret key for sessions
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

# Configure Azure Monitor telemetry
connection_string = os.getenv("ApplicationInsightsConnectionString")
if connection_string:
    configure_azure_monitor(connection_string=connection_string)
    logger.info("Azure Monitor configured")
else:
    logger.warning("ApplicationInsightsConnectionString not provided - telemetry disabled")

# Configure Azure App Configuration
app_config_endpoint = os.getenv("AZURE_APP_CONFIGURATION_ENDPOINT")
if not app_config_endpoint:
    raise ValueError("AZURE_APP_CONFIGURATION_ENDPOINT environment variable is required")

# Initialize App Configuration provider with refresh enabled
try:
    config = AzureAppConfigurationProvider.load(
        endpoint=app_config_endpoint,
        credential=DefaultAzureCredential(),
        selectors=[
            SettingSelector(key_filter="ai_endpoint"),
            SettingSelector(key_filter="Agent*", label_filter="*")
        ],
        feature_flag_enabled=True,
        feature_flag_refresh_enabled=True,
        on_refresh_success=lambda: logger.info("Configuration refreshed successfully")
    )
    logger.info("Azure App Configuration provider initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Azure App Configuration: {e}")
    raise

# Initialize Feature Manager
def targeting_context_accessor():
    """Get targeting context for the current user."""
    user_id = session.get("user_id", "anonymous")
    return TargetingContext(user_id=user_id, groups=[])

feature_manager = FeatureManager(config, targeting_context_accessor=targeting_context_accessor)

# Get AI endpoint from configuration
ai_endpoint = config.get("ai_endpoint")
if not ai_endpoint:
    raise ValueError("ai_endpoint configuration not found in Azure App Configuration")

# Initialize OpenAI service (without fixed assistant_id)
openai_service = AzureOpenAIService(ai_endpoint)

@app.before_request
def assign_user_id():
    """Assign a unique user ID for targeting if not already present."""
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
        logger.info(f"Assigned new user ID: {session['user_id']}")


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
        agent_variant = feature_manager.get_variant("Agent")
        agent_id = None
        
        if agent_variant:
            agent_id = agent_variant.configuration.get("agent_id")
            logger.info(f"Using agent variant: {agent_variant.name} with agent_id: {agent_id}")
        
        if not agent_id:
            logger.error("No agent_id found in variant configuration")
            return jsonify({"error": "Agent configuration not available"}), 500

        response = openai_service.get_response(message, agent_id)
        return jsonify(response), 200

    except Exception as ex:
        logger.error("Error processing chat request: %s", ex)
        return (
            jsonify({"error": "An error occurred while processing your request"}),
            500,
        )


if __name__ == "__main__":
    app.run()
