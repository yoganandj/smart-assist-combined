"""Pydantic request/response models for the TPF Assistant API."""
from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Payload for POST /login."""

    passcode: str = Field(..., description="10-digit numeric demo passcode.")


class LoginResponse(BaseModel):
    """Result of a login attempt."""

    success: bool
    message: str
    token: str | None = None


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
