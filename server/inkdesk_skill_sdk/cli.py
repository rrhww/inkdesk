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
    command = " ".join(args.prompt).strip()
    target_path: Path | None = None
    solution_path: Path | None = None
    target_arg = getattr(args, "target", None)
    if target_arg:
        target_path = Path(target_arg).resolve()
        try:
            if not target_path.is_file():
                raise FileNotFoundError(target_path)
            if target_path.stat().st_size > 1_000_000:
                raise ValueError("target document exceeds the 1 MB CLI limit")
            target_content = target_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError, ValueError) as exc:
            print(f"Error: unable to read target document: {exc}", file=sys.stderr)
            return 1

        solution_path = target_path.with_name(f"{target_path.stem}-tech-solution.md")
        solution_path.write_text(
            "---\nkind: solution\nstatus: active\nsource: engine\n---\n\n"
            f"# {target_path.stem} Tech Solution\n\n"
            f"Source: [{target_path.name}]({target_path.name})\n\n"
            "DAG execution is in progress.\n",
            encoding="utf-8",
        )
        command = (
            f"Skill: {command}\n"
            f"Target: {target_path}\n\n"
            "Read the following product requirements and produce an implementation-ready technical solution.\n\n"
            f"{target_content}"
        )

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
    result_outputs: dict[str, str] = {}
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
                    elif event == "result":
                        outputs = data.get("outputs")
                        if isinstance(outputs, dict):
                            result_outputs = {
                                str(task_id): str(output)
                                for task_id, output in outputs.items()
                            }
    except (httpx.HTTPError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if current_task is not None:
        sys.stdout.write("\n")
    if args.show_ttft and first_visible_at is not None:
        print(f"TTFT {(first_visible_at - started) * 1000:.1f} ms", file=sys.stderr)
    if not failed and target_path is not None and solution_path is not None:
        sections = "\n\n".join(
            f"## {task_id}\n\n{output}"
            for task_id, output in result_outputs.items()
        ) or "## Result\n\nThe DAG completed without a textual result."
        solution_path.write_text(
            "---\nkind: solution\nstatus: ready\nsource: engine\n---\n\n"
            f"# {target_path.stem} Tech Solution\n\n"
            f"Source: [{target_path.name}]({target_path.name})\n\n"
            f"{sections}\n",
            encoding="utf-8",
        )
        print(f"Generated solution: {solution_path}", file=sys.stderr)
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog=Path(sys.argv[0]).name,
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
    p_run = sub.add_parser("run", help="Execute an in-memory DAG through the streaming engine")
    p_run.add_argument("prompt", nargs="+", help="Command sent to the agent DAG")
    p_run.add_argument("--target", help="Markdown requirement document read by the agent DAG")
    p_run.add_argument("--plan", help="Optional JSON DAG plan")
    p_run.add_argument(
        "--server",
        default=os.environ.get("INKDESK_SERVER_URL", "http://127.0.0.1:8000"),
        help="Inkdesk server base URL",
    )
    p_run.add_argument("--show-ttft", action="store_true", help="Print time to first SSE event")

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
