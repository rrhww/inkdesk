from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from inkdesk_server.core.config import Settings
from inkdesk_server.health_rules import (
    RULE_VERSION,
    VALID_STATUSES,
    HealthRuleFinding,
    PageInfo,
    RuleDef,
    _parse_frontmatter,
    _extract_body,
    _extract_h1,
    _bare_text_length,
    check_invalid_status,
    check_short_page,
    check_duplicate_title,
    check_similar_title,
    check_stale_page,
    check_outdated_reference,
    check_explicit_outdated,
    check_missing_section,
    make_fingerprint,
    normalize_title,
    levenshtein,
)
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

    def scan(self, evaluated_at: date | None = None) -> dict:
        """Execute a complete deterministic health scan."""
        t0 = time.monotonic()
        if evaluated_at is None:
            evaluated_at = date.today()

        all_pages = self._collect_pages()
        scan_pages = [p for p in all_pages if p not in EXEMPT_PAGES]
        wiki_targets = frozenset(p for p in all_pages if p.startswith("wiki/"))
        raw_files = frozenset(p for p in all_pages if p.startswith("raw/"))

        # Build PageInfo for each scannable page
        page_infos: list[PageInfo] = []
        for page in scan_pages:
            content = self._read_page(page)
            fm = _parse_frontmatter(content)
            body = _extract_body(content)
            h1 = _extract_h1(body)
            status = fm.get("status", "").strip() if fm else None
            page_infos.append(PageInfo(
                path=page, content=content, frontmatter=fm,
                body=body, h1=h1, status=status,
            ))

        findings: list[dict] = []

        # Legacy checks (4.1.2 compatible)
        for page in scan_pages:
            content = self._read_page(page)
            fm = self._parse_frontmatter_legacy(content)
            findings.extend(self._check_frontmatter(page, content, fm))
            findings.extend(self._check_broken_links(page, content, wiki_targets))
            findings.extend(self._check_missing_source(page, content, fm))

        # Legacy orphan check
        findings.extend(self._check_orphans(scan_pages, wiki_targets))

        # New deep rules (per-page)
        for pi in page_infos:
            findings.extend(f.to_dict() for f in check_invalid_status(pi))
            findings.extend(f.to_dict() for f in check_short_page(pi))
            findings.extend(f.to_dict() for f in check_stale_page(pi, evaluated_at))
            findings.extend(f.to_dict() for f in check_outdated_reference(pi, raw_files))
            findings.extend(f.to_dict() for f in check_explicit_outdated(pi))
            findings.extend(f.to_dict() for f in check_missing_section(pi))

        # Multi-page rules
        findings.extend(f.to_dict() for f in check_duplicate_title(page_infos))
        findings.extend(f.to_dict() for f in check_similar_title(page_infos))

        # Compute score and gate
        score_result = self._compute_score(findings, scan_pages)
        duration_ms = int((time.monotonic() - t0) * 1000)

        summary = {
            "totalPages": len(scan_pages),
            "brokenLinkCount": sum(1 for f in findings if f["type"] == "BROKEN_LINK"),
            "orphanPageCount": sum(1 for f in findings if f["type"] == "ORPHAN_PAGE"),
            "missingFrontmatterCount": sum(1 for f in findings if f["type"] == "MISSING_FRONTMATTER"),
            "missingSourceCount": sum(1 for f in findings if f["type"] == "MISSING_SOURCE"),
        }

        errors = sum(1 for f in findings if f["severity"] == "error")
        warnings = sum(1 for f in findings if f["severity"] == "warning")
        infos = sum(1 for f in findings if f["severity"] == "info")
        gate = "FAILED" if errors > 0 else "PASSED"

        return {
            "summary": summary,
            "findings": findings,
            "ruleVersion": RULE_VERSION,
            "healthScore": score_result[0],
            "gateStatus": gate,
            "categoryCounts": {"error": errors, "warning": warnings, "info": infos},
            "notApplicable": score_result[1],
            "durationMs": duration_ms,
            "evaluatedAt": evaluated_at.isoformat(),
        }

    def _compute_score(self, findings: list[dict], scan_pages: list[str]) -> tuple[float | None, bool]:
        """
        Score = (passed applicable checks / total applicable checks) * 100.
        A "check" is a rule applied to a page.
        When no rules are applicable, return (None, True).
        """
        rule_defs = {
            "MISSING_FRONTMATTER": "warning",
            "BROKEN_LINK": "warning",
            "ORPHAN_PAGE": "info",
            "MISSING_SOURCE": "warning",
            "INVALID_STATUS": "error",
            "SHORT_PAGE": "warning",
            "DUPLICATE_TITLE": "error",
            "SIMILAR_TITLE": "warning",
            "STALE_PAGE": "warning",
            "OUTDATED_REFERENCE": "error",
            "EXPLICIT_OUTDATED": "info",
            "MISSING_SECTION": "warning",
        }

        # Count applicable checks: for each page, which rules hit it
        # Simpler approach: total checks = pages * rule_count for page-level rules,
        # but we don't know which pages have each rule applied.
        # Better approach from the plan: count failed + passed.
        # We'll use a practical heuristic:
        failed_by_rule_page: set[tuple[str, str]] = set()
        for f in findings:
            failed_by_rule_page.add((f["type"], f["page"]))

        # Total applicable = one check per (rule, page) where the rule applies
        # Per-page rules: MISSING_FRONTMATTER, INVALID_STATUS, SHORT_PAGE, MISSING_SOURCE,
        #   STALE_PAGE, OUTDATED_REFERENCE, EXPLICIT_OUTDATED, MISSING_SECTION
        # Multi-page rules: BROKEN_LINK, ORPHAN_PAGE, DUPLICATE_TITLE, SIMILAR_TITLE
        applicable = 0

        # Per-page rules apply to every scanned page
        per_page_rules = [
            "MISSING_FRONTMATTER", "INVALID_STATUS", "SHORT_PAGE",
            "MISSING_SOURCE", "STALE_PAGE", "OUTDATED_REFERENCE",
            "EXPLICIT_OUTDATED", "MISSING_SECTION",
        ]
        applicable += len(scan_pages) * len(per_page_rules)

        # BROKEN_LINK applies per-page (each page can have links)
        applicable += len(scan_pages)

        # ORPHAN_PAGE applies per wiki page
        wiki_pages = [p for p in scan_pages if p.startswith("wiki/")]
        applicable += len(wiki_pages)

        # DUPLICATE_TITLE and SIMILAR_TITLE are cross-page; practical: count one per page
        applicable += len(scan_pages) * 2

        failed = len(failed_by_rule_page)
        passed = max(0, applicable - failed)

        if applicable == 0:
            return (None, True)

        return (round(passed / applicable * 100, 1), False)

    def _collect_pages(self) -> list[str]:
        pages: list[str] = []
        for d in SCAN_DIRS:
            pages.extend(self._list_recursive(d))
        for path in self.vault.root.glob("*.md"):
            relative = str(path.relative_to(self.vault.root)).replace("\\", "/")
            pages.append(relative)
        return sorted(pages)

    def _list_recursive(self, directory: str) -> list[str]:
        """Recursively list all .md files in a directory."""
        directory_path = self.vault.resolve(directory)
        if not directory_path.is_dir():
            return []
        results: list[str] = []
        for path in directory_path.rglob("*.md"):
            relative = str(path.relative_to(self.vault.root)).replace("\\", "/")
            results.append(relative)
        return results

    def _read_page(self, relative_path: str) -> str:
        try:
            return self.vault.read_vault_file(relative_path)
        except Exception:
            return ""

    def _parse_frontmatter_legacy(self, content: str) -> dict | None:
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
                "ruleId": "KB_MISSING_FRONTMATTER",
                "fingerprint": make_fingerprint("KB_MISSING_FRONTMATTER", page),
            }]
        required = ["type", "created", "tags", "status"]
        missing = [k for k in required if k not in fm or not fm[k]]
        if missing:
            return [{
                "type": "MISSING_FRONTMATTER",
                "severity": "warning",
                "page": page,
                "detail": f"frontmatter 缺必填字段: {', '.join(missing)}",
                "ruleId": "KB_MISSING_FRONTMATTER",
                "evidence": {"missing": missing},
                "fingerprint": make_fingerprint("KB_MISSING_FRONTMATTER", page),
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
                    "ruleId": "KB_BROKEN_LINK",
                    "evidence": {"target": link, "candidate": candidate},
                    "fingerprint": make_fingerprint("KB_BROKEN_LINK", page, link),
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
                "ruleId": "KB_MISSING_SOURCE",
                "fingerprint": make_fingerprint("KB_MISSING_SOURCE", page),
            }]
        return []

    def _check_orphans(self, scan_pages: list[str], wiki_targets: frozenset[str]) -> list[dict]:
        wiki_scan_pages = [p for p in scan_pages if p.startswith("wiki/")]
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
                    "ruleId": "KB_ORPHAN_PAGE",
                    "fingerprint": make_fingerprint("KB_ORPHAN_PAGE", page),
                })
        return findings
