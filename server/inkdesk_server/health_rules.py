"""
Health rules module — versioned, deterministic rule definitions.

Every rule is a pure function: same vault + same rule version + same evaluatedAt
→ same findings with stable fingerprints.

No LLM calls, no network access, no Vault mutation.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable

RULE_VERSION = "1.0.0"

# ── Severity ──

ERROR = "error"
WARNING = "warning"
INFO = "info"

VALID_STATUSES = frozenset({"stub", "draft", "stable", "outdated"})

# ── Finding ──


@dataclass(frozen=True)
class HealthRuleFinding:
    rule_id: str
    type: str
    severity: str
    page: str
    detail: str
    evidence: dict = field(default_factory=dict)
    fingerprint: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "severity": self.severity,
            "page": self.page,
            "detail": self.detail,
            "ruleId": self.rule_id,
            "evidence": self.evidence,
            "fingerprint": self.fingerprint,
        }


# ── Fingerprint ──


def make_fingerprint(rule_id: str, page: str, key_evidence: str = "") -> str:
    """Stable fingerprint: rule + normalized page path + key evidence."""
    raw = f"{rule_id}|{page}|{key_evidence}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ── Title normalization ──


def normalize_title(title: str) -> str:
    """NFKC + case fold + collapse whitespace + strip common punctuation."""
    t = unicodedata.normalize("NFKC", title)
    t = t.casefold()
    t = re.sub(r"[“”""''「」『』【】《》〈〉]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def levenshtein(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


# ── Rule signature ──

RuleFn = Callable[..., list[HealthRuleFinding]]


@dataclass
class RuleDef:
    rule_id: str
    severity: str
    description: str


# ── Page model for rules ──


@dataclass
class PageInfo:
    path: str
    content: str
    frontmatter: dict | None
    body: str  # content without frontmatter
    h1: str | None  # first H1 heading
    status: str | None  # from frontmatter


# ── helpers ──


def _parse_frontmatter(content: str) -> dict | None:
    m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
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


def _extract_body(content: str) -> str:
    m = re.match(r"^---\s*\n.*?\n---\n?", content, re.DOTALL)
    if m:
        return content[m.end():]
    return content


def _extract_h1(body: str) -> str | None:
    m = re.search(r"^#\s+(.+)", body, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def _bare_text_length(body: str) -> int:
    """Count non-whitespace chars after stripping markdown syntax."""
    cleaned = re.sub(r"[#*_`~>\-\|\!\[\]\(\)]", "", body)
    cleaned = re.sub(r"\s+", "", cleaned)
    return len(cleaned)


def _get_template_required_headings(page_type: str | None) -> set[str]:
    """Return required heading names for a given page type template."""
    templates: dict[str | None, set[str]] = {
        "concept": {"当前理解", "关键结论", "开放问题", "来源"},
        "entity": {"定义", "关键属性", "关联实体", "来源"},
        "source": {"摘要", "关键要点", "与知识库的关联"},
        "query": {"问题", "回答", "引用来源"},
    }
    return templates.get(page_type, set())


# ── Rule implementations ──


def check_invalid_status(page: PageInfo) -> list[HealthRuleFinding]:
    rule_id = "KB_INVALID_STATUS"
    fm = page.frontmatter
    if fm is None:
        status_raw = None
    else:
        status_raw = fm.get("status", "").strip()
    if not status_raw:
        return [HealthRuleFinding(
            rule_id=rule_id,
            type="INVALID_STATUS",
            severity=ERROR,
            page=page.path,
            detail="page status is missing",
            evidence={"status": None},
            fingerprint=make_fingerprint(rule_id, page.path),
        )]
    if status_raw not in VALID_STATUSES:
        return [HealthRuleFinding(
            rule_id=rule_id,
            type="INVALID_STATUS",
            severity=ERROR,
            page=page.path,
            detail=f"invalid status '{status_raw}'; must be one of stub/draft/stable/outdated",
            evidence={"status": status_raw},
            fingerprint=make_fingerprint(rule_id, page.path, status_raw),
        )]
    return []


def check_short_page(page: PageInfo, min_chars: int = 100) -> list[HealthRuleFinding]:
    rule_id = "KB_SHORT_PAGE"
    status = page.status
    if status == "stub":
        return []
    if status is None:
        # treated separately by KB_INVALID_STATUS
        return []
    length = _bare_text_length(page.body)
    if length < min_chars:
        return [HealthRuleFinding(
            rule_id=rule_id,
            type="SHORT_PAGE",
            severity=WARNING,
            page=page.path,
            detail=f"body content ({length} non-whitespace chars) below minimum ({min_chars})",
            evidence={"charCount": length, "threshold": min_chars, "status": status},
            fingerprint=make_fingerprint(rule_id, page.path),
        )]
    return []


def check_duplicate_title(pages: list[PageInfo]) -> list[HealthRuleFinding]:
    rule_id = "KB_DUPLICATE_TITLE"
    findings: list[HealthRuleFinding] = []
    title_map: dict[str, list[PageInfo]] = {}
    for p in pages:
        if p.h1:
            norm = normalize_title(p.h1)
            title_map.setdefault(norm, []).append(p)
    for norm_title, group in title_map.items():
        if len(group) > 1:
            for p in sorted(group, key=lambda x: x.path):
                others = sorted([o.path for o in group if o.path != p.path])
                findings.append(HealthRuleFinding(
                    rule_id=rule_id,
                    type="DUPLICATE_TITLE",
                    severity=ERROR,
                    page=p.path,
                    detail=f"duplicate H1 title '{p.h1}' also found in: {', '.join(others)}",
                    evidence={"h1": p.h1, "normalized": norm_title, "duplicates": others},
                    fingerprint=make_fingerprint(rule_id, p.path, norm_title),
                ))
    return findings


def check_similar_title(pages: list[PageInfo], threshold: float = 0.90) -> list[HealthRuleFinding]:
    rule_id = "KB_SIMILAR_TITLE"
    findings: list[HealthRuleFinding] = []
    infos: list[tuple[str, str, float]] = []  # (page_a, page_b, ratio)
    for i, pa in enumerate(pages):
        if not pa.h1:
            continue
        na = normalize_title(pa.h1)
        if len(na) < 4:
            continue
        for pb in pages[i + 1:]:
            if not pb.h1:
                continue
            nb = normalize_title(pb.h1)
            if len(nb) < 4:
                continue
            if na == nb:
                continue  # duplicate, not similar
            max_len = max(len(na), len(nb))
            dist = levenshtein(na, nb)
            ratio = 1 - dist / max_len
            if ratio >= threshold:
                infos.append((pa.path, pb.path, round(ratio, 3)))
    for path_a, path_b, ratio in infos:
        findings.append(HealthRuleFinding(
            rule_id=rule_id,
            type="SIMILAR_TITLE",
            severity=WARNING,
            page=path_a,
            detail=f"title similar to '{path_b}' (similarity {ratio})",
            evidence={"similarTo": path_b, "similarity": ratio, "threshold": threshold},
            fingerprint=make_fingerprint(rule_id, f"{path_a}|{path_b}"),
        ))
    return findings


def check_stale_page(page: PageInfo, evaluated_at: date, max_days: int = 180) -> list[HealthRuleFinding]:
    rule_id = "KB_STALE_PAGE"
    status = page.status
    if status not in ("draft", "stable"):
        return []
    fm = page.frontmatter
    if fm is None:
        return []
    updated_str = fm.get("updated", "").strip()
    if not updated_str:
        return [HealthRuleFinding(
            rule_id=rule_id,
            type="STALE_PAGE",
            severity=WARNING,
            page=page.path,
            detail="draft/stable page has no 'updated' field",
            evidence={"status": status},
            fingerprint=make_fingerprint(rule_id, page.path),
        )]
    try:
        updated = date.fromisoformat(updated_str[:10])
    except ValueError:
        return [HealthRuleFinding(
            rule_id=rule_id,
            type="STALE_PAGE",
            severity=WARNING,
            page=page.path,
            detail=f"cannot parse 'updated' date: {updated_str}",
            evidence={"updated": updated_str, "status": status},
            fingerprint=make_fingerprint(rule_id, page.path, updated_str),
        )]
    days = (evaluated_at - updated).days
    if days > max_days:
        return [HealthRuleFinding(
            rule_id=rule_id,
            type="STALE_PAGE",
            severity=WARNING,
            page=page.path,
            detail=f"last updated {days} days ago (threshold {max_days})",
            evidence={"updated": updated_str, "daysSinceUpdate": days, "threshold": max_days},
            fingerprint=make_fingerprint(rule_id, page.path, updated_str),
        )]
    return []


def check_outdated_reference(page: PageInfo, raw_files: frozenset[str]) -> list[HealthRuleFinding]:
    rule_id = "KB_OUTDATED_REFERENCE"
    status = page.status
    if status == "outdated":
        return []  # already marked, KB_EXPLICIT_OUTDATED handles it
    fm = page.frontmatter
    if fm is None:
        return []
    source_file = fm.get("source_file", "").strip()
    if source_file and source_file not in raw_files:
        return [HealthRuleFinding(
            rule_id=rule_id,
            type="OUTDATED_REFERENCE",
            severity=ERROR,
            page=page.path,
            detail=f"source_file '{source_file}' not found in raw/; page not marked outdated",
            evidence={"source_file": source_file, "pageStatus": status},
            fingerprint=make_fingerprint(rule_id, page.path, source_file),
        )]
    return []


def check_explicit_outdated(page: PageInfo) -> list[HealthRuleFinding]:
    rule_id = "KB_EXPLICIT_OUTDATED"
    if page.status == "outdated":
        return [HealthRuleFinding(
            rule_id=rule_id,
            type="EXPLICIT_OUTDATED",
            severity=INFO,
            page=page.path,
            detail="page explicitly marked as outdated",
            evidence={"status": "outdated"},
            fingerprint=make_fingerprint(rule_id, page.path),
        )]
    return []


def check_missing_section(page: PageInfo) -> list[HealthRuleFinding]:
    rule_id = "KB_MISSING_SECTION"
    status = page.status
    if status not in ("draft", "stable"):
        return []
    fm = page.frontmatter
    if fm is None:
        return []
    page_type = fm.get("type", "").strip()
    required = _get_template_required_headings(page_type if page_type else None)
    if not required:
        return []  # unknown type, no template to check against
    body_headings = set()
    for m in re.finditer(r"^#{2,3}\s+(.+)", page.body, re.MULTILINE):
        body_headings.add(m.group(1).strip())
    missing = required - body_headings
    if missing:
        sev = ERROR if status == "stable" else WARNING
        return [HealthRuleFinding(
            rule_id=rule_id,
            type="MISSING_SECTION",
            severity=sev,
            page=page.path,
            detail=f"missing template sections for {page_type}: {', '.join(sorted(missing))}",
            evidence={"pageType": page_type, "required": sorted(required), "missing": sorted(missing), "status": status},
            fingerprint=make_fingerprint(rule_id, page.path),
        )]
    return []


# ── Rule registry ──

ALL_RULES: list[RuleDef] = [
    RuleDef("KB_INVALID_STATUS", ERROR, "Invalid or missing page status"),
    RuleDef("KB_SHORT_PAGE", WARNING, "Page body too short (non-stub)"),
    RuleDef("KB_DUPLICATE_TITLE", ERROR, "Duplicate H1 title"),
    RuleDef("KB_SIMILAR_TITLE", WARNING, "Highly similar H1 title"),
    RuleDef("KB_STALE_PAGE", WARNING, "Draft/stable page not recently updated"),
    RuleDef("KB_OUTDATED_REFERENCE", ERROR, "Source file missing, page not marked outdated"),
    RuleDef("KB_EXPLICIT_OUTDATED", INFO, "Page explicitly marked outdated"),
    RuleDef("KB_MISSING_SECTION", WARNING, "Missing required template sections"),
]
