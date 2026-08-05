from __future__ import annotations

import asyncio
import json
from hashlib import sha256
from typing import Any

from inkdesk_server.harness.models import EvidenceBundle, EvidenceItem, EvidenceStatus, utc_now
from inkdesk_server.harness.redaction import redact_value
from inkdesk_server.harness.run_store import RunStore


_STAGE_ENVELOPE = {
    "specialist-structure": "projectHarness",
    "specialist-testing": "deliveryEvidence",
    "specialist-security": "agentCustomize",
    "lead-reconcile": "leadSummary",
}


class EvidenceLedger:
    def __init__(self, store: RunStore, run_id: str, bundle: EvidenceBundle):
        self.store = store
        self.run_id = run_id
        self.bundle = bundle
        self._lock = asyncio.Lock()

    async def record_tool_result(
        self,
        *,
        stage_id: str,
        session_id: str,
        tool_use_id: str,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_response: Any,
    ) -> tuple[str, Any]:
        redacted_input = redact_value(tool_input)
        redacted_response = redact_value(tool_response)
        raw = json.dumps(tool_response, ensure_ascii=False, sort_keys=True, default=str)
        digest = sha256(raw.encode("utf-8")).hexdigest()
        evidence_id = "E-A-" + sha256(
            f"{self.run_id}|{stage_id}|{tool_use_id}|{digest}".encode("utf-8")
        ).hexdigest()[:12]
        excerpt = json.dumps(
            {"input": redacted_input, "output": redacted_response},
            ensure_ascii=False,
            default=str,
        )[:8192]
        item = EvidenceItem(
            id=evidence_id,
            source=f"agent-tool://{stage_id}/{tool_use_id}",
            contentHash=digest,
            capturedAt=utc_now(),
            repoHead=self.bundle.repoHead,
            excerpt=excerpt,
            collector="agent-tool",
            stageId=stage_id,
            sessionId=session_id,
            toolUseId=tool_use_id,
            toolName=tool_name,
        )
        async with self._lock:
            envelope_name = _STAGE_ENVELOPE.get(stage_id, "leadSummary")
            envelope = self.bundle.envelopes[envelope_name]
            if evidence_id not in {existing.id for existing in envelope.evidence}:
                envelope.evidence.append(item)
            envelope.status = EvidenceStatus.AVAILABLE
            self.bundle.sessionEvidenceStatus = EvidenceStatus.AVAILABLE
            self.store.write_json(self.run_id, "evidence.json", self.bundle)
        return evidence_id, redacted_response

    async def record_session_summary(self, summary: dict[str, Any]) -> None:
        async with self._lock:
            envelope = self.bundle.envelopes["leadSummary"]
            envelope.summaryFacts.append(
                f"{summary.get('stageId', 'agent')} used {summary.get('toolCount', 0)} tools "
                f"across {summary.get('turns', 'unknown')} turns."
            )
            self.bundle.sessionEvidenceStatus = EvidenceStatus.AVAILABLE
            self.store.write_json(self.run_id, "evidence.json", self.bundle)
