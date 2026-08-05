from __future__ import annotations

from argparse import Namespace
<<<<<<< HEAD
=======
from pathlib import Path

import pytest
>>>>>>> origin/main

from inkdesk_skill_sdk import cli


class FakeResponse:
    def __init__(self, lines):
        self.lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def raise_for_status(self):
        return None

    def iter_lines(self):
        return iter(self.lines)


class FakeClient:
    def __init__(self, lines, **_kwargs):
        self.lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def stream(self, method, url, json):
        assert method == "POST"
        assert url == "http://server/api/engine/stream"
        assert json["command"] == "inspect repository"
        return FakeResponse(self.lines)


<<<<<<< HEAD
=======
class SkillFakeClient:
    def __init__(self, lines, captured, **_kwargs):
        self.lines = lines
        self.captured = captured

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def stream(self, method, url, json):
        self.captured.update({"method": method, "url": url, "json": json})
        return FakeResponse(self.lines)


>>>>>>> origin/main
def test_sse_parser_handles_named_json_events() -> None:
    events = list(
        cli._iter_sse_events(
            [
                "event: token",
                'data: {"taskId":"kb","token":"hello"}',
                "",
                ": heartbeat",
                "",
                "event: stream.end",
                'data: {"sequence":2}',
                "",
            ]
        )
    )

    assert events == [
        ("token", {"taskId": "kb", "token": "hello"}),
        ("stream.end", {"sequence": 2}),
    ]


