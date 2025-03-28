import os
import logging
from flask import Flask, request, jsonify
from azure_open_ai_service import AzureOpenAIService
from llm_configuration import (
    LLMConfiguration,
    AzureOpenAIConnectionInfo,
    LLMConfiguration,
)
from azure.identity import DefaultAzureCredential
from azure.appconfiguration.provider import load, WatchKey
from azure_open_ai_service import AzureOpenAIService
from models import ChatRequest, ChatbotMessage

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Load configuration from Azure App Configuration
def load_configuration():
    credential = DefaultAzureCredential()
    app_config_endpoint = os.getenv("AZURE_APP_CONFIG_ENDPOINT")
    configurations = load(app_config_endpoint, credential, refresh_on=[WatchKey("AZURE_OPENAI"),WatchKey("CHAT_LLM")])

    app.config.update(configurations)


# Load configuration
load_configuration()

# Register services
azure_openai_connection_info = AzureOpenAIConnectionInfo(**app.config["AZURE_OPENAI"])
llm_configuration = LLMConfiguration(**app.config["CHAT_LLM"])
openai_service = AzureOpenAIService(azure_openai_connection_info, llm_configuration)


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()

        # Convert history from list of dicts to list of ChatbotMessage objects
        if "history" in data:
            data["history"] = [
                ChatbotMessage(**message) for message in data["history"]
            ]

        message = ChatRequest(**data)

        if not message:
            return jsonify({"error": "Message cannot be empty"}), 400

        response = openai_service.get_chat_completion(message)
        return jsonify(response), 200

    except Exception as ex:
        logger.error(f"Error processing chat request: {ex}")
        return (
            jsonify({"error": "An error occurred while processing your request"}),
            500,
        )


@app.route("/api/chat/model", methods=["GET"])
def get_model_name():
    return jsonify({"model": llm_configuration.model}), 200


if __name__ == "__main__":
    app.run()
