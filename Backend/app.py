"""Flask application for Azure OpenAI Service integration."""

import os
import logging
import uuid
from flask import Flask, request, jsonify, session
from azure.identity import DefaultAzureCredential
from azure.appconfiguration.provider import load
from azure.monitor.opentelemetry import configure_azure_monitor
from featuremanagement import FeatureManager, TargetingContext
from azure_open_ai_service import AzureOpenAIService
from models import ChatRequest, ChatbotMessage

configure_azure_monitor(connection_string=os.getenv("ApplicationInsightsConnectionString"))

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




# Global variables for configuration and feature management
config = None
feature_manager = None
openai_service = None


def targeting_accessor():
    """Targeting accessor to identify users for feature flag targeting."""
    # Extract user information from request header
    return TargetingContext(user_id=session['user_id'])


def initialize_app_configuration():
    """Initialize Azure App Configuration and Feature Management."""
    global config, feature_manager, openai_service
    
    try:
        # Get App Configuration endpoint from environment variable
        app_config_endpoint = os.getenv("AZURE_APPCONFIGURATION_ENDPOINT")
        if not app_config_endpoint:
            raise ValueError("AZURE_APPCONFIGURATION_ENDPOINT environment variable is required")
        
        # Load configuration with refresh enabled for feature flags
        config = load(
            endpoint=app_config_endpoint,
            credential=DefaultAzureCredential(),
            feature_flag_enabled=True,
            feature_flag_refresh_enabled=True
        )
        
        # Get AI endpoint from Azure App Configuration
        ai_endpoint = config.get("ai_endpoint")
        if not ai_endpoint:
            raise ValueError("ai_endpoint configuration is required in Azure App Configuration")
        
        # Initialize feature manager
        feature_manager = FeatureManager(
            config,
            targeting_context_accessor=targeting_accessor
        )
        
        # Initialize OpenAI service with endpoint from configuration
        openai_service = AzureOpenAIService(ai_endpoint)
        
        logger.info("Azure App Configuration and Feature Management initialized successfully")
        
    except Exception as ex:
        logger.error("Failed to initialize Azure App Configuration: %s", ex)
        raise SystemExit("Application failed to start due to configuration error")


# Initialize configuration on startup
initialize_app_configuration()

@app.before_request
def assign_session_id():
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())

@app.route("/api/chat", methods=["POST"])
def chat():
    """Endpoint to handle chat requests."""
    global config

    config.refresh()
    try:
        data = request.get_json()

        # Convert history from list of dicts to list of ChatbotMessage objects
        if "history" in data:
            data["history"] = [ChatbotMessage(**message) for message in data["history"]]

        message = ChatRequest(**data)

        if not message:
            return jsonify({"error": "Message cannot be empty"}), 400

        # Get Agent variant from feature flags
        agent_variant = feature_manager.get_variant("Agent")
        agent_id = agent_variant.configuration if agent_variant else None
        
        if not agent_id:
            logger.error("Missing required configuration: agent_id")
            return jsonify({"error": "Service configuration error"}), 500

        # Get response using the selected agent
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
