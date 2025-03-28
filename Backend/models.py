from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class ChatbotMessage:
    role: str = ""
    content: str | None = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChatRequest:
    message: str = ""
    history: List[ChatbotMessage] = field(default_factory=list)


@dataclass
class ChatResponse:
    message: str | None = ""
    history: List[ChatbotMessage] = field(default_factory=list)
