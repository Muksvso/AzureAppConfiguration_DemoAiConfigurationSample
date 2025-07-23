"""
Azure OpenAI Service wrapper for chat completion.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from models import ChatRequest, ChatResponse, ChatbotMessage


logger = logging.getLogger(__name__)


class AzureOpenAIService:
    """
    Azure OpenAI Service wrapper for chat completion with dynamic configuration support.
    """

    def __init__(self, ai_endpoint: str = "", model: str = ""):
        self._current_endpoint = ai_endpoint
        self._current_model = model
        self._current_variant = "default"
        self._client: Optional[AzureOpenAI] = None
        
        if ai_endpoint and model:
            self._initialize_client(ai_endpoint)

    def _initialize_client(self, ai_endpoint: str):
        """Initialize the Azure OpenAI client."""
        try:
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
            )

            self._client = AzureOpenAI(
                base_url=ai_endpoint,
                azure_ad_token_provider=token_provider,
                api_version="2024-02-01",  # Use a stable API version
            )
            logger.info(f"Azure OpenAI client initialized for endpoint: {ai_endpoint}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {e}")
            self._client = None

    def update_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Update the service configuration with new endpoint and model.
        
        Args:
            config: Dictionary containing endpoint, model, and variant_name
            
        Returns:
            True if configuration was updated successfully
        """
        endpoint = config.get("endpoint", "")
        model = config.get("model", "")
        variant_name = config.get("variant_name", "unknown")
        
        if not endpoint or not model:
            logger.warning("Invalid configuration: endpoint and model are required")
            return False
            
        # Check if configuration has changed
        if (endpoint != self._current_endpoint or 
            model != self._current_model or 
            variant_name != self._current_variant):
            
            logger.info(f"Updating configuration: endpoint={endpoint}, model={model}, variant={variant_name}")
            
            # Initialize new client if endpoint changed
            if endpoint != self._current_endpoint:
                self._initialize_client(endpoint)
                self._current_endpoint = endpoint
                
            self._current_model = model
            self._current_variant = variant_name
            
            return True
            
        return False

    @property
    def model(self) -> str:
        """Get the current model name."""
        return self._current_model
        
    @property
    def variant(self) -> str:
        """Get the current variant name."""
        return self._current_variant
        
    @property
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return bool(self._client is not None and self._current_model and self._current_endpoint)

    def get_response(self, request: ChatRequest) -> ChatResponse:
        """
        Get chat completion from Azure OpenAI service.
        """
        if not self.is_configured:
            raise ValueError("Azure OpenAI service is not properly configured")
            
        messages = []

        # Add conversation history
        for message in request.history:
            messages.append({"role": message.role, "content": message.content})

        # Add current user message
        messages.append({"role": "user", "content": request.message})

        try:
            # Use chat completions instead of responses (which is deprecated)
            response = self._client.chat.completions.create(
                model=self._current_model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )

            response_content = response.choices[0].message.content

            # Update history
            history = request.history.copy()
            history.append(
                ChatbotMessage(
                    role="user",
                    content=request.message,
                    timestamp=datetime.now(tz=timezone.utc),
                )
            )
            history.append(
                ChatbotMessage(
                    role="assistant",
                    content=response_content,
                    timestamp=datetime.now(tz=timezone.utc),
                )
            )
            
            return ChatResponse(message=response_content, history=history)
            
        except Exception as e:
            logger.error(f"Error getting response from Azure OpenAI: {e}")
            raise
