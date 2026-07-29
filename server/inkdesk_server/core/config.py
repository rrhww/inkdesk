from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(frozen=True)
class AgentProviderConfig:
    profile: str
    name: str
    model: str
    base_url: str | None
    api_key: str | None
    structured_output_method: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="local", alias="INKDESK_ENV")
    vault_root: Path = Field(
        default=Path(__file__).resolve().parents[2] / "vault",
        alias="INKDESK_VAULT_ROOT",
    )
    skills_root: Path = Field(
        default=Path(__file__).resolve().parents[2] / "vault" / "skills",
        alias="INKDESK_SKILLS_ROOT",
    )
    repo_root: str | None = Field(default=None, alias="INKDESK_REPO_ROOT")

    agent_runtime: str = Field(default="deterministic", alias="INKDESK_AGENT_RUNTIME")
    agent_provider_profile: str = Field(default="openai", alias="INKDESK_AGENT_PROVIDER_PROFILE")
    agent_model: str | None = Field(default=None, alias="INKDESK_AGENT_MODEL")
    agent_api_key: str | None = Field(default=None, alias="INKDESK_AGENT_API_KEY")
    agent_base_url: str | None = Field(default=None, alias="INKDESK_AGENT_BASE_URL")
    agent_connect_timeout_seconds: float = Field(default=2.0, alias="INKDESK_AGENT_CONNECT_TIMEOUT_SECONDS")
    agent_read_timeout_seconds: float = Field(default=20.0, alias="INKDESK_AGENT_READ_TIMEOUT_SECONDS")

    enable_file_watcher: bool = Field(default=True, alias="INKDESK_ENABLE_FILE_WATCHER")
    graph_sse_heartbeat_seconds: float = Field(default=15.0, alias="INKDESK_GRAPH_SSE_HEARTBEAT_SECONDS")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")

    @property
    def resolved_agent_provider(self) -> AgentProviderConfig:
        profile = (self.agent_provider_profile or "openai").strip().lower()
        if profile == "deepseek":
            return AgentProviderConfig(
                profile="deepseek",
                name="deepseek",
                model=(self.agent_model or "").strip() or "deepseek-v4-flash",
                base_url=(self.agent_base_url or self.openai_base_url or "https://api.deepseek.com").strip(),
                api_key=(self.agent_api_key or self.deepseek_api_key or self.openai_api_key or "").strip() or None,
                structured_output_method="json_mode",
            )

        base_url = (self.agent_base_url or self.openai_base_url or "https://api.openai.com/v1").strip()
        model = (self.agent_model or "").strip() or "gpt-4.1-mini"
        return AgentProviderConfig(
            profile=profile if profile in {"openai", "openai_compatible", "custom"} else "openai",
            name="openai" if profile == "openai" else "openai-compatible",
            model=model,
            base_url=base_url,
            api_key=(self.agent_api_key or self.openai_api_key or self.deepseek_api_key or "").strip() or None,
            structured_output_method="json_mode" if "deepseek.com" in base_url.lower() or model.lower().startswith("deepseek") else "json_schema",
        )

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
