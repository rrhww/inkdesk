from __future__ import annotations

from argparse import Namespace

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
