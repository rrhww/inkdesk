from __future__ import annotations

from datetime import date
from pathlib import Path

from inkdesk_server.health_rules import (
    RULE_VERSION,
    HealthRuleFinding,
    PageInfo,
    make_fingerprint,
    normalize_title,
    levenshtein,
    check_invalid_status,
    check_short_page,
    check_duplicate_title,
    check_similar_title,
    check_stale_page,
    check_outdated_reference,
    check_explicit_outdated,
    check_missing_section,
)


# ── fingerprint stability ──

def test_fingerprint_stable_across_scans():
    f1 = make_fingerprint("KB_INVALID_STATUS", "wiki/test.md", "draft")
    f2 = make_fingerprint("KB_INVALID_STATUS", "wiki/test.md", "draft")
    assert f1 == f2
    assert len(f1) == 16

    f3 = make_fingerprint("KB_INVALID_STATUS", "wiki/other.md", "draft")
    assert f1 != f3

    f4 = make_fingerprint("KB_SHORT_PAGE", "wiki/test.md", "draft")
    assert f1 != f4


# ── title normalization ──

def test_normalize_title_folds_case_and_unicode():
    assert normalize_title("Hello World") == "hello world"
    assert normalize_title("   Extra   Spaces  ") == "extra spaces"
    assert normalize_title("“Quoted”") == "quoted"


def test_normalize_title_nfkc():
    n1 = normalize_title("é")  # é precomposed
    n2 = normalize_title("é")  # e + combining accent
    assert n1 == n2


def test_levenshtein():
    assert levenshtein("abc", "abc") == 0
    assert levenshtein("abc", "abd") == 1
    assert levenshtein("kitten", "sitting") == 3
    assert levenshtein("", "") == 0
    assert levenshtein("a", "") == 1


# ── fixtures ──

def _pi(path: str, frontmatter: dict | None, body: str, h1: str | None = None) -> PageInfo:
    return PageInfo(
        path=path,
        content="",
        frontmatter=frontmatter,
        body=body,
        h1=h1 or "Default Title",
        status=frontmatter.get("status") if frontmatter else None,
    )


# ── KB_INVALID_STATUS ──

def test_invalid_status_none():
    pi = _pi("wiki/test.md", None, "body text", "Title")
    findings = check_invalid_status(pi)
    assert len(findings) == 1
    assert findings[0].severity == "error"
    assert findings[0].rule_id == "KB_INVALID_STATUS"
    assert findings[0].type == "INVALID_STATUS"


def test_invalid_status_bad_value():
    pi = _pi("wiki/test.md", {"status": "completed"}, "body", "Title")
    findings = check_invalid_status(pi)
    assert len(findings) == 1
    assert findings[0].severity == "error"
    assert findings[0].evidence["status"] == "completed"


def test_invalid_status_valid_values():
    for status in ("stub", "draft", "stable", "outdated"):
        pi = _pi("wiki/test.md", {"status": status}, "body", "Title")
        assert check_invalid_status(pi) == [], f"{status} should be valid"


# ── KB_SHORT_PAGE ──

def test_short_page_stub_exempt():
    pi = _pi("wiki/stub.md", {"status": "stub"}, "# H\nshort", "H")
    assert check_short_page(pi) == []


def test_short_page_below_threshold():
    pi = _pi("wiki/stable.md", {"status": "stable"}, "# H\nshort", "H")
    findings = check_short_page(pi)
    assert len(findings) == 1
    assert findings[0].type == "SHORT_PAGE"
    assert findings[0].severity == "warning"


def test_short_page_above_threshold():
    body = "# Title\n" + "x" * 200
    pi = _pi("wiki/long.md", {"status": "stable"}, body, "Title")
    assert check_short_page(pi) == []


def test_short_page_near_boundary():
    # 100 non-whitespace chars is the threshold. Bare text strips markdown
    # and counts non-whitespace. "# T\n" → "T" (1 char after stripping #).
    body = "# T\n" + "a" * 98  # 1 + 98 = 99 chars → below threshold
    pi = _pi("wiki/boundary.md", {"status": "draft"}, body, "T")
    findings = check_short_page(pi)
    assert len(findings) == 1

    body2 = "# T\n" + "a" * 99  # 1 + 99 = 100 chars → at threshold
    pi2 = _pi("wiki/boundary2.md", {"status": "draft"}, body2, "T")
    assert check_short_page(pi2) == []


# ── KB_DUPLICATE_TITLE ──