def test_cli_run_streams_tokens_and_reports_ttft(monkeypatch, capsys) -> None:
    lines = [
        "event: stream.open",
        'data: {"sequence":1}',
        "",
        "event: token",
        'data: {"sequence":2,"taskId":"kb","token":"hello "}',
        "",
        "event: token",
        'data: {"sequence":3,"taskId":"kb","token":"world"}',
        "",
        "event: stream.end",
        'data: {"sequence":4}',
        "",
    ]
    monkeypatch.setattr(cli.httpx, "Client", lambda **kwargs: FakeClient(lines, **kwargs))

    exit_code = cli.cmd_run(
        Namespace(
            prompt=["inspect", "repository"],
            plan=None,
            server="http://server",
            show_ttft=True,
        )
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "[kb] hello world\n"
    assert captured.err.startswith("TTFT ")


<<<<<<< HEAD
def test_cli_run_reads_target_and_writes_solution(monkeypatch, tmp_path, capsys) -> None:
    target = tmp_path / "mock-interview-prd.md"
    target.write_text("# Mock interview\n\nBuild an observable interview flow.\n", encoding="utf-8")
    lines = [
        "event: result",
        'data: {"outputs":{"synthesis":"Implementation-ready plan."}}',
        "",
        "event: stream.end",
        'data: {"sequence":2}',
        "",
    ]

    class TargetClient(FakeClient):
        def stream(self, method, url, json):
            assert str(target.resolve()) in json["command"]
            assert "Build an observable interview flow." in json["command"]
            return super().stream(method, url, {"command": "inspect repository"})

    monkeypatch.setattr(cli.httpx, "Client", lambda **kwargs: TargetClient(lines, **kwargs))
=======
def test_cli_run_tech_solution_validates_prd_and_prints_artifact(monkeypatch, capsys, tmp_path: Path) -> None:
    prd = tmp_path / "mock-interview-prd.md"
    prd.write_text("# Mock Interview\n\nBuild an interview workflow.\n", encoding="utf-8")
    captured_request = {}
    lines = [
        "event: stream.open",
        'data: {"sequence":1}',
        "",
        "event: artifact.written",
        'data: {"sequence":2,"path":"/vault/wiki/generated/mock-interview-prd-tech-solution.md"}',
        "",
        "event: result",
        'data: {"sequence":3,"artifactPath":"/vault/wiki/generated/mock-interview-prd-tech-solution.md"}',
        "",
        "event: stream.end",
        'data: {"sequence":4}',
        "",
    ]
    monkeypatch.setattr(
        cli.httpx,
        "Client",
        lambda **kwargs: SkillFakeClient(lines, captured_request, **kwargs),
    )
>>>>>>> origin/main

    exit_code = cli.cmd_run(
        Namespace(
            prompt=["tech-solution"],
<<<<<<< HEAD
            target=str(target),
=======
            prd=str(prd),
            target=None,
>>>>>>> origin/main
            plan=None,
            server="http://server",
            show_ttft=False,
        )
    )

<<<<<<< HEAD
    solution = tmp_path / "mock-interview-prd-tech-solution.md"
    assert exit_code == 0
    assert "Implementation-ready plan." in solution.read_text(encoding="utf-8")
    assert "Generated solution:" in capsys.readouterr().err
=======
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "Generated: /vault/wiki/generated/mock-interview-prd-tech-solution.md\n"
    assert captured_request["url"] == "http://server/api/skills/tech-solution/stream"
    assert captured_request["json"] == {
        "inputs": {
            "requirement": "# Mock Interview\n\nBuild an interview workflow.\n",
            "sourcePath": str(prd.resolve()),
            "sourceTitle": "Mock Interview",
        },
        "maxConcurrency": 4,
    }


def test_cli_target_alias_warns_and_stream_error_is_nonzero(monkeypatch, capsys, tmp_path: Path) -> None:
    prd = tmp_path / "prd.md"
    prd.write_text("# PRD\n", encoding="utf-8")
    lines = [
        "event: stream.error",
        'data: {"code":"PROVIDER_ERROR","message":"Provider request failed."}',
        "",
        "event: stream.end",
        'data: {"sequence":2}',
        "",
    ]
    monkeypatch.setattr(
        cli.httpx,
        "Client",
        lambda **kwargs: SkillFakeClient(lines, {}, **kwargs),
    )

    exit_code = cli.cmd_run(
        Namespace(
            prompt=["tech-solution"],
            prd=None,
            target=str(prd),
            plan=None,
            server="http://server",
            show_ttft=False,
        )
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "--target is deprecated" in captured.err
    assert "Error [PROVIDER_ERROR]" in captured.err


@pytest.mark.parametrize(
    ("name", "content", "expected"),
    [
        ("empty.md", b"", "cannot be empty"),
        ("wrong.txt", b"hello", "must be a Markdown"),
        ("bad.md", b"\xff\xfe", "valid UTF-8"),
    ],
)
def test_cli_rejects_invalid_prd_files(tmp_path: Path, name: str, content: bytes, expected: str) -> None:
    path = tmp_path / name
    path.write_bytes(content)

    with pytest.raises(ValueError, match=expected):
        cli._read_prd(str(path))


def test_cli_rejects_missing_and_oversized_prd(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        cli._read_prd(str(tmp_path / "missing.md"))

    oversized = tmp_path / "large.md"
    oversized.write_bytes(b"a" * (2 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="2 MiB"):
        cli._read_prd(str(oversized))


def test_cli_harness_audit_creates_run_and_consumes_persisted_events(monkeypatch, capsys) -> None:
    captured: dict = {}
    lines = [
        "id: 1",
        "event: stage.started",
        'data: {"sequence":1,"type":"stage.started","data":{"stageId":"preflight"}}',
        "",
        "id: 2",
        "event: executor.tool.requested",
        'data: {"sequence":2,"type":"executor.tool.requested","data":{"tool":"Bash"}}',
        "",
        "id: 3",
        "event: artifact.written",
        'data: {"sequence":3,"type":"artifact.written","data":{"kind":"report","path":"[USER_HOME]/vault/wiki/generated/repo-harness-audit.md","relativePath":"wiki/generated/repo-harness-audit.md"}}',
        "",
        "id: 4",
        "event: stream.end",
        'data: {"sequence":4,"type":"stream.end","data":{"status":"succeeded"}}',
        "",
    ]

    class CreateResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"runId": "run-abc", "eventsUrl": "/api/runs/run-abc/events"}

    class HarnessClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, url, json):
            captured.update({"url": url, "json": json})
            return CreateResponse()

        def stream(self, method, url):
            assert method == "GET"
            assert url == "http://server/api/runs/run-abc/events"
            return FakeResponse(lines)

    monkeypatch.setattr(cli.httpx, "Client", HarnessClient)
    exit_code = cli.cmd_run(
        Namespace(
            prompt=["harness-audit"],
            prd=None,
            target=None,
            plan=None,
            server="http://server",
            show_ttft=False,
            executor="claude",
            depth="quick",
            repo=None,
        )
    )
    output = capsys.readouterr()
    assert exit_code == 0
    assert "Run: run-abc" in output.out
    assert "[preflight] running" in output.out
    assert "Approval required for Bash" in output.out
    assert "Generated: wiki/generated/repo-harness-audit.md" in output.out
    assert "[USER_HOME]" not in output.out
    assert captured["json"]["executor"] == "claude"


def test_cli_live_executor_probe(monkeypatch, capsys) -> None:
    class ProbeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "available": True,
                "capabilities": ["agent-loop", "tool-use"],
                "toolLoopVerified": True,
                "structuredOutputVerified": True,
            }

    class ProbeClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def request(self, method, url):
            assert method == "POST"
            assert url == "http://server/api/executors/claude/probe"
            return ProbeResponse()

    monkeypatch.setattr(cli.httpx, "Client", ProbeClient)
    result = cli.cmd_executor(Namespace(executor_name="claude", live=True, server="http://server"))
    output = capsys.readouterr().out
    assert result == 0
    assert "Tool loop verified: true" in output
    assert "Structured output verified: true" in output
>>>>>>> origin/main
