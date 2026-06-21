from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from inkdesk_server.core.config import Settings
from inkdesk_server.vault import VaultService

EVALS_DIR = "evals"
GOLDEN_DIR = "evals/golden"
RUNS_DIR = "evals/runs"
GOLDEN_CANDIDATES_FILE = "evals/golden/candidates.json"
SCHEMA_VERSION = "1.0.0"

MAX_ID_LENGTH = 200
MAX_STRING_LENGTH = 5000
MAX_MANIFEST_SIZE = 500 * 1024  # 500 KB


@dataclass
class EvaluationService:
    settings: Settings
    vault: VaultService

    def save_golden_tasks(self, tasks: list[dict]) -> str:
        """Persist golden task candidates to evals/golden/candidates.json."""
        self._ensure_dir(GOLDEN_DIR)
        payload = {
            "schemaVersion": SCHEMA_VERSION,
            "tasks": tasks,
        }
        self._validate_golden_tasks(tasks)
        self.vault.write_vault_file(
            GOLDEN_CANDIDATES_FILE,
            json.dumps(payload, ensure_ascii=False, indent=2),
        )
        return GOLDEN_CANDIDATES_FILE

    def get_golden_tasks(self) -> dict:
        """Read and validate golden task candidates."""
        try:
            raw = self.vault.read_vault_file(GOLDEN_CANDIDATES_FILE)
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return {"schemaVersion": SCHEMA_VERSION, "tasks": []}

        if not isinstance(data.get("tasks"), list):
            return {"schemaVersion": SCHEMA_VERSION, "tasks": []}

        data["tasks"] = [t for t in data["tasks"] if self._validate_task_for_response(t)]
        return data

    def create_eval_run(self, task_ids: list[str], rubric_ids: list[str],
                        gate_status: str, health_run_id: str | None = None) -> dict:
        """Create an isolated Evaluation Run manifest. Refuses if gate is FAILED."""
        if gate_status == "FAILED":
            raise ValueError("Schema gate is FAILED; cannot create Evaluation Run.")

        if not task_ids:
            raise ValueError("At least one task ID is required.")

        if len(task_ids) > 50 or len(rubric_ids) > 10:
            raise ValueError("Too many task/rubric IDs.")

        eval_run_id = self._generate_eval_run_id()
        output_dir = f"{RUNS_DIR}/{eval_run_id}"
        self._ensure_dir(f"{output_dir}/outputs")

        manifest = {
            "evalRunId": eval_run_id,
            "schemaVersion": SCHEMA_VERSION,
            "taskIds": task_ids,
            "rubricIds": rubric_ids,
            "vaultCommitHash": None,
            "ruleVersion": "1.0.0",
            "gateStatusAtStart": gate_status,
            "healthRunId": health_run_id,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "status": "created",
            "outputDir": output_dir,
        }

        self.vault.write_vault_file(
            f"{output_dir}/manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2),
        )
        return manifest

    def get_eval_run(self, eval_run_id: str) -> dict | None:
        """Read an evaluation run manifest."""
        self._validate_id(eval_run_id)
        path = f"{RUNS_DIR}/{eval_run_id}/manifest.json"
        try:
            raw = self.vault.read_vault_file(path)
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return None
        return data

    def save_rubric(self, rubric: dict) -> str:
        """Save a rubric to evals/rubrics/<id>.json."""
        rubric_id = rubric.get("id", "")
        self._validate_id(rubric_id)
        self._ensure_dir("evals/rubrics")
        rubric["schemaVersion"] = SCHEMA_VERSION
        if "createdAt" not in rubric:
            rubric["createdAt"] = datetime.now(timezone.utc).isoformat()
        self._validate_rubric(rubric)
        path = f"evals/rubrics/{rubric_id}.json"
        self.vault.write_vault_file(path, json.dumps(rubric, ensure_ascii=False, indent=2))
        return path

    def get_rubric(self, rubric_id: str) -> dict | None:
        """Read a rubric by ID."""
        self._validate_id(rubric_id)
        path = f"evals/rubrics/{rubric_id}.json"
        try:
            raw = self.vault.read_vault_file(path)
            return json.loads(raw)
        except (OSError, json.JSONDecodeError):
            return None

    def _validate_golden_tasks(self, tasks: list[dict]) -> None:
        seen_ids = set()
        for t in tasks:
            task_id = t.get("id", "")
            if not task_id:
                raise ValueError("Each task must have an 'id'")
            self._validate_id(task_id)
            if task_id in seen_ids:
                raise ValueError(f"Duplicate task ID: {task_id}")
            seen_ids.add(task_id)
            if not t.get("title"):
                raise ValueError(f"Task {task_id}: title is required")
            if not isinstance(t.get("inputs"), dict):
                raise ValueError(f"Task {task_id}: inputs must be a dict")
            if not isinstance(t.get("expectedEvidence"), list):
                raise ValueError(f"Task {task_id}: expectedEvidence must be a list")
            if not t.get("source"):
                raise ValueError(f"Task {task_id}: source is required")

    def _validate_task_for_response(self, task: dict) -> bool:
        if not task.get("id") or not task.get("title"):
            return False
        return True

    def _validate_rubric(self, rubric: dict) -> None:
        dims = rubric.get("dimensions", [])
        if not isinstance(dims, list) or len(dims) == 0:
            raise ValueError("Rubric must have at least one dimension")
        for d in dims:
            if not d.get("name"):
                raise ValueError("Each dimension must have a 'name'")
            if not isinstance(d.get("maxScore"), (int, float)):
                raise ValueError("Each dimension must have a 'maxScore'")

    def _ensure_dir(self, relative_dir: str) -> None:
        dir_path = self.vault.root / relative_dir
        dir_path.mkdir(parents=True, exist_ok=True)

    def _generate_eval_run_id(self) -> str:
        now_utc = datetime.now(timezone.utc)
        ts = now_utc.strftime("%Y%m%dT%H%M%SZ")
        return f"eval-{ts}"

    def _validate_id(self, id_str: str) -> None:
        if not id_str or not id_str.strip():
            raise ValueError("ID is required")
        if not all(c.isalnum() or c in "_-." for c in id_str):
            raise ValueError(f"Invalid ID: {id_str}")
        if len(id_str) > MAX_ID_LENGTH:
            raise ValueError(f"ID too long: {id_str}")
