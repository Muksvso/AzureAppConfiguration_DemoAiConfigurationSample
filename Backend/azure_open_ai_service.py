"""
Azure OpenAI Service wrapper for chat completion.
"""

import logging
from datetime import datetime, timezone
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from models import ChatRequest, ChatResponse, ChatbotMessage


logger = logging.getLogger(__name__)


class AzureOpenAIService:
    """
    Azure OpenAI Service wrapper for chat completion.
    """

    def __init__(self, ai_endpoint: str, model: str):
        self.model = model

        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )

        self.client = AzureOpenAI(
            base_url=ai_endpoint,
            azure_ad_token_provider=token_provider,
            api_version="preview",
        )

    def get_response(self, request: ChatRequest) -> ChatResponse:
        """
        Get chat completion from Azure OpenAI service.
        """
        messages = []

        # Add conversation history
        for message in request.history:
            messages.append({"role": message.role, "content": message.content})

        # Add current user message
        messages.append({"role": "user", "content": request.message})

        ai_request = self.client.responses.create(
            model=self.model,
            input=request.message
        )

        response = self.client.responses.retrieve(ai_request.id)

        response_content = response.output[0].content[0].text

        # Update history
        history = request.history.copy()
        history.append(
            ChatbotMessage(
                role="user",
                content=request.message,
                timestamp=datetime.now(tz=timezone.utc),
            )
        )
        return ChatResponse(message=response_content, history=history)
