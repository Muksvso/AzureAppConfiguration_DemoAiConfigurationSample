"""
This module defines the data models used in the chat application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


@dataclass
class ChatbotMessage:
    """Represents a message in the chat history."""

    role: str = ""
    content: str | None = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChatRequest:
    """Represents a chat request."""

    message: str = ""
    history: List[ChatbotMessage] = field(default_factory=list)


@dataclass
class ChatResponse:
    """Represents a chat response."""

    message: str | None = ""
    history: List[ChatbotMessage] = field(default_factory=list)
    agent_name: str = ""


# Create user model
class Users(UserMixin, db.Model):
    """Represents a user in the system."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password_hash = db.Column(db.String(250), nullable=False)

    def __init__(self, username, password):
        self.username = username
        self.password_hash = password
