from dataclasses import dataclass, field
from typing import List


@dataclass
class AzureOpenAIConnectionInfo:
    api_key: str
    endpoint: str
    api_version: str = "2024-12-01-preview"


@dataclass
class MessageConfiguration:
    role: str
    content: str


@dataclass
class LLMConfiguration:
    model_provider: str
    model: str
    temperature: float
    max_completion_tokens: int
    messages: List[MessageConfiguration] = field(default_factory=list)
