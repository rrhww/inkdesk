from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile

from inkdesk_server.core.config import Settings
from inkdesk_server.models import Source, Topic, TopicClaim
from inkdesk_server.time_utils import ensure_utc_datetime
from inkdesk_server.vault_assets import SHARED_DIRS, SHARED_FILES, VAULT_TYPE_WIKI_DIRS


LIST_DELIMITER = "\n---\n"


@dataclass(frozen=True)
class VaultWriteResult:
    relative_path: str
    content_hash: str


class VaultService:
    def __init__(self, settings: Settings):
        self.root = Path(settings.vault_root).expanduser().resolve()

    def ensure_initialized(self, vault_type: str | None = None) -> None:
        for dir_name in SHARED_DIRS:
            self.root.joinpath(dir_name).mkdir(parents=True, exist_ok=True)
        if vault_type is not None:
            for wiki_dir in VAULT_TYPE_WIKI_DIRS.get(vault_type, []):
                self.root.joinpath(wiki_dir).mkdir(parents=True, exist_ok=True)
        for asset in SHARED_FILES:
            if not self.exists(asset.relative_path):
                self.write_vault_file(asset.relative_path, asset.content)

    def get_status(self) -> dict:
        """返回 Vault 初始化状态，不修改文件系统。"""
        kb_meta_exists = self.exists("KB-META.md")
        wiki_entities = (self.root / "wiki" / "entities").is_dir()
        wiki_concepts = (self.root / "wiki" / "concepts").is_dir()
        wiki_topics = (self.root / "wiki" / "topics").is_dir()
        wiki_sources = (self.root / "wiki" / "sources").is_dir()
        wiki_queries = (self.root / "wiki" / "queries").is_dir()

        vault_type = None
        if wiki_entities and wiki_concepts:
            vault_type = "code"
        elif wiki_topics and wiki_sources and wiki_queries:
            vault_type = "general"

        dirs_created = all(
            self.root.joinpath(d).is_dir() for d in SHARED_DIRS
        )

        return {
            "initialized": kb_meta_exists and dirs_created,
            "vaultType": vault_type,
            "sharedDirsExist": dirs_created,
        }

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

    def update_wiki_index(self, topics: list) -> None:
        """根据当前 wiki 文件列表重建 wiki/index.md（多维视图 + 成熟度统计）。"""
        wiki_files = self._list_recursive("wiki")
        topic_files = sorted(
            f for f in wiki_files
            if f not in ("wiki/index.md", "wiki/log.md")
        )

        # 收集每个页面的 frontmatter 信息
        page_meta: dict[str, dict] = {}
        for path in topic_files:
            try:
                content = self.read_vault_file(path)
                fm = self._parse_frontmatter(content)
                page_meta[path] = fm or {}
            except Exception:
                page_meta[path] = {}

        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

        # 按 frontmatter type 分类
        by_type: dict[str, list[str]] = {}
        for path in topic_files:
            pt = page_meta.get(path, {}).get("type", "unknown")
            by_type.setdefault(pt, []).append(path)

        # 按标签维度分类（business-line/* 或 topic/*）
        by_dimension: dict[str, list[str]] = {}
        unclassified: list[str] = []
        for path in topic_files:
            tags = page_meta.get(path, {}).get("tags", "")
            dims = self._extract_dimensions(tags)
            if dims:
                for d in dims:
                    by_dimension.setdefault(d, []).append(path)
            else:
                unclassified.append(path)

        # 成熟度统计
        status_counts: dict[str, int] = {"stub": 0, "draft": 0, "stable": 0, "outdated": 0, "unknown": 0}
        for path in topic_files:
            s = page_meta.get(path, {}).get("status", "")
            if s in status_counts:
                status_counts[s] += 1
            else:
                status_counts["unknown"] += 1

        lines = [
            "# 知识库目录",
            "",
            f"## 页面列表（{len(topic_files)} 页）",
            "",
        ]
        for path in topic_files:
            display = path.replace("wiki/", "").replace(".md", "")
            lines.append(f"- [[{display}]]")
        lines.append("")

        # ── 按页面类型 ──
        lines.append("## 按页面类型")
        for pt in sorted(by_type.keys()):
            lines.append(f"### {pt}（{len(by_type[pt])} 页）")
            for path in sorted(by_type[pt]):
                display = path.replace("wiki/", "").replace(".md", "")
                lines.append(f"- [[{display}]]")
            lines.append("")
        if not by_type:
            lines.append("（暂无分类页面）\n")

        # ── 按维度 ──
        lines.append("## 按维度")
        if by_dimension:
            for dim in sorted(by_dimension.keys()):
                label = dim.replace("business-line/", "业务线: ").replace("topic/", "主题: ")
                lines.append(f"### {label}（{len(by_dimension[dim])} 页）")
                for path in sorted(by_dimension[dim]):
                    display = path.replace("wiki/", "").replace(".md", "")
                    lines.append(f"- [[{display}]]")
                lines.append("")
        if unclassified:
            lines.append(f"### 待分类（{len(unclassified)} 页）")
            for path in sorted(unclassified):
                display = path.replace("wiki/", "").replace(".md", "")
                lines.append(f"- [[{display}]]")
            lines.append("")

        # ── 成熟度统计 ──
        lines.append("## 成熟度统计")
        lines.append(f"- stub: {status_counts['stub']}")
        lines.append(f"- draft: {status_counts['draft']}")
        lines.append(f"- stable: {status_counts['stable']}")
        lines.append(f"- outdated: {status_counts['outdated']}")
        if status_counts["unknown"] > 0:
            lines.append(f"- 未标状态: {status_counts['unknown']}")
        lines.append("")

        # ── 统计区 ──
        lines.append("## 统计")
        lines.append(f"- 总页数：{len(topic_files)}")
        type_counts = {pt: len(ps) for pt, ps in by_type.items()}
        for pt in sorted(type_counts.keys()):
            lines.append(f"- {pt}：{type_counts[pt]}")
        lines.append(f"- 最后更新：{timestamp}")
        lines.append("")

        self.write_vault_file("wiki/index.md", "\n".join(lines))

    @staticmethod
    def _parse_frontmatter(content: str) -> dict:
        import re
        m = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not m:
            return {}
        raw = m.group(1)
        result: dict = {}
        for line in raw.split("\n"):
            line = line.strip()
            if ":" in line:
                key, _, val = line.partition(":")
                result[key.strip()] = val.strip()
        return result

    @staticmethod
    def _extract_dimensions(tags_raw: str | list) -> list[str]:
        """Extract dimension labels from frontmatter tags."""
        tags: list[str] = []
        if isinstance(tags_raw, list):
            tags = [str(t).strip() for t in tags_raw if str(t).strip()]
        elif isinstance(tags_raw, str):
            import re
            tags_str = tags_raw.strip()
            if tags_str.startswith("[") and tags_str.endswith("]"):
                tags_str = tags_str[1:-1]
            tags = [t.strip() for t in re.split(r"[,，]", tags_str) if t.strip()]
        dims = []
        for t in tags:
            if t.startswith("business-line/") or t.startswith("topic/"):
                dims.append(t)
        return dims

    def _list_recursive(self, directory: str) -> list[str]:
        """Recursively list all .md files in a directory."""
        directory_path = self.resolve(directory)
        if not directory_path.is_dir():
            return []
        results: list[str] = []
        for path in directory_path.rglob("*.md"):
            relative = str(path.relative_to(self.root)).replace("\\", "/")
            results.append(relative)
        return results

    def append_log_entry(self, entry: str) -> None:
        """向 wiki/log.md 追加一条时间戳条目"""
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        log_line = f"- {timestamp} | {entry}"
        existing = ""
        if self.exists("wiki/log.md"):
            existing = self.read_vault_file("wiki/log.md").rstrip()
        self.write_vault_file("wiki/log.md", existing + "\n" + log_line + "\n")

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
inkdeskType: raw
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
            "inkdeskType: wiki",
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