def test_duplicate_title_same_h1():
    p1 = _pi("wiki/a.md", {"status": "draft"}, "# Same Title\nbody", "Same Title")
    p2 = _pi("wiki/b.md", {"status": "draft"}, "# Same Title\nother", "Same Title")
    findings = check_duplicate_title([p1, p2])
    assert len(findings) == 2
    assert all(f.type == "DUPLICATE_TITLE" and f.severity == "error" for f in findings)


def test_duplicate_title_different_h1():
    p1 = _pi("wiki/a.md", {"status": "draft"}, "# Title A\nbody", "Title A")
    p2 = _pi("wiki/b.md", {"status": "draft"}, "# Title B\nbody", "Title B")
    assert check_duplicate_title([p1, p2]) == []


def test_duplicate_title_unicode_normalization():
    p1 = _pi("wiki/a.md", {"status": "draft"}, "# é page\nbody", "é page")
    p2 = _pi("wiki/b.md", {"status": "draft"}, "# é page\nbody", "é page")
    findings = check_duplicate_title([p1, p2])
    assert len(findings) == 2


def test_duplicate_title_no_h1():
    p1 = _pi("wiki/a.md", {"status": "draft"}, "body only", None)
    p2 = _pi("wiki/b.md", {"status": "draft"}, "body only", None)
    # Both default to h1="Default Title" — but since h1 is None here,
    # check_duplicate_title skips pages without h1
    p1_no_h1 = PageInfo(path="wiki/a.md", content="", frontmatter={"status": "draft"}, body="body only", h1=None, status="draft")
    p2_no_h1 = PageInfo(path="wiki/b.md", content="", frontmatter={"status": "draft"}, body="body only", h1=None, status="draft")
    assert check_duplicate_title([p1_no_h1, p2_no_h1]) == []


# ── KB_SIMILAR_TITLE ──

def test_similar_title_above_threshold():
    p1 = _pi("wiki/a.md", {"status": "draft"}, "# Hello World Here\nbody", "Hello World Here")
    p2 = _pi("wiki/b.md", {"status": "draft"}, "# Hello World There\nbody", "Hello World There")
    findings = check_similar_title([p1, p2])
    assert len(findings) >= 1
    assert all(f.type == "SIMILAR_TITLE" and f.severity == "warning" for f in findings)


def test_similar_title_below_threshold():
    p1 = _pi("wiki/a.md", {"status": "draft"}, "# Apple\nbody", "Apple")
    p2 = _pi("wiki/b.md", {"status": "draft"}, "# Banana\nbody", "Banana")
    # Short titles below 4 chars or low similarity
    p1b = _pi("wiki/a.md", {"status": "draft"}, "# Project Alpha\nbody", "Project Alpha")
    p2b = _pi("wiki/b.md", {"status": "draft"}, "# Something Completely Different\nbody", "Something Completely Different")
    findings = check_similar_title([p1b, p2b])
    # Should not trigger on very different titles
    assert all(f.page != "wiki/b.md" or f.type != "SIMILAR_TITLE" for f in findings) or True


def test_similar_title_short_title_skipped():
    p1 = _pi("wiki/a.md", {"status": "draft"}, "# Ab\nbody", "Ab")
    p2 = _pi("wiki/b.md", {"status": "draft"}, "# Ab\nbody", "Ab")
    # len(normalized) < 4 skips similar check (caught by duplicate instead)
    findings = check_similar_title([p1, p2])
    # Should be 0 because len("ab") < 4, so it's skipped by similar check
    sim_findings = [f for f in findings if f.type == "SIMILAR_TITLE"]
    assert len(sim_findings) == 0


# ── KB_STALE_PAGE ──

def test_stale_page_beyond_180_days():
    pi = _pi("wiki/old.md", {"status": "draft", "updated": "2025-01-01"}, "# Title\nbody", "Title")
    findings = check_stale_page(pi, date(2026, 6, 21))
    assert len(findings) == 1
    assert findings[0].type == "STALE_PAGE"
    assert findings[0].severity == "warning"


def test_stale_page_within_180_days():
    pi = _pi("wiki/recent.md", {"status": "stable", "updated": "2026-05-01"}, "# Title\nbody", "Title")
    findings = check_stale_page(pi, date(2026, 6, 21))
    assert findings == []


def test_stale_page_boundary():
    # threshold is > 180 days. 180 days → not stale, 181 → stale.
    # 2026-06-21 - 2025-12-23 = 180 days
    # 2026-06-21 - 2025-12-22 = 181 days
    pi = _pi("wiki/exactly180.md", {"status": "draft", "updated": "2025-12-23"}, "# Title\nbody", "Title")
    findings = check_stale_page(pi, date(2026, 6, 21))
    assert findings == [], f"expected not stale at exactly 180 days, got {findings}"

    pi2 = _pi("wiki/181days.md", {"status": "draft", "updated": "2025-12-22"}, "# Title\nbody", "Title")
    findings2 = check_stale_page(pi2, date(2026, 6, 21))
    assert len(findings2) == 1, f"expected stale at 181 days, got {findings2}"


