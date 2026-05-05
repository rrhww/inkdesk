from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile

from inkvault_server.core.config import Settings
from inkvault_server.models import Source, Topic, TopicClaim
from inkvault_server.time_utils import ensure_utc_datetime


AGENTS_MD = """# Inkvault LLM Wiki Agents

This vault follows the raw -> ingest -> wiki workflow.

- raw/ stores imported webpages, PDFs, and migrated internal notes.
- ingest is a review workflow, not a durable content directory.
- wiki/ stores accepted, settled knowledge pages.
- Never silently edit wiki knowledge without a review decision.
- Preserve backlinks from every compiled claim to raw source material.
"""

LIST_DELIMITER = "\n---\n"


@dataclass(frozen=True)
class VaultWriteResult:
    relative_path: str
    content_hash: str


class VaultService:
    def __init__(self, settings: Settings):
        self.root = Path(settings.vault_root).expanduser().resolve()

    def ensure_initialized(self) -> None:
        self.root.joinpath("raw").mkdir(parents=True, exist_ok=True)
        self.root.joinpath("wiki").mkdir(parents=True, exist_ok=True)
        agents = self.root / "AGENTS.md"
        if not agents.exists():
            self.write_vault_file("AGENTS.md", AGENTS_MD)

    def write_raw_source(self, imported_at: datetime, title: str, source_id: str, content: str) -> VaultWriteResult:
        file_name = f"{imported_at.astimezone(UTC):%Y-%m-%d}-{self.slugify(title)}-{self.compact_id(source_id)}.md"
        return self.write_vault_file(f"raw/{file_name}", content)

    def write_wiki_topic(self, slug: str, content: str) -> VaultWriteResult:
        return self.write_vault_file(self.wiki_path_for_slug(slug), content)

    def wiki_path_for_slug(self, slug: str) -> str:
        return f"wiki/{self.slugify(slug)}.md"

    def write_vault_file(self, relative_path: str, content: str) -> VaultWriteResult:
        normalized = self.normalize_relative_path(relative_path)
        target = self.resolve(normalized)
        target.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=target.parent, prefix=f".{target.name}.", suffix=".tmp") as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        temp_path.replace(target)
        return VaultWriteResult(relative_path=normalized, content_hash=self.content_hash(content))

    def read_vault_file(self, relative_path: str) -> str:
        return self.resolve(relative_path).read_text(encoding="utf-8")

    def list_markdown_files(self, directory: str) -> list[str]:
        directory_path = self.resolve(directory)
        if not directory_path.is_dir():
            return []
        return sorted(str(path.relative_to(self.root)).replace("\\", "/") for path in directory_path.glob("*.md"))

    def exists(self, relative_path: str) -> bool:
        return self.resolve(relative_path).exists()

    def content_hash(self, content: str) -> str:
        return sha256(content.encode("utf-8")).hexdigest()

    def resolve(self, relative_path: str) -> Path:
        normalized = self.normalize_relative_path(relative_path)
        resolved = self.root.joinpath(normalized).resolve()
        if not str(resolved).startswith(str(self.root)):
            raise ValueError(f"Vault path escapes root: {relative_path}")
        return resolved

    def normalize_relative_path(self, relative_path: str) -> str:
        if not relative_path or not relative_path.strip():
            raise ValueError("Vault path is required")
        normalized = relative_path.replace("\\", "/")
        while "//" in normalized:
            normalized = normalized.replace("//", "/")
        if normalized.startswith("/") or (len(normalized) > 2 and normalized[1:3] == ":/"):
            raise ValueError(f"Vault path must be relative: {relative_path}")
        return normalized

    def compact_id(self, value: str) -> str:
        normalized = "".join(char for char in (value or "") if char.isalnum())
        if not normalized:
            return "source"
        return normalized[:12]

    def slugify(self, value: str) -> str:
        raw = (value or "").strip().lower()
        result = []
        previous_dash = False
        for char in raw:
            if char.isalnum() or ("\u4e00" <= char <= "\u9fff"):
                result.append(char)
                previous_dash = False
            elif not previous_dash:
                result.append("-")
                previous_dash = True
        slug = "".join(result).strip("-")
        return slug or "untitled"


class VaultMarkdownService:
    def render_raw_source(self, source: Source, imported_at: datetime) -> str:
        locator = self.escape(source.locator)
        return f"""---
inkvaultType: raw
sourceId: {source.id}
kind: {source.kind}
status: {source.status}
title: "{self.escape(source.title)}"
locator: "{locator}"
importedAt: {imported_at.astimezone(UTC).isoformat().replace("+00:00", "Z")}
---

# {source.title}

## Excerpt
{self.blank_to_fallback(source.excerpt, "No excerpt captured.")}

## Body
{self.blank_to_fallback(source.body, source.excerpt)}
"""

    def render_wiki_topic(self, topic: Topic, claims: list[TopicClaim]) -> str:
        current_understanding = self.split_segments(topic.current_understanding)
        open_questions = self.split_segments(topic.open_questions)

        lines = [
            "---",
            "inkvaultType: wiki",
            f"topicId: {topic.id}",
            f"slug: {topic.slug}",
            f'title: "{self.escape(topic.title)}"',
            f"updatedAt: {ensure_utc_datetime(topic.updated_at).isoformat().replace('+00:00', 'Z')}",
            "---",
            "",
            f"# {topic.title}",
            "",
            "## Current Understanding",
        ]
        lines.extend(self.bullets(current_understanding, "Waiting for accepted ingest proposals."))
        lines.extend(["", "## Key Claims"])
        if claims:
            for claim in claims:
                if claim.source and claim.source.vault_path:
                    lines.append(f"- {claim.statement} ([{claim.citation_label}](../{claim.source.vault_path.replace('\\', '/')}))")
                else:
                    lines.append(f"- {claim.statement} ({claim.citation_label})")
        else:
            lines.append("- No accepted claims yet.")
        lines.extend(["", "## Open Questions"])
        lines.extend(self.bullets(open_questions, "Waiting for accepted ingest proposals."))
        lines.extend(["", "## Sources"])
        sources = sorted(topic.sources, key=lambda item: ensure_utc_datetime(item.updated_at), reverse=True)
        if sources:
            for source in sources:
                entry = f"- [{source.title}](../{source.vault_path.replace('\\', '/')})" if source.vault_path else f"- {source.title}"
                if source.locator:
                    entry += f" - {source.locator}"
                lines.append(entry)
        else:
            lines.append("- No linked sources yet.")
        lines.extend(["", "## Related", "- Add related wiki pages after future ingest reviews.", ""])
        return "\n".join(lines)

    def split_segments(self, value: str | None) -> list[str]:
        if not value or not value.strip():
            return []
        return [segment.strip() for segment in value.split(LIST_DELIMITER) if segment.strip()]

    def bullets(self, items: list[str], fallback: str) -> list[str]:
        return [f"- {item}" for item in items] if items else [f"- {fallback}"]

    def escape(self, value: str | None) -> str:
        return (value or "").replace("\\", "\\\\").replace('"', '\\"')

    def blank_to_fallback(self, value: str | None, fallback: str | None) -> str:
        return value.strip() if value and value.strip() else (fallback or "")
