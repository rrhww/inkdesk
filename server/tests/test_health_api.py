from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient


COOKIE = {"inkdesk_owner_session": "owner"}


def _make_client(temp_app_env: Path) -> TestClient:
    from inkdesk_server.main import create_app
    return TestClient(create_app(), cookies=COOKIE)


def _ensure_vault(temp_app_env: Path) -> None:
    """确保 vault 已初始化并创建有问题的测试 fixtrue 页面。"""
    client = _make_client(temp_app_env)
    resp = client.post("/api/vault/initialize", json={"vaultType": "general"})
    assert resp.status_code == 200, f"vault init failed: {resp.text}"


def _write_page(vault_root: Path, relative_path: str, content: str) -> None:
    target = vault_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


# ── 断链 (broken links) ──

def test_broken_links_detected(temp_app_env: Path) -> None:
    _ensure_vault(temp_app_env)

    # 创建一页引用不存在的页面
    _write_page(temp_app_env, "wiki/broken-link-page.md", """---
type: concept
created: 2026-06-01
updated: 2026-06-01
tags: [test]
related: []
source_file: raw/some-source.md
status: stable
---
# 断链测试页
这里引用了一个 [[不存在的页面]]，应该被检测到。
""")

    client = _make_client(temp_app_env)
    resp = client.get("/api/health")
    assert resp.status_code == 200, f"health endpoint failed: {resp.text}"
    data = resp.json()

    broken_link_findings = [f for f in data["findings"] if f["type"] == "BROKEN_LINK"]
    assert len(broken_link_findings) >= 1, f"expected at least 1 broken link finding, got {len(broken_link_findings)}"
    found = broken_link_findings[0]
    assert found["severity"] == "warning"
    assert "不存在的页面" in found["detail"]
    assert found["page"] == "wiki/broken-link-page.md"


def test_valid_wikilink_not_flagged(temp_app_env: Path) -> None:
    _ensure_vault(temp_app_env)

    _write_page(temp_app_env, "wiki/target-page.md", """---
type: concept
created: 2026-06-01
updated: 2026-06-01
tags: [test]
related: []
source_file: raw/some-source.md
status: stable
---
# 目标页
这个页面存在。
""")

    _write_page(temp_app_env, "wiki/link-ok-page.md", """---
type: concept
created: 2026-06-01
updated: 2026-06-01
tags: [test]
related: [target-page]
source_file: raw/some-source.md
status: stable
---
# 有效链接页
引用 [[target-page]]，这个页面存在，不应被标记。
""")

    client = _make_client(temp_app_env)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()

    broken_link_pages = {f["page"] for f in data["findings"] if f["type"] == "BROKEN_LINK"}
    assert "wiki/link-ok-page.md" not in broken_link_pages, f"valid link should not be flagged as broken"


# ── 孤页 (orphan pages) ──

def test_orphan_page_detected(temp_app_env: Path) -> None:
    _ensure_vault(temp_app_env)

    # 创建一个 wiki 页，没有其他页引用它
    _write_page(temp_app_env, "wiki/orphan-page.md", """---
type: concept
created: 2026-06-01
updated: 2026-06-01
tags: [test]
related: []
source_file: raw/some-source.md
status: stable
---
# 孤页测试
这个页面没有任何其他页面链接过来。
""")

    client = _make_client(temp_app_env)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()

    orphan_findings = [f for f in data["findings"] if f["type"] == "ORPHAN_PAGE"]
    assert len(orphan_findings) >= 1, f"expected at least 1 orphan finding, got {len(orphan_findings)}"
    found = orphan_findings[0]
    assert found["severity"] == "info"
    assert found["page"] == "wiki/orphan-page.md"


def test_linked_page_not_orphan(temp_app_env: Path) -> None:
    _ensure_vault(temp_app_env)

    _write_page(temp_app_env, "wiki/linked-target.md", """---
type: concept
created: 2026-06-01
updated: 2026-06-01
tags: [test]
related: []
source_file: raw/some-source.md
status: stable
---
# 被链接的目标页
""")

    _write_page(temp_app_env, "wiki/linker-page.md", """---
type: concept
created: 2026-06-01
updated: 2026-06-01
tags: [test]
related: [linked-target]
source_file: raw/some-source.md
status: stable
---
# 链接页
引用 [[linked-target]]，所以 linked-target 不是孤页。
""")

    client = _make_client(temp_app_env)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()

    orphan_targets = {f["page"] for f in data["findings"] if f["type"] == "ORPHAN_PAGE"}
    assert "wiki/linked-target.md" not in orphan_targets, "linked page should not be orphan"


# ── 缺 frontmatter ──

def test_missing_frontmatter_detected(temp_app_env: Path) -> None:
    _ensure_vault(temp_app_env)

    # 没有 frontmatter 的页面
    _write_page(temp_app_env, "wiki/no-frontmatter.md", """# 缺 frontmatter 页
这个页面没有任何 YAML frontmatter，应该被检测到。
""")

    # 有 frontmatter 但缺必填字段的页面
    _write_page(temp_app_env, "wiki/missing-fields.md", """---
title: 只有标题
---
# 缺字段页
只有 title，缺 type、created、tags。
""")

    client = _make_client(temp_app_env)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()

    missing_fm_findings = [f for f in data["findings"] if f["type"] == "MISSING_FRONTMATTER"]
    no_fm = next((f for f in missing_fm_findings if f["page"] == "wiki/no-frontmatter.md"), None)
    assert no_fm is not None, f"expected missing frontmatter finding for no-frontmatter page"
    assert no_fm["severity"] == "warning"

    missing_fields = next((f for f in missing_fm_findings if f["page"] == "wiki/missing-fields.md"), None)
    assert missing_fields is not None, f"expected missing frontmatter finding for missing-fields page"


