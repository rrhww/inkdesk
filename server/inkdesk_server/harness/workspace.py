from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class WorkspaceLease:
    id: str
    run_id: str
    stage_id: str
    path: Path
    repo_head: str


class WorkspaceManager:
    def __init__(self, repo_root: Path, work_root: Path | None = None):
        self.repo_root = Path(repo_root).resolve()
        self.work_root = Path(work_root or Path(tempfile.gettempdir()) / "inkdesk-harness").resolve()
        try:
            self.work_root.relative_to(self.repo_root)
        except ValueError:
            pass
        else:
            raise ValueError("Harness work root must not be inside the source repository.")
        self.work_root.mkdir(parents=True, exist_ok=True)
        self._leases: dict[str, WorkspaceLease] = {}
        self._cleanup_stale()

    def acquire(self, run_id: str, stage_id: str, repo_head: str) -> WorkspaceLease:
        path = (self.work_root / run_id / stage_id).resolve()
        self._assert_owned(path)
        if path.exists():
            raise RuntimeError(f"Workspace already exists: {run_id}/{stage_id}")
        path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "-C", str(self.repo_root), "worktree", "add", "--detach", str(path), repo_head],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        lease = WorkspaceLease(f"ws-{run_id}-{stage_id}", run_id, stage_id, path, repo_head)
        self._leases[lease.id] = lease
        return lease

    def release(self, lease: WorkspaceLease) -> None:
        self._assert_owned(lease.path)
        try:
            subprocess.run(
                ["git", "-C", str(self.repo_root), "worktree", "remove", "--force", str(lease.path)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        finally:
            if lease.path.exists():
                shutil.rmtree(lease.path)
            self._leases.pop(lease.id, None)
            parent = lease.path.parent
            if parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()

    def close(self) -> None:
        for lease in tuple(self._leases.values()):
            self.release(lease)

    def _assert_owned(self, path: Path) -> None:
        try:
            path.resolve().relative_to(self.work_root)
        except ValueError as exc:
            raise ValueError("Harness workspace path escapes the configured work root.") from exc

    def _cleanup_stale(self) -> None:
        result = subprocess.run(
            ["git", "-C", str(self.repo_root), "worktree", "list", "--porcelain"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        for line in result.stdout.splitlines():
            if not line.startswith("worktree "):
                continue
            candidate = Path(line.removeprefix("worktree ").strip()).resolve()
            try:
                candidate.relative_to(self.work_root)
            except ValueError:
                continue
            if candidate == self.work_root:
                continue
            subprocess.run(
                ["git", "-C", str(self.repo_root), "worktree", "remove", "--force", str(candidate)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
            if candidate.exists():
                shutil.rmtree(candidate)
            parent = candidate.parent
            if parent != self.work_root and parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
