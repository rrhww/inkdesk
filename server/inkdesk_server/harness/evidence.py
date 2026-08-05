from __future__ import annotations

import re
import subprocess
from hashlib import sha256
from pathlib import Path

from inkdesk_server.harness.models import (
    EvidenceBundle,
    EvidenceEnvelope,
    EvidenceItem,
    EvidenceStatus,
    utc_now,
)
from inkdesk_server.harness.redaction import redact_text


SECRET_PATH = re.compile(
    r"(^|[._-])(env|secrets?|credentials?|private[-_]?keys?)([._-]|$)",
    re.I,
)
SKIPPED_PARTS = {
    ".git",
    ".next",
    ".venv",
    "build",
    "dist",
    "node_modules",
    "target",
    "vendor",
}
MAX_TRACKED_PATHS = 5000


class EvidenceCollector:
    def __init__(self, repo_root: Path):
        self.repo_root = Path(repo_root).resolve()
        if not self.repo_root.is_dir():
            raise FileNotFoundError(self.repo_root)

    def collect(self, run_id: str, *, depth: str = "quick") -> EvidenceBundle:
        if depth not in {"quick", "normal"}:
            raise ValueError("depth must be quick or normal")
        captured_at = utc_now()
        repo_head = self._git("rev-parse", "HEAD").strip()
        tracked = self._tracked_paths()
        limit = 3 if depth == "quick" else 5

        project_paths = self._select_project_harness(tracked, limit)
        project_items = [self._file_item(path, repo_head, captured_at) for path in project_paths]
        project_items = [item for item in project_items if item is not None]

        agent_paths = [
            path
            for path in tracked
            if path.parts and path.parts[0] in {".agents", ".claude", ".codex"}
            or "skills" in path.parts
        ][: 20 if depth == "quick" else 50]
        agent_summary = [f"Detected {len(agent_paths)} tracked agent customization assets."]
        agent_items = [self._inventory_item("agent-assets", agent_paths, repo_head, captured_at)]

        workflow_paths = [path for path in tracked if path.parts[:2] == (".github", "workflows")]
        test_paths = [path for path in tracked if "tests" in path.parts or path.name.startswith("test_")]
        delivery_facts = [
            f"Detected {len(workflow_paths)} tracked CI workflow files.",
            f"Detected {len(test_paths)} tracked test files.",
            f"Working tree changes: {len(self._git('status', '--porcelain').splitlines())}.",
        ]
        delivery_items = [
            self._inventory_item("delivery-assets", workflow_paths + test_paths[:20], repo_head, captured_at),
            self._text_item(
                "recent-history",
                "git log",
                self._git("log", f"--since={'7 days ago' if depth == 'quick' else '30 days ago'}", "--oneline", "-20"),
                repo_head,
                captured_at,
            ),
        ]

        envelopes = {
            "projectHarness": EvidenceEnvelope(
                status=EvidenceStatus.AVAILABLE if project_items else EvidenceStatus.UNAVAILABLE,
                summaryFacts=[f"Collected {len(project_items)} project guidance assets."],
                evidence=project_items,
            ),
            "agentCustomize": EvidenceEnvelope(
                status=EvidenceStatus.AVAILABLE if agent_paths else EvidenceStatus.UNAVAILABLE,
                summaryFacts=agent_summary,
                evidence=agent_items if agent_paths else [],
            ),
            "deliveryEvidence": EvidenceEnvelope(
                status=EvidenceStatus.AVAILABLE,
                summaryFacts=delivery_facts,
                evidence=delivery_items,
            ),
            "leadSummary": EvidenceEnvelope(
                status=EvidenceStatus.AVAILABLE,
                summaryFacts=[
                    "Session evidence was not authorized and remains unavailable.",
                    "Configured assets are not proof of runtime use.",
                ],
                evidence=[],
            ),
        }
        return EvidenceBundle(
            runId=run_id,
            target="repository",
            depth=depth,
            repoHead=repo_head,
            capturedAt=captured_at,
            sessionEvidenceStatus=EvidenceStatus.UNAVAILABLE,
            envelopes=envelopes,
        )

    def current_head(self) -> str:
        return self._git("rev-parse", "HEAD").strip()

    def is_dirty(self) -> bool:
        return bool(self._git("status", "--porcelain").strip())

    def _tracked_paths(self) -> list[Path]:
        values: list[Path] = []
        for raw in self._git("ls-tree", "-r", "--name-only", "HEAD").splitlines()[:MAX_TRACKED_PATHS]:
            if not raw.strip():
                continue
            path = Path(raw.strip())
            if self._safe_path(path):
                values.append(path)
        return sorted(values, key=lambda item: item.as_posix().casefold())

    def _select_project_harness(self, tracked: list[Path], limit: int) -> list[Path]:
        priority = ["AGENTS.md", "CLAUDE.md", "README.md", "pyproject.toml", "package.json"]
        result: list[Path] = []
        by_name = {path.as_posix(): path for path in tracked}
        for name in priority:
            if name in by_name:
                result.append(by_name[name])
            if len(result) == limit:
                return result
        for path in tracked:
            if path.suffix.casefold() == ".md" and path not in result:
                result.append(path)
            if len(result) == limit:
                break
        return result

    def _file_item(self, relative: Path, repo_head: str, captured_at: str) -> EvidenceItem | None:
        metadata = self._git("ls-tree", repo_head, "--", relative.as_posix()).strip()
        if not metadata or metadata.startswith("120000 "):
            return None
        try:
            content_bytes = self._git_bytes("show", f"{repo_head}:{relative.as_posix()}")
            if b"\0" in content_bytes:
                return None
            content = content_bytes.decode("utf-8")
        except (OSError, UnicodeDecodeError, subprocess.SubprocessError):
            return None
        return self._text_item(relative.as_posix(), relative.as_posix(), content[:32768], repo_head, captured_at)

    def _inventory_item(
        self,
        name: str,
        paths: list[Path],
        repo_head: str,
        captured_at: str,
    ) -> EvidenceItem:
        content = "\n".join(path.as_posix() for path in paths) or "No matching tracked files."
        return self._text_item(name, name, content, repo_head, captured_at)

    def _text_item(
        self,
        identity: str,
        source: str,
        content: str,
        repo_head: str,
        captured_at: str,
    ) -> EvidenceItem:
        digest = sha256(content.encode("utf-8")).hexdigest()
        evidence_id = "E-" + sha256(f"{identity}|{digest}".encode("utf-8")).hexdigest()[:12]
        return EvidenceItem(
            id=evidence_id,
            source=source,
            contentHash=digest,
            capturedAt=captured_at,
            repoHead=repo_head,
            excerpt=redact_text(content),
        )

    def _safe_path(self, relative: Path) -> bool:
        if relative.is_absolute() or ".." in relative.parts:
            return False
        if any(part in SKIPPED_PARTS for part in relative.parts):
            return False
        return not any(SECRET_PATH.search(part) for part in relative.parts)

    def _git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.repo_root), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        return result.stdout

    def _git_bytes(self, *args: str) -> bytes:
        result = subprocess.run(
            ["git", "-C", str(self.repo_root), *args],
            check=True,
            capture_output=True,
            timeout=10,
        )
        return result.stdout
