from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
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
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="local", alias="INKVAULT_ENV")
    db_url: str = Field(
        default="postgresql+psycopg://inkvault:inkvault@localhost:5432/inkvault",
        alias="INKVAULT_DB_URL",
    )
    vault_root: Path = Field(default=Path("./inkvault-vault"), alias="INKVAULT_VAULT_ROOT")
    auth_secret: str = Field(
        default="inkvault-local-owner-session-secret",
        validation_alias=AliasChoices("INKVAULT_AUTH_SECRET", "APP_JWT_SECRET"),
    )
    auth_session_duration: timedelta = Field(default=timedelta(hours=8), alias="INKVAULT_AUTH_SESSION_DURATION")
    auth_allow_legacy_owner_cookie: bool = Field(default=True, alias="INKVAULT_AUTH_ALLOW_LEGACY_OWNER_COOKIE")
    owner_session_cookie: str = "inkvault_owner_session"
    agent_runtime: str = Field(default="langgraph", alias="INKVAULT_AGENT_RUNTIME")
    agent_provider_profile: str = Field(default="openai", alias="INKVAULT_AGENT_PROVIDER_PROFILE")
    agent_model: str | None = Field(default=None, alias="INKVAULT_AGENT_MODEL")
    agent_api_key: str | None = Field(default=None, alias="INKVAULT_AGENT_API_KEY")
    agent_base_url: str | None = Field(default=None, alias="INKVAULT_AGENT_BASE_URL")
    embedding_provider_profile: str = Field(default="openai", alias="INKVAULT_EMBEDDING_PROVIDER_PROFILE")
    embedding_model: str | None = Field(default="text-embedding-3-small", alias="INKVAULT_EMBEDDING_MODEL")
    embedding_api_key: str | None = Field(default=None, alias="INKVAULT_EMBEDDING_API_KEY")
    embedding_base_url: str | None = Field(default=None, alias="INKVAULT_EMBEDDING_BASE_URL")
    agent_connect_timeout_seconds: float = Field(default=2.0, alias="INKVAULT_AGENT_CONNECT_TIMEOUT_SECONDS")
    agent_read_timeout_seconds: float = Field(default=20.0, alias="INKVAULT_AGENT_READ_TIMEOUT_SECONDS")
    enable_web_assist: bool = Field(default=True, alias="INKVAULT_ENABLE_WEB_ASSIST")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    enable_local_seed: bool = Field(default=True, alias="INKVAULT_ENABLE_LOCAL_SEED")

    @property
    def resolved_agent_provider(self) -> AgentProviderConfig:
        profile = (self.agent_provider_profile or "openai").strip().lower()
        if profile == "deepseek":
            model = (self.agent_model or "").strip() or "deepseek-v4-flash"
            base_url = (self.agent_base_url or self.openai_base_url or "https://api.deepseek.com").strip()
            api_key = (self.agent_api_key or self.deepseek_api_key or self.openai_api_key or "").strip() or None
            return AgentProviderConfig(
                profile="deepseek",
                name="deepseek",
                model=model,
                base_url=base_url,
                api_key=api_key,
                structured_output_method="json_mode",
            )

        model = (self.agent_model or "").strip() or "gpt-4.1-mini"
        base_url = (self.agent_base_url or self.openai_base_url or "https://api.openai.com/v1").strip()
        api_key = (self.agent_api_key or self.openai_api_key or self.deepseek_api_key or "").strip() or None
        structured_output_method = "json_schema"
        if "deepseek.com" in base_url.lower() or model.lower().startswith("deepseek"):
            structured_output_method = "json_mode"
        return AgentProviderConfig(
            profile=profile if profile in {"openai", "openai_compatible", "custom"} else "openai",
            name="openai" if profile == "openai" else "openai-compatible",
            model=model,
            base_url=base_url,
            api_key=api_key,
            structured_output_method=structured_output_method,
        )

    @property
    def agent_provider_name(self) -> str:
        return self.resolved_agent_provider.name

    @property
    def agent_provider_model(self) -> str:
        return self.resolved_agent_provider.model

    @property
    def agent_provider_base_url(self) -> str | None:
        return self.resolved_agent_provider.base_url

    @property
    def agent_provider_api_key(self) -> str | None:
        return self.resolved_agent_provider.api_key

    @property
    def agent_provider_structured_output_method(self) -> str:
        return self.resolved_agent_provider.structured_output_method

    @property
    def resolved_embedding_provider(self) -> EmbeddingProviderConfig:
        profile = (self.embedding_provider_profile or "openai").strip().lower()
        if profile == "deterministic":
            model = (self.embedding_model or "").strip() or "deterministic-32"
            return EmbeddingProviderConfig(
                profile="deterministic",
                name="deterministic",
                model=model,
                base_url=None,
                api_key=None,
            )

        model = (self.embedding_model or "").strip() or "text-embedding-3-small"
        base_url = (
            self.embedding_base_url
            or self.openai_base_url
            or self.agent_base_url
            or "https://api.openai.com/v1"
        ).strip()
        api_key = (
            self.embedding_api_key
            or self.openai_api_key
            or self.deepseek_api_key
            or self.agent_api_key
            or ""
        ).strip() or None
        normalized_profile = profile if profile in {"openai", "openai_compatible", "custom", "deepseek"} else "openai"
        return EmbeddingProviderConfig(
            profile=normalized_profile,
            name="openai" if normalized_profile == "openai" else "openai-compatible",
            model=model,
            base_url=base_url,
            api_key=api_key,
        )

    @property
    def embedding_provider_name(self) -> str:
        return self.resolved_embedding_provider.name

    @property
    def embedding_provider_model(self) -> str:
        return self.resolved_embedding_provider.model

    @property
    def embedding_provider_base_url(self) -> str | None:
        return self.resolved_embedding_provider.base_url

    @property
    def embedding_provider_api_key(self) -> str | None:
        return self.resolved_embedding_provider.api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
