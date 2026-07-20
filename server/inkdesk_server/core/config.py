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


@dataclass(frozen=True)
class EmbeddingProviderConfig:
    profile: str
    name: str
    model: str
    base_url: str | None
    api_key: str | None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="local", alias="INKDESK_ENV")
    db_url: str = Field(
        default="postgresql+psycopg://inkdesk:inkdesk@localhost:5432/inkdesk",
        alias="INKDESK_DB_URL",
    )
    vault_root: Path = Field(default=Path("./inkdesk-vault"), alias="INKDESK_VAULT_ROOT")
    repo_root: str | None = Field(default=None, alias="INKDESK_REPO_ROOT")

    agent_runtime: str = Field(default="deterministic", alias="INKDESK_AGENT_RUNTIME")
    agent_provider_profile: str = Field(default="openai", alias="INKDESK_AGENT_PROVIDER_PROFILE")
    agent_model: str | None = Field(default=None, alias="INKDESK_AGENT_MODEL")
    agent_api_key: str | None = Field(default=None, alias="INKDESK_AGENT_API_KEY")
    agent_base_url: str | None = Field(default=None, alias="INKDESK_AGENT_BASE_URL")
    agent_connect_timeout_seconds: float = Field(default=2.0, alias="INKDESK_AGENT_CONNECT_TIMEOUT_SECONDS")
    agent_read_timeout_seconds: float = Field(default=20.0, alias="INKDESK_AGENT_READ_TIMEOUT_SECONDS")

    embedding_provider_profile: str = Field(default="openai", alias="INKDESK_EMBEDDING_PROVIDER_PROFILE")
    embedding_model: str | None = Field(default="text-embedding-3-small", alias="INKDESK_EMBEDDING_MODEL")
    embedding_api_key: str | None = Field(default=None, alias="INKDESK_EMBEDDING_API_KEY")
    embedding_base_url: str | None = Field(default=None, alias="INKDESK_EMBEDDING_BASE_URL")

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

    @property
    def resolved_embedding_provider(self) -> EmbeddingProviderConfig:
        profile = (self.embedding_provider_profile or "openai").strip().lower()
        if profile == "deterministic":
            return EmbeddingProviderConfig("deterministic", "deterministic", (self.embedding_model or "").strip() or "deterministic-32", None, None)
        normalized = profile if profile in {"openai", "openai_compatible", "custom", "deepseek"} else "openai"
        return EmbeddingProviderConfig(
            profile=normalized,
            name="openai" if normalized == "openai" else "openai-compatible",
            model=(self.embedding_model or "").strip() or "text-embedding-3-small",
            base_url=(self.embedding_base_url or self.openai_base_url or self.agent_base_url or "https://api.openai.com/v1").strip(),
            api_key=(self.embedding_api_key or self.openai_api_key or self.deepseek_api_key or self.agent_api_key or "").strip() or None,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