def test_valid_frontmatter_not_flagged(temp_app_env: Path) -> None:
    _ensure_vault(temp_app_env)

    _write_page(temp_app_env, "wiki/valid-fm.md", """---
type: concept
created: 2026-06-01
updated: 2026-06-01
tags: [test]
related: []
source_file: raw/some-source.md
status: stable
---
# 完整 frontmatter 页
有所有必填字段，不应被标记。
""")

    client = _make_client(temp_app_env)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()

    fm_pages = {f["page"] for f in data["findings"] if f["type"] == "MISSING_FRONTMATTER"}
    assert "wiki/valid-fm.md" not in fm_pages, "page with complete frontmatter should not be flagged"


# ── 缺来源 (missing source) ──

def test_missing_source_detected(temp_app_env: Path) -> None:
    _ensure_vault(temp_app_env)

    # stable 状态但没有 source_file
    _write_page(temp_app_env, "wiki/no-source-stable.md", """---
type: concept
created: 2026-06-01
updated: 2026-06-01
tags: [test]
related: []
status: stable
---
# 缺来源的 stable 页
这个页面标记为 stable 但没有 source_file，应该被检测。
""")

    # stable 状态有 source_file 但内容里没有 [[引用]]
    _write_page(temp_app_env, "wiki/no-inline-source.md", """---
type: concept
created: 2026-06-01
updated: 2026-06-01
tags: [test]
related: []
status: stable
---
# 空 source_file 的页
source_file 为空，也没有内联来源引用。
""")

    client = _make_client(temp_app_env)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()

    missing_source_findings = [f for f in data["findings"] if f["type"] == "MISSING_SOURCE"]
    no_source = next((f for f in missing_source_findings if f["page"] == "wiki/no-source-stable.md"), None)
    assert no_source is not None, f"expected missing source finding for stable page without source"

    no_inline = next((f for f in missing_source_findings if f["page"] == "wiki/no-inline-source.md"), None)
    assert no_inline is not None, f"expected missing source finding for stable page with empty source_file"


def test_draft_page_without_source_not_flagged(temp_app_env: Path) -> None:
    _ensure_vault(temp_app_env)

    # draft 状态缺少 source_file 不应被标记
    _write_page(temp_app_env, "wiki/draft-no-source.md", """---
type: concept
created: 2026-06-01
updated: 2026-06-01
tags: [test]
related: []
status: draft
---
# Draft 页
这个页面是 draft 状态，缺来源不应被标记。
""")

    client = _make_client(temp_app_env)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()

    draft_source_findings = [f for f in data["findings"] if f["type"] == "MISSING_SOURCE" and f["page"] == "wiki/draft-no-source.md"]
    assert len(draft_source_findings) == 0, "draft page without source should not be flagged"


# ── 豁免页（系统页、模板页） ──

def test_system_pages_exempt_from_health_checks(temp_app_env: Path) -> None:
    _ensure_vault(temp_app_env)

    client = _make_client(temp_app_env)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()

    exempt_pages = {
        "AGENTS.md",
        "KB-META.md",
        "wiki/index.md",
        "wiki/log.md",
        "schema/vault-layout.md",
        "schema/wiki-page-template.md",
        "schema/source-citation-rules.md",
        "schema/ingest-proposal-rules.md",
        "schema/ask-answer-rules.md",
        "schema/wiki-health-rules.md",
    }

    for finding in data["findings"]:
        assert finding["page"] not in exempt_pages, (
            f"system/template page {finding['page']} should be exempt from health checks, "
            f"but got finding type={finding['type']}"
        )


# ── 健康摘要 ──

def test_health_summary_counts(temp_app_env: Path) -> None:
    _ensure_vault(temp_app_env)

    _write_page(temp_app_env, "wiki/broken-link.md", """---
type: concept
created: 2026-06-01
updated: 2026-06-01
tags: [test]
related: []
status: stable
---
引用 [[nonexistent-page]]。
""")

    _write_page(temp_app_env, "wiki/orphan.md", """---
type: concept
created: 2026-06-01
updated: 2026-06-01
tags: [test]
related: []
source_file: raw/some-source.md
status: stable
---
# 孤页
""")

    client = _make_client(temp_app_env)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()

    assert "summary" in data, "health response must include summary"
    summary = data["summary"]
    assert "totalPages" in summary
    assert "brokenLinkCount" in summary
    assert "orphanPageCount" in summary
    assert "missingFrontmatterCount" in summary
    assert "missingSourceCount" in summary

    assert summary["brokenLinkCount"] >= 1
    assert summary["orphanPageCount"] >= 1


# ── 幂等性 ──

def test_health_scan_idempotent(temp_app_env: Path) -> None:
    _ensure_vault(temp_app_env)

    client = _make_client(temp_app_env)
    first = client.get("/api/health").json()
    second = client.get("/api/health").json()

    assert first["summary"] == second["summary"], "health scan should be idempotent"
    assert len(first["findings"]) == len(second["findings"]), "finding count should be stable across scans"


# ── 不修改 Vault ──

def test_health_scan_does_not_modify_vault(temp_app_env: Path) -> None:
    _ensure_vault(temp_app_env)

    vault_root = temp_app_env
    before_files = sorted(f for f in vault_root.rglob("*") if f.is_file())

    client = _make_client(temp_app_env)
    client.get("/api/health")

    after_files = sorted(f for f in vault_root.rglob("*") if f.is_file())
    assert before_files == after_files, "health scan must not create or delete any vault files"
