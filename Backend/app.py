"""Flask application for Azure OpenAI Service integration."""

import os
import logging
from flask import Flask, request, jsonify
from azure.identity import DefaultAzureCredential
from azure.appconfiguration.provider import load, SettingSelector
from featuremanagement import FeatureManager
from azure_open_ai_service import AzureOpenAIService
from models import ChatRequest, ChatbotMessage

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)




# Global variables for configuration and feature management
config = None
feature_manager = None
openai_service = None


def targeting_accessor(request):
    """Targeting accessor to identify users for feature flag targeting."""
    # Extract user information from request
    user_id = request.headers.get('User-Id', 'anonymous')
    groups = request.headers.get('User-Groups', '').split(',') if request.headers.get('User-Groups') else []
    
    return {
        'user_id': user_id,
        'groups': groups
    }


def on_refresh_success():
    """Callback function when configuration refresh succeeds."""
    global feature_manager
    try:
        # Update feature manager with refreshed configuration
        if config and hasattr(config, 'feature_flag_provider'):
            feature_manager = FeatureManager(
                feature_flag_provider=config.feature_flag_provider,
                targeting_accessor=targeting_accessor
            )
            logger.info("Feature management updated successfully after configuration refresh")
    except Exception as ex:
        logger.error("Error updating feature management after refresh: %s", ex)


def initialize_app_configuration():
    """Initialize Azure App Configuration and Feature Management."""
    global config, feature_manager, openai_service
    
    try:
        # Get App Configuration endpoint from environment variable
        app_config_endpoint = os.getenv("AZURE_APPCONFIGURATION_ENDPOINT")
        if not app_config_endpoint:
            raise ValueError("AZURE_APPCONFIGURATION_ENDPOINT environment variable is required")
        
        # Load configuration with refresh enabled for feature flags
        credential = DefaultAzureCredential()
        
        config = load(
            endpoint=app_config_endpoint,
            credential=credential,
            feature_flag_enabled=True,
            feature_flag_refresh_enabled=True,
            refresh_interval=30,  # Refresh every 30 seconds
            on_refresh_success=on_refresh_success
        )
        
        # Initialize feature manager
        feature_manager = FeatureManager(
            feature_flag_provider=config.feature_flag_provider,
            targeting_accessor=targeting_accessor
        )
        
        # Initialize OpenAI service - will be configured per request based on feature flags
        openai_service = AzureOpenAIService()
        
        logger.info("Azure App Configuration and Feature Management initialized successfully")
        
    except Exception as ex:
        logger.error("Failed to initialize Azure App Configuration: %s", ex)
        raise SystemExit("Application failed to start due to configuration error")


# Initialize configuration on startup (unless explicitly disabled for testing)
if os.getenv("SKIP_AZURE_INIT") != "true":
    initialize_app_configuration()
else:
    # For testing purposes
    config = None
    feature_manager = None
    openai_service = AzureOpenAIService()


# Register services
# Remove hardcoded environment variable usage
# ai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
# assistant_id = os.getenv("ASSISTANT_ID")
# openai_service = AzureOpenAIService(ai_endpoint, assistant_id)


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

        # Get feature-flagged configuration for this request
        targeting_context = targeting_accessor(request)
        
        # Get AI endpoint variant
        ai_endpoint = None
        agent_id = None
        
        if feature_manager:
            ai_endpoint_variant = feature_manager.get_variant(
                feature_flag="ai_endpoint",
                targeting_context=targeting_context
            )
            ai_endpoint = ai_endpoint_variant.configuration if ai_endpoint_variant else config.get("ai_endpoint")
            
            # Get Agent variant
            agent_variant = feature_manager.get_variant(
                feature_flag="Agent", 
                targeting_context=targeting_context
            )
            agent_id = agent_variant.configuration if agent_variant else os.getenv("ASSISTANT_ID")
        else:
            # Fallback to environment variables when feature management is not available
            ai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            agent_id = os.getenv("ASSISTANT_ID")
        
        if not ai_endpoint or not agent_id:
            logger.error("Missing required configuration: ai_endpoint=%s, agent_id=%s", ai_endpoint, agent_id)
            return jsonify({"error": "Service configuration error"}), 500

        # Configure the OpenAI service for this request
        openai_service.configure(ai_endpoint, agent_id)
        
        response = openai_service.get_response(message)
        return jsonify(response), 200

    except Exception as ex:
        logger.error("Error processing chat request: %s", ex)
        return (
            jsonify({"error": "An error occurred while processing your request"}),
            500,
        )


if __name__ == "__main__":
    app.run()
