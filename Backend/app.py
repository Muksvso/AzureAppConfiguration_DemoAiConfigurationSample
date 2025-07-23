"""Flask application for Azure OpenAI Service integration."""

import os
import logging
import threading
import time
from flask import Flask, request, jsonify
from azure_open_ai_service import AzureOpenAIService
from configuration_service import ConfigurationService
from models import ChatRequest, ChatbotMessage

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)





# Initialize services
config_service = ConfigurationService()
openai_service = AzureOpenAIService()

# Configuration refresh thread
refresh_thread = None
stop_refresh = threading.Event()

def refresh_configuration_periodically():
    """Background thread to periodically refresh configuration."""
    while not stop_refresh.wait(30):  # Wait 30 seconds between refreshes
        try:
            if config_service.refresh_configuration():
                # Get updated AI model configuration
                ai_config = config_service.get_ai_model_configuration()
                
                # Update the OpenAI service if configuration changed
                if openai_service.update_configuration(ai_config):
                    logger.info(f"Updated AI service to use variant: {ai_config.get('variant_name', 'unknown')}")
                    
        except Exception as e:
            logger.error(f"Error in configuration refresh thread: {e}")

def initialize_services():
    """Initialize the OpenAI service with initial configuration."""
    try:
        ai_config = config_service.get_ai_model_configuration()
        openai_service.update_configuration(ai_config)
        
        if openai_service.is_configured:
            logger.info(f"OpenAI service initialized with model: {openai_service.model}, variant: {openai_service.variant}")
        else:
            logger.warning("OpenAI service could not be initialized - check configuration")
            
    except Exception as e:
        logger.error(f"Error initializing services: {e}")

# Initialize services on startup
initialize_services()

# Start configuration refresh thread if Azure App Configuration is available
if config_service.is_configured:
    refresh_thread = threading.Thread(target=refresh_configuration_periodically, daemon=True)
    refresh_thread.start()
    logger.info("Configuration refresh thread started")
else:
    logger.warning("Azure App Configuration not available - using fallback configuration")


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

        response = openai_service.get_response(message)
        return jsonify(response), 200

    except Exception as ex:
        logger.error("Error processing chat request: %s", ex)
        return (
            jsonify({"error": "An error occurred while processing your request"}),
            500,
        )


@app.route("/api/chat/model", methods=["GET"])
def get_model_name():
    """Endpoint to get the model name and configuration info."""
    return jsonify({
        "model": openai_service.model,
        "variant": openai_service.variant,
        "configured": openai_service.is_configured,
        "app_config_enabled": config_service.is_configured
    }), 200


@app.route("/api/config/refresh", methods=["POST"])
def refresh_config():
    """Endpoint to manually refresh configuration."""
    try:
        if config_service.refresh_configuration():
            ai_config = config_service.get_ai_model_configuration()
            config_updated = openai_service.update_configuration(ai_config)
            
            return jsonify({
                "success": True,
                "config_refreshed": True,
                "service_updated": config_updated,
                "current_model": openai_service.model,
                "current_variant": openai_service.variant
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Failed to refresh configuration"
            }), 500
            
    except Exception as e:
        logger.error(f"Error in manual config refresh: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    try:
        app.run()
    finally:
        # Cleanup: stop the refresh thread
        if refresh_thread and refresh_thread.is_alive():
            stop_refresh.set()
            refresh_thread.join(timeout=5)
            logger.info("Configuration refresh thread stopped")
