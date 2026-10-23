"""
Azure AI Foundry Agent client wrapper.

Talks to a pre-created Foundry Agent (e.g. "fos-smart-assistant") using the
Responses API via the project's OpenAI-compatible client. The agent is
referenced by name + version through an "agent_reference" (the approach shown
in the Foundry portal sample), so the app uses the agent's own instructions,
knowledge and tools instead of calling the raw model.

Authentication uses Entra ID. The credential is selected by AZURE_AUTH_MODE:

* "default" (recommended for the cloud): DefaultAzureCredential, which uses the
  app's Managed Identity when running in Azure (and Azure CLI / env vars during
  local development). No browser or human interaction is required.
* "interactive": InteractiveBrowserCredential, which opens a browser window for
  a manual login. Only usable during local development.

Whatever identity is used (the Managed Identity in the cloud, or your user
account locally) must have the "Foundry User" role on the project.
"""
import logging
from collections.abc import Iterator

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, InteractiveBrowserCredential

from config import Settings, get_settings
from models import ChatMessage

logger = logging.getLogger("tpf.agent")


class FoundryAgentError(Exception):
    """Raised when a call to the Foundry agent fails."""


class FoundryAgentService:
    """Talks to a Foundry agent via the Responses API (agent_reference)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._project_client: AIProjectClient | None = None
        self._openai_client = None

        if self._settings.agent_configured:
            credential = self._build_credential()
            self._project_client = AIProjectClient(
                endpoint=self._settings.project_endpoint,
                credential=credential,
            )
            self._openai_client = self._project_client.get_openai_client()
        else:
            logger.warning(
                "Foundry agent is not configured. /chat will return an error "
                "until AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_AGENT_NAME are set."
            )

    @property
    def is_configured(self) -> bool:
        return self._openai_client is not None

    def _build_credential(self):
        """
        Select an Entra ID credential based on AZURE_AUTH_MODE.

        In the cloud, leave AZURE_AUTH_MODE at "default" so DefaultAzureCredential
        uses the app's Managed Identity (no browser / manual login needed). Set it
        to "interactive" only for local development.
        """
        if self._settings.azure_auth_mode == "interactive":
            logger.info("Using InteractiveBrowserCredential (local development).")
            return InteractiveBrowserCredential()

        logger.info("Using DefaultAzureCredential (Managed Identity in the cloud).")
        return DefaultAzureCredential()

    def _build_agent_reference(self, mode: str = "code") -> dict[str, str]:
        """Build agent_reference dictionary for the target mode ('code' or 'document')."""
        agent_name, agent_version = self._settings.get_agent_ref(mode)
        if not agent_name:
            env_var = "AZURE_AI_DOC_AGENT_NAME" if mode == "document" else "AZURE_AI_AGENT_NAME"
            raise FoundryAgentError(
                f"Agent for mode '{mode}' is not configured on the server. "
                f"Please set {env_var} in your .env file."
            )

        agent_reference: dict[str, str] = {
            "name": agent_name,
            "type": "agent_reference",
        }
        if agent_version:
            agent_reference["version"] = agent_version
        return agent_reference

    def get_reply(
        self, message: str, history: list[ChatMessage], mode: str = "code"
    ) -> str:
        """Send the prompt + history to the selected agent and return its reply text."""
        client = self._openai_client
        if client is None:
            raise FoundryAgentError(
                "The Foundry agent is not configured on the server. Check the "
                "backend .env file (AZURE_AI_PROJECT_ENDPOINT, AZURE_AI_AGENT_NAME)."
            )

        # Build the input list: prior turns (for multi-turn context) + the new
        # user message. Skip client-supplied system messages.
        input_items: list[dict[str, str]] = []
        for turn in history:
            if turn.role in ("user", "assistant"):
                input_items.append({"role": turn.role, "content": turn.content})
        input_items.append({"role": "user", "content": message})

        agent_reference = self._build_agent_reference(mode)

        try:
            response = client.responses.create(
                input=input_items,
                extra_body={"agent_reference": agent_reference},
            )
        except Exception as exc:  # noqa: BLE001 - surface a safe message
            logger.exception("Foundry agent call failed for mode '%s'", mode)
            raise FoundryAgentError(
                "An unexpected agent error occurred. Please try again."
            ) from exc

        reply = (getattr(response, "output_text", None) or "").strip()
        if not reply:
            raise FoundryAgentError("The agent returned an empty response.")
        return reply

    def stream_reply(
        self, message: str, history: list[ChatMessage], mode: str = "code"
    ) -> Iterator[str]:
        """Yield reply text deltas from the Foundry agent stream for the selected mode."""
        client = self._openai_client
        if client is None:
            raise FoundryAgentError(
                "The Foundry agent is not configured on the server. Check the "
                "backend .env file (AZURE_AI_PROJECT_ENDPOINT, AZURE_AI_AGENT_NAME)."
            )

        input_items: list[dict[str, str]] = []
        for turn in history:
            if turn.role in ("user", "assistant"):
                input_items.append({"role": turn.role, "content": turn.content})
        input_items.append({"role": "user", "content": message})

        agent_reference = self._build_agent_reference(mode)

        try:
            with client.responses.stream(
                input=input_items,
                model=self._settings.azure_openai_deployment,
                extra_body={"agent_reference": agent_reference},
            ) as stream:
                for event in stream:
                    if event.type == "response.output_text.delta" and event.delta:
                        yield event.delta
        except Exception as exc:  # noqa: BLE001 - surface a safe message
            logger.exception("Foundry agent streaming call failed for mode '%s'", mode)
            raise FoundryAgentError(
                "An unexpected agent error occurred. Please try again."
            ) from exc

