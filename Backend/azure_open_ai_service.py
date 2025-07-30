"""
Azure OpenAI Service wrapper for chat completion.
"""

import logging
from datetime import datetime, timezone
from azure.identity import DefaultAzureCredential
from models import ChatRequest, ChatResponse, ChatbotMessage
from azure.ai.projects import AIProjectClient

logger = logging.getLogger(__name__)


class AzureOpenAIService:
    """
    Azure OpenAI Service wrapper for chat completion.
    """

    def __init__(self, ai_endpoint: str, assistant_id: str):
        self.assistant_id = assistant_id
        self.project_client = AIProjectClient(
            endpoint=ai_endpoint,
            credential=DefaultAzureCredential(),  # Use Azure Default Credential for authentication
        )

    def get_response(self, request: ChatRequest) -> ChatResponse:
        """
        Get chat completion from Azure OpenAI service.
        """

        agent = self.project_client.agents.get_agent(agent_id=self.assistant_id)

        # Create a thread for communication
        thread = self.project_client.agents.threads.create()

        # Add conversation history
        for message in request.history:
            self.project_client.agents.messages.create(thread_id=thread.id, content=message.content, role=message.role)

        # Add current user message
        self.project_client.agents.messages.create(thread_id=thread.id, content=request.message, role="user")

        # Create and process an agent run
        self.project_client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)

        response = self.project_client.agents.messages.list(thread_id=thread.id)

        response_content = None

        for msg in response:
            if msg.role == "assistant":
                response_content = msg.content[0].text.value
                break

        # Update history
        history = request.history.copy()
        history.extend(
            [
                ChatbotMessage(
                    role="user",
                    content=request.message,
                    timestamp=datetime.now(tz=timezone.utc),
                ),
                ChatbotMessage(
                    role="assistant",
                    content=response_content,
                    timestamp=datetime.now(tz=timezone.utc),
                ),
            ]
        )
        agent_name = getattr(agent, "name", "Agent")
        return ChatResponse(message=response_content, history=history, agent_name=agent_name)
