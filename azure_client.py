"""
Azure OpenAI (Azure AI Foundry) client wrapper.

Encapsulates all communication with the deployed model so the rest of the app
does not need to know about the SDK details. The deployment name (e.g.
"gpt-5.4") is configured via environment variables.
"""
import logging

from openai import APIConnectionError, APIStatusError, APITimeoutError, AzureOpenAI

from config import Settings, get_settings
from models import ChatMessage

logger = logging.getLogger("tpf.azure")


class AzureOpenAIError(Exception):
    """Raised when the Azure OpenAI call fails."""


class AzureOpenAIService:
    """Thin wrapper around the AzureOpenAI SDK client."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: AzureOpenAI | None = None

        if self._settings.azure_configured:
            # The SDK targets a specific deployment via the `model` argument
            # using the deployment name configured in Azure AI Foundry.
            self._client = AzureOpenAI(
                azure_endpoint=self._settings.azure_openai_endpoint,
                api_key=self._settings.azure_openai_api_key,
                api_version=self._settings.azure_openai_api_version,
            )
        else:
            logger.warning(
                "Azure OpenAI is not fully configured. /chat will return an error "
                "until AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY and "
                "AZURE_OPENAI_DEPLOYMENT_NAME are set."
            )

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def build_messages(
        self, message: str, history: list[ChatMessage]
    ) -> list[dict[str, str]]:
        """
        Compose the full message list sent to the model: a system prompt, the
        prior conversation history, and the new user message.
        """
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._settings.system_prompt}
        ]
        # Carry over previous turns for multi-turn context (skip any system
        # messages from the client to avoid overriding our system prompt).
        for turn in history:
            if turn.role in ("user", "assistant"):
                messages.append({"role": turn.role, "content": turn.content})
        messages.append({"role": "user", "content": message})
        return messages

    def get_chat_completion(self, message: str, history: list[ChatMessage]) -> str:
        """Call the deployed model and return the assistant's reply text."""
        if self._client is None:
            raise AzureOpenAIError(
                "Azure OpenAI is not configured on the server. Check the backend "
                ".env file."
            )

        messages = self.build_messages(message, history)

        try:
            response = self._client.chat.completions.create(
                model=self._settings.azure_openai_deployment,
                messages=messages,
            )
        except APITimeoutError as exc:
            logger.exception("Azure OpenAI request timed out")
            raise AzureOpenAIError("The AI service timed out. Please try again.") from exc
        except APIConnectionError as exc:
            logger.exception("Could not connect to Azure OpenAI")
            raise AzureOpenAIError(
                "Could not reach the AI service. Please check your connection."
            ) from exc
        except APIStatusError as exc:
            logger.exception("Azure OpenAI returned an error status")
            raise AzureOpenAIError(
                f"The AI service returned an error (HTTP {exc.status_code})."
            ) from exc
        except Exception as exc:  # noqa: BLE001 - surface a safe message
            logger.exception("Unexpected Azure OpenAI error")
            raise AzureOpenAIError("An unexpected AI service error occurred.") from exc

        choice = response.choices[0] if response.choices else None
        reply = (choice.message.content if choice and choice.message else None) or ""
        if not reply.strip():
            raise AzureOpenAIError("The AI service returned an empty response.")
        return reply.strip()
