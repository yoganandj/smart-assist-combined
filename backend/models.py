"""Pydantic request/response models for the TPF Assistant API."""
from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in the conversation history."""

    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    """Payload for POST /chat."""

    # The new user prompt to answer.
    message: str = Field(..., min_length=1, description="The latest user prompt.")
    # Prior conversation turns (for multi-turn context). Most recent last.
    history: list[ChatMessage] = Field(default_factory=list)
    # UI attribute to select the target agent ('code' or 'document')
    mode: Literal["code", "document"] = Field(
        default="code",
        description="Target agent: 'code' for existing agent, 'document' for second agent.",
    )


class ChatResponse(BaseModel):
    """The assistant's reply."""

    reply: str


class CurrentUserResponse(BaseModel):
    """Signed-in user's identity and assigned app roles."""

    userId: str
    displayName: str
    roles: list[str]
