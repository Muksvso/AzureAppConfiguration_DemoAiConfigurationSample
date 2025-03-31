"""
This module defines the configuration for the LLM (Large Language Model) used in the application.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class AzureOpenAIConnectionInfo:
    """Represents the connection information for Azure OpenAI."""

    api_key: str
    endpoint: str
    api_version: str = "2024-12-01-preview"


@dataclass
class MessageConfiguration:
    """Represents a message configuration."""

    role: str
    content: str


@dataclass
class LLMConfiguration:
    """Represents the configuration for the LLM."""

    model_provider: str
    model: str
    temperature: float
    max_completion_tokens: int
    messages: List[MessageConfiguration]

    def __init__(
        self,
        model_provider: str = "azure_openai",
        model: str = "gpt-35-turbo",
        temperature: float = 0.7,
        max_completion_tokens: int = 1000,
        messages: Optional[List[Dict[str, str]]] = None,
    ):
        self.model_provider = model_provider
        self.model = model
        self.temperature = temperature
        self.max_completion_tokens = max_completion_tokens
        self.messages = []

        # Initialize messages if provided in the configuration
        if messages is not None:
            for message in messages:
                self.messages.append(MessageConfiguration(**message))
