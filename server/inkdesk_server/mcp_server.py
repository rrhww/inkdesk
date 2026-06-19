from __future__ import annotations

import json

from pydantic import Field
from starlette.requests import Request as StarletteRequest
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from inkdesk_server.core.config import Settings
from inkdesk_server.db import session_scope
from inkdesk_server.deposit_service import DepositService
from inkdesk_server.health_service import HealthService
from inkdesk_server.security import OwnerSessionService
from inkdesk_server.run_service import RunService
from inkdesk_server.vault import VaultService


MAX_QUERY_LENGTH = 500


def _resolve_workspace_id(ctx: Context, settings: Settings) -> str:
    starlette_req: StarletteRequest = ctx.request_context.request
    token = starlette_req.cookies.get("inkdesk_owner_session", "")
    if not token:
        raise PermissionError("missing inkdesk_owner_session cookie")

    session_service = OwnerSessionService(settings)
    with session_scope() as db:
        session = session_service.verify_session_token(token, db)
        if session is None:
            raise PermissionError("session expired or invalid")
        from inkdesk_server.security import get_current_workspace
        workspace = get_current_workspace(db, session.username)
        return workspace.id


def build_mcp_server(settings: Settings) -> FastMCP:
    mcp = FastMCP(
        "inkdesk",
        streamable_http_path="/",
        stateless_http=True,
        transport_security=TransportSecuritySettings(
            allowed_hosts=[],
            enable_dns_rebinding_protection=False,
            require_host_header=False,
        ),
    )

    @mcp.tool(name="context_pack", title="上下文包",
              description="获取 DevRun 的完整上下文，包括任务信息、Ask 历史和阶段输出。")
    def context_pack(
        ctx: Context,
        run_id: str = Field(validation_alias="runId"),
    ) -> str:
        if not run_id or not run_id.strip():
            return json.dumps({"error": "runId is required"}, ensure_ascii=False)

        workspace_id = _resolve_workspace_id(ctx, settings)
        with session_scope() as db:
            try:
                run = RunService(db).get_run(run_id, workspace_id)
            except Exception:
                return json.dumps({"error": f"DevRun not found: {run_id}"}, ensure_ascii=False)

            pack = {
                "id": run.id,
                "type": run.type,
                "title": run.title,
                "goal": run.goal,
                "repoContext": run.repoContext,
                "status": run.status,
                "currentStage": run.currentStage,
                "stages": [{"name": s.name, "status": s.status} for s in run.stages],
                "eventCount": len(run.events),
            }
            return json.dumps(pack, ensure_ascii=False)

    @mcp.tool(name="search", title="搜索知识库",
              description="在 wiki 和 raw 目录中全文搜索，返回匹配的页面路径与摘要。")
    def search(ctx: Context, query: str) -> str:
        query = query.strip()
        if not query:
            return json.dumps({"error": "query is required"}, ensure_ascii=False)
        if len(query) > MAX_QUERY_LENGTH:
            return json.dumps({"error": f"query too long (max {MAX_QUERY_LENGTH} chars)"}, ensure_ascii=False)

        vault = VaultService(settings)
        results: list[dict] = []

        for directory in ["wiki", "raw"]:
            for rel_path in vault.list_markdown_files(directory):
                try:
                    content = vault.read_vault_file(rel_path)
                except Exception:
                    continue
                if query.lower() in content.lower():
                    results.append({
                        "path": rel_path,
                        "snippet": content[:200],
                    })

        return json.dumps({"results": results, "count": len(results)}, ensure_ascii=False)

    @mcp.tool(name="deposit", title="沉淀知识",
              description="将外部 Agent 的阶段输出或发现提交到审阅队列。不会直接写入 wiki。")
    def deposit(
        ctx: Context,
        source: str,
        payload: dict,
        run_id: str | None = Field(default=None, validation_alias="runId"),
        ask_turn_id: str | None = Field(default=None, validation_alias="askTurnId"),
        stage: str | None = None,
    ) -> str:
        workspace_id = _resolve_workspace_id(ctx, settings)
        with session_scope() as db:
            service = DepositService(db, VaultService(settings))
            try:
                result = service.deposit(
                    workspace_id=workspace_id,
                    source=source,
                    payload=payload,
                    run_id=run_id,
                    ask_turn_id=ask_turn_id,
                    stage=stage,
                )
                return json.dumps({
                    "reviewId": result.reviewId,
                    "status": result.status,
                    "source": result.source,
                    "isNew": result.isNew,
                }, ensure_ascii=False)
            except Exception as exc:
                return json.dumps({"error": str(exc)}, ensure_ascii=False)

    @mcp.tool(name="health_check", title="知识库健康检查",
              description="返回 Vault 知识库的结构健康摘要。")
    def health_check(ctx: Context) -> str:
        service = HealthService(settings, VaultService(settings))
        result = service.scan()
        return json.dumps(result["summary"], ensure_ascii=False)

    return mcp
