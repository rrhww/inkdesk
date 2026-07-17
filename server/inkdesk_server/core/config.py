from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
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
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="local", alias="INKDESK_ENV")
    db_url: str = Field(
        default="postgresql+psycopg://inkdesk:inkdesk@localhost:5432/inkdesk",
        alias="INKDESK_DB_URL",
    )
    migration_lock_timeout_seconds: float = Field(
        default=30.0,
        ge=0,
        alias="INKDESK_MIGRATION_LOCK_TIMEOUT_SECONDS",
    )
    job_backend: str = Field(default="durable", alias="INKDESK_JOB_BACKEND")
    job_poll_interval_seconds: float = Field(default=1.0, gt=0, alias="INKDESK_JOB_POLL_INTERVAL_SECONDS")
    job_lease_seconds: int = Field(default=60, gt=0, alias="INKDESK_JOB_LEASE_SECONDS")
    job_heartbeat_seconds: int = Field(default=10, gt=0, alias="INKDESK_JOB_HEARTBEAT_SECONDS")
    job_shutdown_grace_seconds: int = Field(default=10, ge=0, alias="INKDESK_JOB_SHUTDOWN_GRACE_SECONDS")
    job_default_max_attempts: int = Field(default=3, gt=0, alias="INKDESK_JOB_DEFAULT_MAX_ATTEMPTS")
    vault_root: Path = Field(default=Path("./inkdesk-vault"), alias="INKDESK_VAULT_ROOT")
    agent_runtime: str = Field(default="langgraph", alias="INKDESK_AGENT_RUNTIME")
    agent_provider_profile: str = Field(default="openai", alias="INKDESK_AGENT_PROVIDER_PROFILE")
    agent_model: str | None = Field(default=None, alias="INKDESK_AGENT_MODEL")
    agent_api_key: str | None = Field(default=None, alias="INKDESK_AGENT_API_KEY")
    agent_base_url: str | None = Field(default=None, alias="INKDESK_AGENT_BASE_URL")
    embedding_provider_profile: str = Field(default="openai", alias="INKDESK_EMBEDDING_PROVIDER_PROFILE")
    embedding_model: str | None = Field(default="text-embedding-3-small", alias="INKDESK_EMBEDDING_MODEL")
    embedding_api_key: str | None = Field(default=None, alias="INKDESK_EMBEDDING_API_KEY")
    embedding_base_url: str | None = Field(default=None, alias="INKDESK_EMBEDDING_BASE_URL")
    agent_connect_timeout_seconds: float = Field(default=2.0, alias="INKDESK_AGENT_CONNECT_TIMEOUT_SECONDS")
    agent_read_timeout_seconds: float = Field(default=20.0, alias="INKDESK_AGENT_READ_TIMEOUT_SECONDS")
    # Claude Code 子进程的工作目录（仓库根）。
    # repoContext 只是 briefing 里的标签字符串，不能作为子进程 cwd。
    repo_root: str | None = Field(default=None, alias="INKDESK_REPO_ROOT")
    # Claude Agent SDK 可选配置：覆盖默认的 Anthropic API 端点和认证。
    # 留空则让 SDK 读取 ~/.claude/settings.json 的用户级配置（推荐）。
    claude_api_base_url: str | None = Field(default=None, alias="INKDESK_CLAUDE_API_BASE_URL")
    claude_api_token: str | None = Field(default=None, alias="INKDESK_CLAUDE_API_TOKEN")
    # 模型映射：ccswitch 把 Claude 模型名映射到 DeepSeek 等第三方模型。
    # setting_sources=[] 禁用了 settings.json，必须显式传入这些映射，否则
    # Claude Code 会用默认的 claude-sonnet-4-5 请求，第三方端点不识别 → 工具调用空转。
    claude_model: str | None = Field(default=None, alias="INKDESK_CLAUDE_MODEL")
    claude_default_sonnet_model: str | None = Field(default=None, alias="INKDESK_CLAUDE_DEFAULT_SONNET_MODEL")
    claude_default_haiku_model: str | None = Field(default=None, alias="INKDESK_CLAUDE_DEFAULT_HAIKU_MODEL")
    claude_default_opus_model: str | None = Field(default=None, alias="INKDESK_CLAUDE_DEFAULT_OPUS_MODEL")
    # Claude Agent SDK 单次 query 的最大轮次和预算（USD），防止失控。
    claude_max_turns: int = Field(default=20, alias="INKDESK_CLAUDE_MAX_TURNS")
    claude_max_budget_usd: float = Field(default=1.0, alias="INKDESK_CLAUDE_MAX_BUDGET_USD")
    # 交互式 coding：True=启用 can_use_tool 权限弹窗 + SSE 流式对话；
    # False=保留 bypassPermissions 行为（快速执行，无前端交互）。
    claude_interactive_mode: bool = Field(default=True, alias="INKDESK_CLAUDE_INTERACTIVE_MODE")
    # can_use_tool 等待前端回应的超时秒数，超时视为拒绝。
    claude_permission_timeout_seconds: int = Field(
        default=120, alias="INKDESK_CLAUDE_PERMISSION_TIMEOUT_SECONDS"
    )
    # SSE 事件队列上限，满了优先丢弃 partial_message。
    claude_sse_queue_maxsize: int = Field(default=100, alias="INKDESK_CLAUDE_SSE_QUEUE_MAXSIZE")
    enable_web_assist: bool = Field(default=True, alias="INKDESK_ENABLE_WEB_ASSIST")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    deepseek_api_key: str | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    enable_local_seed: bool = Field(default=True, alias="INKDESK_ENABLE_LOCAL_SEED")

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
