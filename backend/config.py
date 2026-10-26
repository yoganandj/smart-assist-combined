"""
Configuration loader for the TPF Assistant backend.

All settings are read from environment variables (loaded from a local .env file
during development). Secrets such as the Azure OpenAI API key live ONLY here on
the backend and are never sent to the frontend.
"""
import os
from functools import lru_cache

from dotenv import load_dotenv

# Load variables from a local .env file if present (no-op in production where
# real environment variables are injected by the hosting platform).
load_dotenv()


class Settings:
    """Strongly-typed accessor for environment configuration."""

    def __init__(self) -> None:
        # --- Azure OpenAI / AI Foundry ---
        self.azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
        self.azure_openai_deployment: str = os.getenv(
            "AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.4"
        ).strip()
        self.azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
        self.azure_openai_api_version: str = os.getenv(
            "AZURE_OPENAI_API_VERSION", "2024-08-01-preview"
        ).strip()

        # --- Azure AI Foundry Agent Settings ---
        # Full project endpoint, e.g.
        # https://<resource>.services.ai.azure.com/api/projects/<project-name>
        self.project_endpoint: str = os.getenv(
            "AZURE_AI_PROJECT_ENDPOINT", ""
        ).strip()

        # --- Code Agent (existing agent) ---
        self.code_agent_name: str = os.getenv(
            "AZURE_AI_CODE_AGENT_NAME",
            os.getenv("AZURE_AI_AGENT_NAME", "fos-smart-assistant"),
        ).strip()
        self.code_agent_version: str = os.getenv(
            "AZURE_AI_CODE_AGENT_VERSION",
            os.getenv("AZURE_AI_AGENT_VERSION", "2"),
        ).strip()
        self.code_agent_id: str = os.getenv(
            "AZURE_AI_CODE_AGENT_ID",
            os.getenv("AZURE_AI_AGENT_ID", ""),
        ).strip()

        # Backward compatibility aliases
        self.agent_name: str = self.code_agent_name
        self.agent_version: str = self.code_agent_version
        self.agent_id: str = self.code_agent_id

        # --- Document Agent (second agent) ---
        self.doc_agent_name: str = os.getenv(
            "AZURE_AI_DOCUMENT_AGENT_NAME",
            os.getenv("AZURE_AI_DOC_AGENT_NAME", ""),
        ).strip()
        self.doc_agent_version: str = os.getenv(
            "AZURE_AI_DOCUMENT_AGENT_VERSION",
            os.getenv("AZURE_AI_DOC_AGENT_VERSION", "1"),
        ).strip()
        self.doc_agent_id: str = os.getenv(
            "AZURE_AI_DOCUMENT_AGENT_ID",
            os.getenv("AZURE_AI_DOC_AGENT_ID", ""),
        ).strip()

        # How the backend authenticates to Foundry. In the cloud use "default"
        # (Managed Identity via DefaultAzureCredential). Use "interactive" only
        # for local development where a browser login is possible.
        self.azure_auth_mode: str = os.getenv(
            "AZURE_AUTH_MODE", "default"
        ).strip().lower()

        # --- App Service Authentication / Entra app-role authorization ---
        self.required_app_role: str = os.getenv(
            "EASYAUTH_REQUIRED_APP_ROLE", "americanusers"
        ).strip()

        self.system_prompt: str = os.getenv(
            "SYSTEM_PROMPT",
            "You are TPF Assistant, a helpful, professional enterprise AI "
            "assistant. Answer clearly and concisely.",
        ).strip()

        # Origins allowed by CORS (the Angular dev server by default).
        raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:4200")
        self.cors_allowed_origins: list[str] = [
            origin.strip() for origin in raw_origins.split(",") if origin.strip()
        ]

    @property
    def azure_configured(self) -> bool:
        """True only when the minimum Azure settings are present."""
        return bool(
            self.azure_openai_endpoint
            and self.azure_openai_api_key
            and self.azure_openai_deployment
        )

    @property
    def agent_configured(self) -> bool:
        """True only when the Foundry agent settings are present."""
        return bool(self.project_endpoint and (self.code_agent_name or self.doc_agent_name))

    def get_agent_ref(self, mode: str = "code") -> tuple[str, str]:
        """Return (agent_name, agent_version) based on mode ('code' or 'document')."""
        if mode == "document":
            return self.doc_agent_name, self.doc_agent_version
        return self.code_agent_name, self.code_agent_version


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
