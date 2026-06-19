from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from inkdesk_server.core.config import Settings
from inkdesk_server.vault import VaultService


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[^\]|#]*?)?\]\]")

EXEMPT_PAGES = frozenset({
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
})

SCAN_DIRS = ["wiki", "raw"]


@dataclass
class HealthService:
    settings: Settings
    vault: VaultService

    def scan(self) -> dict:
        findings: list[dict] = []
        all_pages = self._collect_pages()
        scan_pages = [p for p in all_pages if p not in EXEMPT_PAGES]
        wiki_targets = frozenset(p for p in all_pages if p.startswith("wiki/"))

        for page in scan_pages:
            content = self._read_page(page)
            fm = self._parse_frontmatter(content)
            findings.extend(self._check_frontmatter(page, content, fm))
            findings.extend(self._check_broken_links(page, content, wiki_targets))
            findings.extend(self._check_missing_source(page, content, fm))

        # orphan check: pages with no inbound wikilinks
        findings.extend(self._check_orphans(scan_pages, wiki_targets))

        summary = {
            "totalPages": len(scan_pages),
            "brokenLinkCount": sum(1 for f in findings if f["type"] == "BROKEN_LINK"),
            "orphanPageCount": sum(1 for f in findings if f["type"] == "ORPHAN_PAGE"),
            "missingFrontmatterCount": sum(1 for f in findings if f["type"] == "MISSING_FRONTMATTER"),
            "missingSourceCount": sum(1 for f in findings if f["type"] == "MISSING_SOURCE"),
        }

        return {"summary": summary, "findings": findings}

    def _collect_pages(self) -> list[str]:
        pages: list[str] = []
        for d in SCAN_DIRS:
            pages.extend(self.vault.list_markdown_files(d))
        # also include top-level .md files
        for path in self.vault.root.glob("*.md"):
            relative = str(path.relative_to(self.vault.root)).replace("\\", "/")
            pages.append(relative)
        return sorted(pages)

    def _read_page(self, relative_path: str) -> str:
        try:
            return self.vault.read_vault_file(relative_path)
        except Exception:
            return ""

    def _parse_frontmatter(self, content: str) -> dict | None:
        m = FRONTMATTER_RE.match(content)
        if not m:
            return None
        raw = m.group(1)
        result: dict = {}
        for line in raw.split("\n"):
            line = line.strip()
            if ":" in line:
                key, _, val = line.partition(":")
                result[key.strip()] = val.strip()
        return result if result else None

    def _check_frontmatter(self, page: str, content: str, fm: dict | None) -> list[dict]:
        if fm is None:
            return [{
                "type": "MISSING_FRONTMATTER",
                "severity": "warning",
                "page": page,
                "detail": "页面缺少 YAML frontmatter",
            }]

        required = ["type", "created", "tags", "status"]
        missing = [k for k in required if k not in fm or not fm[k]]
        if missing:
            return [{
                "type": "MISSING_FRONTMATTER",
                "severity": "warning",
                "page": page,
                "detail": f"frontmatter 缺必填字段: {', '.join(missing)}",
            }]

        return []

    def _check_broken_links(self, page: str, content: str, wiki_targets: frozenset[str]) -> list[dict]:
        body = content
        m = FRONTMATTER_RE.match(content)
        if m:
            body = content[m.end():]

        links = set()
        for match in WIKILINK_RE.findall(body):
            target = match.strip()
            links.add(target)

        findings: list[dict] = []
        for link in sorted(links):
            candidate = f"wiki/{link}.md"
            if candidate not in wiki_targets:
                findings.append({
                    "type": "BROKEN_LINK",
                    "severity": "warning",
                    "page": page,
                    "detail": f"引用 [[{link}]] 指向不存在的页面",
                })
        return findings

    def _check_missing_source(self, page: str, content: str, fm: dict | None) -> list[dict]:
        if fm is None:
            return []

        status = fm.get("status", "")
        if status != "stable":
            return []

        source_file = fm.get("source_file", "")

        body = content
        m = FRONTMATTER_RE.match(content)
        if m:
            body = content[m.end():]

        has_inline_link = bool(WIKILINK_RE.search(body))

        if not source_file and not has_inline_link:
            return [{
                "type": "MISSING_SOURCE",
                "severity": "warning",
                "page": page,
                "detail": "stable 页面缺少来源引用：无 source_file 且内容中无 [[来源]] 链接",
            }]

        return []

    def _check_orphans(self, scan_pages: list[str], wiki_targets: frozenset[str]) -> list[dict]:
        wiki_scan_pages = [p for p in scan_pages if p.startswith("wiki/")]

        # build inbound link set
        inbound: dict[str, set[str]] = {}
        for page in wiki_scan_pages:
            content = self._read_page(page)
            body = content
            m = FRONTMATTER_RE.match(content)
            if m:
                body = content[m.end():]
            for match in WIKILINK_RE.findall(body):
                target = match.strip()
                candidate = f"wiki/{target}.md"
                inbound.setdefault(candidate, set()).add(page)

        findings: list[dict] = []
        for page in wiki_scan_pages:
            if page not in inbound:
                findings.append({
                    "type": "ORPHAN_PAGE",
                    "severity": "info",
                    "page": page,
                    "detail": "此页面未被任何其他 wiki 页面引用（孤页）",
                })

        return findings
