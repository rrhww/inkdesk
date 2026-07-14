from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")
    path.chmod(0o755)


def test_local_server_entrypoint_does_not_start_uvicorn_when_migration_fails(tmp_path: Path):
    shell = shutil.which("sh")
    if shell is None:
        pytest.skip("A POSIX shell is required to test the Docker entrypoint.")
    repository_root = Path(__file__).resolve().parents[3]
    entrypoint = repository_root / "infra" / "docker" / "local-server-entrypoint.sh"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    marker = tmp_path / "uvicorn-started"
    _write_executable(fake_bin / "python", "#!/bin/sh\nexit 19\n")
    _write_executable(fake_bin / "uvicorn", f"#!/bin/sh\ntouch '{marker.as_posix()}'\n")

    completed = subprocess.run(
        [shell, str(entrypoint), "inkdesk_server.main:app"],
        check=False,
        env={**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"},
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 19
    assert marker.exists() is False
