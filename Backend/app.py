"""Flask application for Azure OpenAI Service integration."""

import os
import logging
import uuid
from flask import Flask, request, jsonify, session
from azure.identity import DefaultAzureCredential
from azure.appconfiguration.provider import load
from featuremanagement import FeatureManager, TargetingContext
from azure_open_ai_service import AzureOpenAIService
from models import ChatRequest, ChatbotMessage

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session management

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)





# Initialize Azure App Configuration
app_config_endpoint = os.getenv("AZURE_APPCONFIGURATION_ENDPOINT")
if not app_config_endpoint:
    logger.error("AZURE_APPCONFIGURATION_ENDPOINT environment variable is required")
    raise ValueError("AZURE_APPCONFIGURATION_ENDPOINT environment variable is required")

try:
    # Load configuration from Azure App Configuration
    config = load(
        endpoint=app_config_endpoint,
        credential=DefaultAzureCredential(),
        feature_flag_enabled=True,
        on_refresh_success=lambda: logger.info("Configuration refreshed successfully")
    )
    
    # Get ai_endpoint from App Configuration
    ai_endpoint = config.get("ai_endpoint")
    if not ai_endpoint:
        logger.error("ai_endpoint configuration is required in App Configuration")
        raise ValueError("ai_endpoint configuration is required in App Configuration")
        
    logger.info("Azure App Configuration loaded successfully")
    
except Exception as e:
    logger.error(f"Failed to connect to Azure App Configuration: {e}")
    raise

def get_targeting_context():
    """Get targeting context for the current user."""
    from flask import session, has_request_context
    
    if not has_request_context():
        return TargetingContext(user_id=None, groups=[])
    
    user_id = session.get('user_id')
    return TargetingContext(user_id=user_id, groups=[])


# Initialize Feature Manager
feature_manager = FeatureManager(config, targeting_context_accessor=get_targeting_context)

# Initialize services - will be created per request based on feature flags
openai_services = {}


@app.before_request
def assign_user_id():
    """Assign a unique user ID if not already present in session."""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
        logger.info(f"Assigned new user ID: {session['user_id']}")


def get_openai_service():
    """Get the appropriate OpenAI service based on feature flags."""
    # Get the agent variant from feature management - context is now provided via accessor
    agent_variant = feature_manager.get_variant("Agent")
    
    if agent_variant and agent_variant.configuration:
        agent_id = agent_variant.configuration
    else:
        # Fallback to environment variable if feature flag is not available
        agent_id = os.getenv("ASSISTANT_ID")
        if not agent_id:
            raise ValueError("No agent_id available from feature flags or environment")
    
    # Use a single service instance since all agents use the same endpoint
    # Only create the service once and store the agent_id for use in requests
    if 'openai_service' not in openai_services:
        openai_services['openai_service'] = AzureOpenAIService(ai_endpoint, agent_id)
        logger.info(f"Created OpenAI service with endpoint: {ai_endpoint}")
    
    # Update the agent_id for the current request
    openai_services['openai_service'].assistant_id = agent_id
    
    return openai_services['openai_service']


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

        response = get_openai_service().get_response(message)
        return jsonify(response), 200

    except Exception as ex:
        logger.error("Error processing chat request: %s", ex)
        return (
            jsonify({"error": "An error occurred while processing your request"}),
            500,
        )


if __name__ == "__main__":
    app.run()
