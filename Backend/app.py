"""Flask application for Azure OpenAI Service integration."""

import os
import logging
import uuid
from azure.monitor.opentelemetry import configure_azure_monitor

# Configure Azure Monitor before importing Flask
app_insights_connection_string = os.getenv("ApplicationInsightsConnectionString")
if app_insights_connection_string:
    configure_azure_monitor(connection_string=app_insights_connection_string)
else:
    print("Warning: ApplicationInsightsConnectionString not set, telemetry will not be enabled")

from flask import Flask, request, jsonify, session
from azure.appconfiguration.provider import SettingSelector, load
from azure.identity import DefaultAzureCredential
from featuremanagement import FeatureManager, TargetingFilter
from featuremanagement.azuremonitor import track_event
from azure_open_ai_service import AzureOpenAIService
from models import ChatRequest, ChatbotMessage

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Azure App Configuration setup
app_config_endpoint = os.getenv("AZURE_APP_CONFIGURATION_ENDPOINT")
if not app_config_endpoint:
    logger.error("AZURE_APP_CONFIGURATION_ENDPOINT environment variable is required")
    raise SystemExit("Application failed to start: Missing AZURE_APP_CONFIGURATION_ENDPOINT")

credential = DefaultAzureCredential()

try:
    # Load configuration with feature flags refresh enabled
    app_config = load(
        endpoint=app_config_endpoint,
        credential=credential,
        selectors=[SettingSelector(key_filter="*")],
        feature_flag_enabled=True,
        refresh_on=[{"key": "Agent", "label": None}],
        feature_flag_refresh_enabled=True
    )
    
except Exception as e:
    logger.error(f"Failed to connect to Azure App Configuration: {e}")
    raise SystemExit(f"Application failed to start: Unable to connect to Azure App Configuration: {e}")

# Feature Management setup with targeting context accessor
def targeting_context_accessor():
    return {"user_id": session.get("user_id", "")}

feature_manager = FeatureManager(
    feature_flags=app_config.get("feature_flags", {}),
    feature_filters=[TargetingFilter()],
    targeting_context_accessor=targeting_context_accessor
)

# Register refresh callback
app_config.on_refresh_success = lambda: feature_manager.update_feature_flags()





# Get AI endpoint from App Configuration
ai_endpoint = app_config.get("ai_endpoint")
if not ai_endpoint:
    logger.error("ai_endpoint configuration not found in Azure App Configuration")
    raise SystemExit("Application failed to start: ai_endpoint not configured")

# Initialize OpenAI Service (agent_id will be determined per request)
openai_service = AzureOpenAIService(ai_endpoint)


@app.before_request
def before_request():
    """Generate unique user ID for targeting and refresh App Configuration."""
    # Refresh App Configuration to get latest feature flags
    app_config.refresh()
    
    # Generate unique user ID if not present in session
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())


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

        # Get agent variant from feature manager
        agent_variant = feature_manager.get_variant("Agent")
        agent_id = agent_variant.configuration if agent_variant else None
        
        if not agent_id:
            logger.error("No agent variant assigned to user")
            return jsonify({"error": "Unable to determine agent"}), 500

        # Track variant usage in Azure Monitor
        track_event(
            event_name="FeatureFlag",
            user=session.get("user_id", ""),
            event_properties={
                "FeatureName": "Agent",
                "VariantName": agent_variant.name if agent_variant else "Unknown",
                "VariantConfiguration": agent_id
            }
        )

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
