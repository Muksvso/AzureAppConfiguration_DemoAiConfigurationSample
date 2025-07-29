"""Flask application for Azure OpenAI Service integration."""

import os
import logging
import uuid
import random

# Configure Azure Monitor before importing Flask
connection_string = os.getenv("APPLICATION_INSIGHTS_CONNECTION_STRING")
if connection_string:
    from azure.monitor.opentelemetry import configure_azure_monitor
    configure_azure_monitor(connection_string=connection_string)

from flask import Flask, request, jsonify, session
from azure.identity import DefaultAzureCredential
from azure.appconfiguration.provider import load, SettingSelector
from featuremanagement import FeatureManager, TargetingContext
from azure_open_ai_service import AzureOpenAIService
from models import ChatRequest, ChatbotMessage

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Azure App Configuration Provider
config = load(
    endpoint=os.getenv("AZURE_APP_CONFIGURATION_ENDPOINT"),
    credential=DefaultAzureCredential(),
    selectors=[SettingSelector(key_filter="*")],
    feature_flag_enabled=True,
    feature_flag_refresh_enabled=True,
    on_refresh_success=lambda: logger.info("Feature flags refreshed successfully")
)

# Targeting context accessor for feature management
def targeting_context_accessor():
    user_id = session.get('user_id')
    if user_id:
        return TargetingContext(user_id=user_id)
    return None

# Initialize Feature Manager
feature_manager = FeatureManager(config, targeting_context_accessor=targeting_context_accessor)





@app.before_request
def before_request():
    """Assign a unique user ID and refresh configuration."""
    # Assign unique user ID for targeting
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    # Refresh Azure App Configuration to get latest feature flags
    config.refresh()


# Register services
ai_endpoint = config.get("ai_endpoint")
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

        # Get the agent variant from feature management
        agent_variant = feature_manager.get_variant("Agent")
        agent_id = agent_variant.configuration if agent_variant else "defaultAgent"
        
        response = openai_service.get_response(message, agent_id)
        
        # Track telemetry
        agent_name = agent_variant.name if agent_variant else "defaultAgent"
        
        # Generate random CSAT based on agent type
        if agent_name == "newAgent":
            csat_value = round(random.uniform(2.5, 5.0), 2)
        else:  # oldAgent or default
            csat_value = round(random.uniform(1.0, 3.0), 2)
        
        # Track event for telemetry
        config.track_event(
            "agent_metrics",
            {
                "agent_name": agent_name,
                "csat_value": csat_value
            }
        )
        
        return jsonify(response), 200

    except Exception as ex:
        logger.error("Error processing chat request: %s", ex)
        return (
            jsonify({"error": "An error occurred while processing your request"}),
            500,
        )


if __name__ == "__main__":
    app.run()
