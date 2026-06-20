from __future__ import annotations

import json

from pydantic import Field
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from inkdesk_server.core.config import Settings
from inkdesk_server.db import session_scope
from inkdesk_server.deposit_service import DepositService
from inkdesk_server.health_service import HealthService
from inkdesk_server.run_service import RunService
from inkdesk_server.vault import VaultService


MAX_QUERY_LENGTH = 500
CONTEXT_PACK_LIMIT = 20


def _resolve_workspace_id(ctx: Context, settings: Settings) -> str:
    from sqlalchemy import select
    from inkdesk_server.models import Workspace
    from inkdesk_server.research import DEFAULT_WORKSPACE_SLUG

    with session_scope() as db:
        workspace = db.scalar(select(Workspace).where(Workspace.slug == DEFAULT_WORKSPACE_SLUG))
        if workspace is None:
            raise PermissionError(f"Workspace not found: {DEFAULT_WORKSPACE_SLUG}")
        return workspace.id


def _build_context_pack(settings: Settings, workspace_id: str, run_id: str) -> str:
    import json
    from sqlalchemy import select, desc

    with session_scope() as db:
        from inkdesk_server.models import DevRun, AskTurn, ReviewItem

        run = db.get(DevRun, run_id)
        if run is None or run.workspace_id != workspace_id:
            return json.dumps({"error": f"DevRun not found: {run_id}"}, ensure_ascii=False)

        # --- 阶段事件 ---
        events_data = []
        for e in sorted(run.events, key=lambda x: x.created_at):
            payload = {}
            try:
                payload = json.loads(e.payload_json)
            except (json.JSONDecodeError, TypeError):
                pass
            events_data.append({
                "id": e.id,
                "type": e.event_type,
                "stage": e.stage,
                "payload": payload,
            })

        # --- 关联 Ask 历史（最近 CONTEXT_PACK_LIMIT 条）---
        ask_turns = db.scalars(
            select(AskTurn)
            .where(AskTurn.run_id == run_id, AskTurn.workspace_id == workspace_id)
            .order_by(desc(AskTurn.created_at))
            .limit(CONTEXT_PACK_LIMIT)
        ).all()
        asks_data = []
        for a in reversed(ask_turns):
            gaps = []
            try:
                gaps = json.loads(a.knowledge_gaps_json)
            except (json.JSONDecodeError, TypeError):
                pass
            asks_data.append({
                "id": a.id,
                "question": a.question,
                "answer": a.answer[:800],
                "confidence": a.confidence,
                "knowledgeGaps": gaps[:10],
                "canWriteback": a.can_writeback,
                "createdAt": a.created_at.isoformat(),
            })

        # --- 关联 Deposit / Review（通过 proposal_payload_json 中的 runId）---
        reviews = db.scalars(
            select(ReviewItem)
            .where(ReviewItem.workspace_id == workspace_id, ReviewItem.status == "PENDING")
        ).all()
        related_reviews = []
        for r in reviews:
            try:
                pp = json.loads(r.proposal_payload_json)
            except (json.JSONDecodeError, TypeError):
                continue
            if pp.get("runId") == run_id:
                related_reviews.append({
                    "id": r.id,
                    "kind": r.kind,
                    "title": r.title,
                    "summary": r.summary[:300],
                    "status": r.status,
                })

        pack = {
            "id": run.id,
            "type": run.type,
            "title": run.title,
            "goal": run.goal,
            "repoContext": run.repo_context,
            "status": run.status,
            "currentStage": run.current_stage,
            "stages": [
                {"name": s, "status": (
                    "completed" if _stage_passed(s, run.current_stage, run.stage_status)
                    else ("active" if s == run.current_stage else "pending")
                )} for s in ("context", "solution", "review", "coding", "testing", "deposit")
            ],
            "events": events_data,
            "askHistory": asks_data,
            "relatedReviews": related_reviews,
        }
        return json.dumps(pack, ensure_ascii=False)


_STAGES = ("context", "solution", "review", "coding", "testing", "deposit")


def _stage_passed(stage: str, current: str, stage_status: str) -> bool:
    try:
        idx = _STAGES.index(stage)
        cur_idx = _STAGES.index(current)
    except ValueError:
        return False
    return idx < cur_idx or (idx == cur_idx and stage_status in ("completed", "skipped"))


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
              description="获取 DevRun 完整上下文：任务信息、阶段事件、Ask 历史和相关待审提案。")
    def context_pack(
        ctx: Context,
        run_id: str = Field(validation_alias="runId"),
    ) -> str:
        if not run_id or not run_id.strip():
            return json.dumps({"error": "runId is required"}, ensure_ascii=False)

        workspace_id = _resolve_workspace_id(ctx, settings)
        return _build_context_pack(settings, workspace_id, run_id)

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