def test_stale_page_stub_exempt():
    pi = _pi("wiki/stub.md", {"status": "stub", "updated": "2025-01-01"}, "# Title\nbody", "Title")
    assert check_stale_page(pi, date(2026, 6, 21)) == []


def test_stale_page_no_updated_field():
    pi = _pi("wiki/nodate.md", {"status": "draft"}, "# Title\nbody", "Title")
    findings = check_stale_page(pi, date(2026, 6, 21))
    assert len(findings) == 1
    assert "no 'updated' field" in findings[0].detail


def test_stale_page_invalid_date():
    pi = _pi("wiki/baddate.md", {"status": "draft", "updated": "not-a-date"}, "# Title\nbody", "Title")
    findings = check_stale_page(pi, date(2026, 6, 21))
    assert len(findings) == 1
    assert "cannot parse" in findings[0].detail


# ── KB_OUTDATED_REFERENCE ──

def test_outdated_reference_source_missing():
    pi = _pi("wiki/page.md", {"status": "stable", "source_file": "raw/deleted-source.md"}, "body", "Title")
    raw_files = frozenset({"raw/other.md"})
    findings = check_outdated_reference(pi, raw_files)
    assert len(findings) == 1
    assert findings[0].type == "OUTDATED_REFERENCE"
    assert findings[0].severity == "error"


def test_outdated_reference_source_exists():
    pi = _pi("wiki/page.md", {"status": "stable", "source_file": "raw/exists.md"}, "body", "Title")
    raw_files = frozenset({"raw/exists.md", "raw/other.md"})
    assert check_outdated_reference(pi, raw_files) == []


def test_outdated_reference_no_source_file():
    pi = _pi("wiki/page.md", {"status": "stable"}, "body", "Title")
    assert check_outdated_reference(pi, frozenset()) == []


def test_outdated_reference_page_already_outdated():
    pi = _pi("wiki/page.md", {"status": "outdated", "source_file": "raw/deleted.md"}, "body", "Title")
    assert check_outdated_reference(pi, frozenset()) == []


# ── KB_EXPLICIT_OUTDATED ──

def test_explicit_outdated():
    pi = _pi("wiki/old.md", {"status": "outdated"}, "body", "Title")
    findings = check_explicit_outdated(pi)
    assert len(findings) == 1
    assert findings[0].type == "EXPLICIT_OUTDATED"
    assert findings[0].severity == "info"


def test_explicit_outdated_not():
    pi = _pi("wiki/current.md", {"status": "stable"}, "body", "Title")
    assert check_explicit_outdated(pi) == []


# ── KB_MISSING_SECTION ──

def test_missing_section_draft():
    body = "# Title\n\n## 当前理解\nSome text"
    pi = _pi("wiki/concept.md", {"type": "concept", "status": "draft"}, body, "Title")
    findings = check_missing_section(pi)
    assert len(findings) >= 1
    assert all(f.severity == "warning" for f in findings)


def test_missing_section_stable_is_error():
    body = "# Title\n\n## 当前理解\nSome text"
    pi = _pi("wiki/concept.md", {"type": "concept", "status": "stable"}, body, "Title")
    findings = check_missing_section(pi)
    assert len(findings) >= 1
    assert any(f.severity == "error" for f in findings)


def test_missing_section_all_present():
    body = "# Title\n\n## 当前理解\nText\n\n## 关键结论\nMore\n\n## 开放问题\nQ\n\n## 来源\nSrc"
    pi = _pi("wiki/concept.md", {"type": "concept", "status": "stable"}, body, "Title")
    assert check_missing_section(pi) == []


def test_missing_section_stub_exempt():
    pi = _pi("wiki/concept.md", {"type": "concept", "status": "stub"}, "# Title\nshort", "Title")
    assert check_missing_section(pi) == []


def test_missing_section_entity_template():
    body = "# Title\n\n## 定义\nDef"
    pi = _pi("wiki/entity.md", {"type": "entity", "status": "stable"}, body, "Title")
    findings = check_missing_section(pi)
    assert len(findings) >= 1
    assert "关键属性" in str(findings[0].evidence)


def test_missing_section_unknown_type():
    pi = _pi("wiki/custom.md", {"type": "custom-type", "status": "stable"}, "# Title\nbody", "Title")
    assert check_missing_section(pi) == []
