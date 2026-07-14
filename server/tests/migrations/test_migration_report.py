from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path

import pytest


F02_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts" / "f02"


def _build_migration_report():
    module_path = F02_SCRIPTS / "build-migration-report.py"
    specification = importlib.util.spec_from_file_location("build_migration_report", module_path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module.build_migration_report


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_report_is_pass_only_when_f01_and_every_check_pass(tmp_path: Path):
    build_migration_report = _build_migration_report()

    f01_manifest = tmp_path / "f01-manifest.json"
    artifact = tmp_path / "fresh-schema.json"
    _write_json(f01_manifest, {"overallStatus": "PASS", "runId": "f01-run"})
    artifact.write_text("fresh schema", encoding="utf-8")

    report = build_migration_report(
        run_id="f02-run",
        f01_manifest=f01_manifest,
        checks=[{"name": "fresh-upgrade", "status": "PASS", "artifacts": [artifact]}],
    )

    assert report["overallStatus"] == "PASS"
    assert report["f01"]["runId"] == "f01-run"
    assert report["checks"][0]["artifacts"][0]["sha256"]


def test_report_is_fail_when_any_check_fails(tmp_path: Path):
    build_migration_report = _build_migration_report()

    f01_manifest = tmp_path / "f01-manifest.json"
    _write_json(f01_manifest, {"overallStatus": "PASS", "runId": "f01-run"})

    report = build_migration_report(
        run_id="f02-run",
        f01_manifest=f01_manifest,
        checks=[{"name": "adoption", "status": "FAIL", "artifacts": []}],
    )

    assert report["overallStatus"] == "FAIL"


def test_report_rejects_non_pass_f01_evidence(tmp_path: Path):
    build_migration_report = _build_migration_report()

    f01_manifest = tmp_path / "f01-manifest.json"
    _write_json(f01_manifest, {"overallStatus": "FAIL", "runId": "f01-run"})

    with pytest.raises(ValueError, match="PASS"):
        build_migration_report(run_id="f02-run", f01_manifest=f01_manifest, checks=[])
