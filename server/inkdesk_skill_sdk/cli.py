"""
CLI entry point for Skill SDK operations: init, validate, graph, check.

Usage:
  python -m inkdesk_skill_sdk init <name> --description <text> --category <category> --kind <kind> [--resources refs,prompts] [--target <dir>]
  python -m inkdesk_skill_sdk validate [<name>] [--root <path>]
  python -m inkdesk_skill_sdk graph [--root <path>]
  python -m inkdesk_skill_sdk check <name> [--root <path>]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from time import perf_counter

import httpx

from inkdesk_skill_sdk.contracts import SkillCategory, SkillKind
from inkdesk_skill_sdk.graph import build_graph, validate_graph
from inkdesk_skill_sdk.registry import SkillRegistry
from inkdesk_skill_sdk.scaffolder import init_skill_package
from inkdesk_skill_sdk.validation import (
    Severity,
    validate_safety,
    validate_semantic,
    validate_structural,
)


def _resolve_root(root_arg: str | None) -> Path:
    if root_arg:
        return Path(root_arg).resolve()
    # Default: look for vault skills/ relative to cwd
    cwd = Path.cwd()
    # Try vault/skills if in server directory
    for candidate in [cwd / "vault" / "skills", cwd / ".dev-vault" / "skills", cwd / "skills"]:
        if candidate.exists():
            return candidate
    return cwd / "skills"


def cmd_init(args: argparse.Namespace) -> int:
    target_dir = Path(args.target).resolve() if args.target else Path.cwd() / "skills" / args.name
    resources = [r.strip() for r in args.resources.split(",")] if args.resources else []

    try:
        pkg_path = init_skill_package(
            target_dir=target_dir,
            name=args.name,
            description=args.description,
            category=args.category,
            kind=args.kind,
            resources=resources,
        )
        print(f"Created Skill package: {pkg_path}")
        return 0
    except FileExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    if args.name:
        pkg_path = root / args.name
        if not pkg_path.is_dir():
            print(f"Error: Skill package not found: {pkg_path}", file=sys.stderr)
            return 1
        packages = [pkg_path]
    else:
        registry = SkillRegistry([root])
        packages = registry.discover()
        if not packages:
            print("No Skill packages found.")
            return 0

    exit_code = 0
    for pkg_path in sorted(packages):
        findings = (
            validate_structural(pkg_path)
            + validate_semantic(pkg_path)
            + validate_safety(pkg_path)
        )
        passed = all(f.severity != Severity.ERROR for f in findings)
        status = "PASSED" if passed else "FAILED"
        print(f"\n{pkg_path.name}: {status}")
        for f in findings:
            marker = "E" if f.severity == Severity.ERROR else "W"
            print(f"  [{marker}] {f.code}: {f.message}")
        if not passed:
            exit_code = 1

    return exit_code


def cmd_graph(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    registry = SkillRegistry([root])
    graph = build_graph(registry)
    findings = validate_graph(graph)

    print(f"Nodes: {len(graph.nodes)}")
    for node_id, node in sorted(graph.nodes.items()):
        edges_str = ", ".join(node.edges) if node.edges else "(none)"
        print(f"  {node_id} ({node.meta.kind}/{node.meta.category}) -> [{edges_str}]")

    exit_code = 0
    if findings:
        print(f"\nFindings ({len(findings)}):")
        for f in findings:
            marker = "E" if f.severity == Severity.ERROR else "W"
            print(f"  [{marker}] {f.code}: {f.message}")
            if f.severity == Severity.ERROR:
                exit_code = 1

    return exit_code


def cmd_check(args: argparse.Namespace) -> int:
    root = _resolve_root(args.root)
    pkg_path = root / args.name

    if not pkg_path.is_dir():
        print(f"Error: Skill package not found: {pkg_path}", file=sys.stderr)
        return 1

    findings = (
        validate_structural(pkg_path)
        + validate_semantic(pkg_path)
        + validate_safety(pkg_path)
    )
    passed = all(f.severity != Severity.ERROR for f in findings)

    print(f"Promotion check for {args.name}:")
    print(f"  Lint: {'PASSED' if passed else 'FAILED'}")

    for f in findings:
        marker = "E" if f.severity == Severity.ERROR else "W"
        print(f"    [{marker}] {f.code}: {f.message}")

    # Check for behavioral cases
    evals_dir = pkg_path.parent.parent / "evals" / "skills" / args.name
    cases_path = evals_dir / "contract-cases.json"
    if cases_path.is_file():
        print(f"  Behavioral cases: FOUND ({cases_path})")
    else:
        print(f"  Behavioral cases: MISSING ({cases_path})")

    # Check for schema gate
    print(f"  Schema gate: CHECK_REQUIRED (run health check)")
    print(f"  Human review: CHECK_REQUIRED (not automated)")

    if not passed:
        print(f"\nResult: NOT READY for promotion")
        return 1
    else:
        print(f"\nResult: Lint passed — needs behavioral cases + human review + schema gate")
        return 0


def _iter_sse_events(lines):
    event_name = "message"
    data_lines: list[str] = []
    for line in lines:
        if line == "":
            if data_lines:
                raw_data = "\n".join(data_lines)
                try:
                    data = json.loads(raw_data)
                except json.JSONDecodeError:
                    data = {"raw": raw_data}
                yield event_name, data
            event_name = "message"
            data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
    if data_lines:
        raw_data = "\n".join(data_lines)
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            data = {"raw": raw_data}
        yield event_name, data


def cmd_run(args: argparse.Namespace) -> int:
    prompt = list(getattr(args, "prompt", []))
    prd_arg = getattr(args, "prd", None)
    target_arg = getattr(args, "target", None)
    if prompt and prompt[0] == "harness-audit":
        return _cmd_run_harness(args, prompt)
    if prd_arg or target_arg or (prompt and prompt[0] == "tech-solution"):
        return _cmd_run_skill(args, prompt, prd_arg, target_arg)

    command = " ".join(prompt).strip()
    if not command:
        print("Error: a command or Skill id is required", file=sys.stderr)
        return 2
    payload: dict = {"command": command}
    if args.plan:
        try:
            plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Error: invalid DAG plan: {exc}", file=sys.stderr)
            return 1
        if isinstance(plan, list):
            payload["tasks"] = plan
        elif isinstance(plan, dict):
            payload.update({key: value for key, value in plan.items() if key in {"tasks", "maxConcurrency"}})
        else:
            print("Error: DAG plan must be an object or task array", file=sys.stderr)
            return 1

    server_url = args.server.rstrip("/")
    started = perf_counter()
    first_visible_at: float | None = None
    current_task: str | None = None
    failed = False
    try:
        with httpx.Client(timeout=None) as client:
            with client.stream("POST", f"{server_url}/api/engine/stream", json=payload) as response:
                response.raise_for_status()
                for event, data in _iter_sse_events(response.iter_lines()):
                    if first_visible_at is None:
                        first_visible_at = perf_counter()
                    if event == "token":
                        task_id = str(data.get("taskId") or "agent")
                        if task_id != current_task:
                            if current_task is not None:
                                sys.stdout.write("\n")
                            sys.stdout.write(f"[{task_id}] ")
                            current_task = task_id
                        sys.stdout.write(str(data.get("token") or ""))
                        sys.stdout.flush()
                    elif event == "stream.error":
                        failed = True
                        print(f"\nError: {data.get('error', 'stream failed')}", file=sys.stderr)
    except (httpx.HTTPError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if current_task is not None:
        sys.stdout.write("\n")
    if args.show_ttft and first_visible_at is not None:
        print(f"TTFT {(first_visible_at - started) * 1000:.1f} ms", file=sys.stderr)
    return 1 if failed else 0


def _cmd_run_harness(args: argparse.Namespace, prompt: list[str]) -> int:
    if len(prompt) > 1:
        print("Error: harness-audit does not accept positional arguments", file=sys.stderr)
        return 2
    repo_arg = getattr(args, "repo", None)
    repo_path: Path | None = None
    if repo_arg:
        repo_path = Path(repo_arg).expanduser().resolve()
        if not repo_path.is_dir() or not (repo_path / ".git").exists():
            print(f"Error: --repo must identify a Git repository: {repo_path}", file=sys.stderr)
            return 2
    payload = {
        "capabilityId": "harness-audit",
        "inputs": {
            "target": "repository",
            "depth": getattr(args, "depth", "quick"),
            **({"repoPath": str(repo_path)} if repo_path else {}),
        },
        "executor": getattr(args, "executor", "claude"),
    }
    server_url = args.server.rstrip("/")
    started = perf_counter()
    first_visible_at: float | None = None
    report_path: str | None = None
    failed = False
    try:
        with httpx.Client(timeout=None) as client:
            response = client.post(f"{server_url}/api/runs", json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError:
                print(f"Error: {_http_error_message(response)}", file=sys.stderr)
                return 1
            created = response.json()
            run_id = str(created["runId"])
            events_url = str(created.get("eventsUrl") or f"/api/runs/{run_id}/events")
            if events_url.startswith("/"):
                events_url = server_url + events_url
            print(f"Run: {run_id}")
            with client.stream("GET", events_url) as stream:
                stream.raise_for_status()
                for event, envelope in _iter_sse_events(stream.iter_lines()):
                    if first_visible_at is None:
                        first_visible_at = perf_counter()
                    data = envelope.get("data", envelope) if isinstance(envelope, dict) else {}
                    if event == "stage.started":
                        print(f"[{data.get('stageId', 'stage')}] running")
                    elif event == "executor.tool.requested":
                        web_url = os.environ.get("INKDESK_WEB_URL", "http://127.0.0.1:3000").rstrip("/")
                        print(
                            f"Approval required for {data.get('tool', 'tool')}: "
                            f"{web_url}/app/runs/{run_id}"
                        )
                    elif event == "finding.created":
                        print(f"Finding {data.get('id')}: {data.get('title')}")
                    elif event == "artifact.written" and data.get("kind") == "report":
                        report_path = str(data.get("relativePath") or data.get("path") or "") or None
                    elif event == "run.failed":
                        failed = True
                        print(
                            f"Error [{data.get('code', 'RUN_FAILED')}]: {data.get('message', 'Audit failed')}",
                            file=sys.stderr,
                        )
                    elif event == "run.cancelled":
                        failed = True
                        print("Error: audit run was cancelled", file=sys.stderr)
    except (httpx.HTTPError, OSError, ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.show_ttft and first_visible_at is not None:
        print(f"TTFT {(first_visible_at - started) * 1000:.1f} ms", file=sys.stderr)
    if failed:
        return 1
    if report_path:
        print(f"Generated: {report_path}")
    return 0


def cmd_executor(args: argparse.Namespace) -> int:
    server_url = args.server.rstrip("/")
    suffix = "/probe" if args.live else ""
    method = "POST" if args.live else "GET"
    try:
        with httpx.Client(timeout=None) as client:
            response = client.request(method, f"{server_url}/api/executors/{args.executor_name}{suffix}")
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError:
                print(f"Error: {_http_error_message(response)}", file=sys.stderr)
                return 1
            value = response.json()
    except (httpx.HTTPError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    capabilities = ", ".join(value.get("capabilities") or [])
    print(f"Executor: {args.executor_name}")
    print(f"Available: {str(bool(value.get('available'))).lower()}")
    if capabilities:
        print(f"Capabilities: {capabilities}")
    if args.live:
        print(f"Tool loop verified: {str(bool(value.get('toolLoopVerified'))).lower()}")
        print(f"Structured output verified: {str(bool(value.get('structuredOutputVerified'))).lower()}")
    return 0


def _cmd_run_skill(
    args: argparse.Namespace,
    prompt: list[str],
    prd_arg: str | None,
    target_arg: str | None,
) -> int:
    skill_id = prompt[0] if prompt else "tech-solution"
    if skill_id != "tech-solution":
        print(f"Error: unsupported Skill: {skill_id}", file=sys.stderr)
        return 2
    if len(prompt) > 1:
        print("Error: tech-solution accepts the PRD through --prd", file=sys.stderr)
        return 2
    if prd_arg and target_arg:
        print("Error: use either --prd or --target, not both", file=sys.stderr)
        return 2
    source_arg = prd_arg or target_arg
    if not source_arg:
        print("Error: tech-solution requires --prd <markdown>", file=sys.stderr)
        return 2
    if target_arg:
        print("Warning: --target is deprecated; use --prd instead.", file=sys.stderr)

    try:
        source_path, requirement, source_title = _read_prd(source_arg)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    payload = {
        "inputs": {
            "requirement": requirement,
            "sourcePath": str(source_path),
            "sourceTitle": source_title,
        },
        "maxConcurrency": 4,
    }
    server_url = args.server.rstrip("/")
    started = perf_counter()
    first_visible_at: float | None = None
    failed = False
    artifact_path: str | None = None
    try:
        with httpx.Client(timeout=None) as client:
            with client.stream(
                "POST",
                f"{server_url}/api/skills/{skill_id}/stream",
                json=payload,
            ) as response:
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError:
                    message = _http_error_message(response)
                    print(f"Error: {message}", file=sys.stderr)
                    return 1
                for event, data in _iter_sse_events(response.iter_lines()):
                    if first_visible_at is None:
                        first_visible_at = perf_counter()
                    if event == "artifact.written":
                        artifact_path = str(data.get("path") or data.get("relativePath") or "") or None
                    elif event == "result":
                        artifact_path = str(data.get("artifactPath") or artifact_path or "") or None
                    elif event == "stream.error":
                        failed = True
                        code = str(data.get("code") or "STREAM_ERROR")
                        message = str(data.get("message") or data.get("error") or "Skill execution failed")
                        print(f"Error [{code}]: {message}", file=sys.stderr)
    except (httpx.HTTPError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.show_ttft and first_visible_at is not None:
        print(f"TTFT {(first_visible_at - started) * 1000:.1f} ms", file=sys.stderr)
    if failed:
        return 1
    if not artifact_path:
        print("Error: the Skill stream ended without an artifact", file=sys.stderr)
        return 1
    print(f"Generated: {artifact_path}")
    return 0


def _read_prd(value: str) -> tuple[Path, str, str]:
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise ValueError(f"PRD does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"PRD is not a file: {path}")
    if path.suffix.casefold() != ".md":
        raise ValueError("PRD must be a Markdown (.md) file")
    size = path.stat().st_size
    if size == 0:
        raise ValueError("PRD cannot be empty")
    if size > 2 * 1024 * 1024:
        raise ValueError("PRD exceeds the 2 MiB limit")
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("PRD must be valid UTF-8") from exc
    if not content.strip():
        raise ValueError("PRD cannot contain only whitespace")
    heading = re.search(r"^#\s+(.+?)\s*$", content, re.MULTILINE)
    title = heading.group(1).strip() if heading else path.stem.replace("-", " ").strip()
    return path, content, title


def _http_error_message(response) -> str:
    try:
        payload = response.json()
    except (ValueError, AttributeError):
        return f"server returned HTTP {response.status_code}"
    code = payload.get("code") if isinstance(payload, dict) else None
    message = payload.get("message") if isinstance(payload, dict) else None
    if code and message:
        return f"[{code}] {message}"
    return str(message or f"server returned HTTP {response.status_code}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inkdesk Skill SDK CLI",
    )
    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="Initialize a new draft Skill package")
    p_init.add_argument("name", help="Skill name (lowercase, digits, hyphens)")
    p_init.add_argument("--description", required=True, help="One-line summary")
    p_init.add_argument("--category", required=True, choices=[c.value for c in SkillCategory], help="Skill category")
    p_init.add_argument("--kind", required=True, choices=[k.value for k in SkillKind], help="Skill kind")
    p_init.add_argument("--resources", help="Comma-separated optional dirs (references,prompts,templates)")
    p_init.add_argument("--target", help="Target directory (default: skills/<name>)")

    # validate
    p_val = sub.add_parser("validate", help="Validate Skill packages")
    p_val.add_argument("name", nargs="?", help="Specific Skill name; omit to validate all")
    p_val.add_argument("--root", help="Skills directory root")

    # graph
    p_gr = sub.add_parser("graph", help="Build and validate routing graph")
    p_gr.add_argument("--root", help="Skills directory root")

    # check
    p_chk = sub.add_parser("check", help="Run full promotion check on a Skill")
    p_chk.add_argument("name", help="Skill name to check")
    p_chk.add_argument("--root", help="Skills directory root")

    # run
    p_run = sub.add_parser("run", help="Execute a Skill or an in-memory DAG")
    p_run.add_argument("prompt", nargs="*", help="Skill id or legacy command sent to the agent DAG")
    p_run.add_argument("--prd", help="UTF-8 Markdown PRD for tech-solution")
    p_run.add_argument("--target", help="Deprecated alias for --prd")
    p_run.add_argument("--executor", default="claude", choices=["claude", "codex", "deterministic"], help="Executor for harness capabilities")
    p_run.add_argument("--depth", default="quick", choices=["quick", "normal"], help="Evidence collection depth")
    p_run.add_argument("--repo", help="Repository path; must match the server configuration")
    p_run.add_argument("--plan", help="Optional JSON DAG plan")
    p_run.add_argument(
        "--server",
        default=os.environ.get("INKDESK_SERVER_URL", "http://127.0.0.1:8080"),
        help="Inkdesk server base URL",
    )
    p_run.add_argument("--show-ttft", action="store_true", help="Print time to first SSE event")

    p_executor = sub.add_parser("executor", help="Inspect or live-probe an Agent Executor")
    p_executor.add_argument("executor_name", choices=["claude", "codex"])
    p_executor.add_argument("--live", action="store_true", help="Run a paid tool-loop capability probe")
    p_executor.add_argument(
        "--server",
        default=os.environ.get("INKDESK_SERVER_URL", "http://127.0.0.1:8080"),
        help="Inkdesk server base URL",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "init":
        return cmd_init(args)
    elif args.command == "validate":
        return cmd_validate(args)
    elif args.command == "graph":
        return cmd_graph(args)
    elif args.command == "check":
        return cmd_check(args)
    elif args.command == "run":
        return cmd_run(args)
    elif args.command == "executor":
        return cmd_executor(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
