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
import sys
from pathlib import Path

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


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="inkdesk-skill",
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
