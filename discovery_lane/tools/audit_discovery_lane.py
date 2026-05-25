#!/usr/bin/env python3
"""Read-only audit for Discovery Lane state and safety boundaries."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable, Optional


REQUIRED_FOLDERS = (
    "inbox",
    "accepted_reports",
    "rejected_reports",
    "review_queue",
    "phase_packets",
    "worker_prompts",
    "manifests",
    "approved_packets",
    "rejected_packets",
    "execution_handoffs",
    "execution_queues",
    "execution_queue_reports",
    "approval_records",
    "branch_plans",
    "research_sets",
    "research_set_manifests",
    "intake_reports",
    "research_set_ingests",
    "research_set_ingest_reports",
    "slash_commands",
    "templates",
    "schemas",
    "tools",
)

REQUIRED_TEMPLATES = (
    "research_report_template.md",
    "phase_packet_template.md",
    "worker_prompt_template.md",
    "daily_progress_report_template.md",
)

REQUIRED_SCHEMAS = (
    "research_report_contract.md",
    "phase_packet_contract.md",
)

REQUIRED_TOOLS = (
    "ingest_research_reports.py",
    "approve_phase_packet.py",
    "discovery_command.py",
    "audit_discovery_lane.py",
    "intake_research_set.py",
    "ingest_research_set.py",
    "approve_research_set.py",
    "build_execution_queue.py",
)

REQUIRED_SLASH_DOCS = (
    "discovery_commands.md",
    "discovery_commands.json",
)

REQUIRED_HANDOFF_FILES = (
    "HANDOFF.md",
    "phase_packet.md",
    "worker_prompt.md",
    "approval_record.json",
    "branch_plan.json",
    "README.md",
)

READY = "READY_FOR_HUMAN_REVIEW"
NOT_READY = "NOT_EXECUTION_READY"
APPROVED = "APPROVED_FOR_EXECUTION_HANDOFF"
APPROVED_OVERRIDE = "APPROVED_WITH_OVERRIDES"
REJECTED = "REJECTED_BY_HUMAN"
PLANNED_BRANCH = "PLANNED_NOT_CREATED"
SET_READY = "READY_FOR_INGEST"
SET_NEEDS_DECISION = "NEEDS_HUMAN_DECISION"
SET_NOT_READY = "NOT_READY"
VALID_SET_STATUSES = {SET_READY, SET_NEEDS_DECISION, SET_NOT_READY}
VALID_INGEST_STATUSES = {
    "INGESTED",
    "NOT_INGESTED_SOURCE_CHANGED",
    "NOT_INGESTED_SET_NOT_READY",
    "NOT_INGESTED_MISSING_SOURCE",
    "NOT_INGESTED_VALIDATION_FAILED",
}
VALID_QUEUE_STATUSES = {
    "READY_FOR_EXECUTION_LANE",
    "EMPTY_NO_APPROVED_HANDOFFS",
    "BLOCKED_MISSING_HANDOFFS",
    "BLOCKED_INVALID_BRANCH_PLANS",
    "BLOCKED_INVALID_APPROVALS",
}
REQUIRED_RESEARCH_SET_FIELDS = {
    "set_id",
    "source_input_path",
    "created_timestamp",
    "report_count",
    "reports",
    "duplicate_phase_ids",
    "missing_or_unclear_phase_ids",
    "set_status",
    "recommended_next_action",
    "generated_by",
}
REQUIRED_INGEST_FIELDS = {
    "set_id",
    "source_research_set_manifest",
    "ingest_timestamp",
    "report_count",
    "source_reports",
    "generated_phase_packets",
    "generated_worker_prompts",
    "generated_manifests",
    "checksum_verification_status",
    "ingest_status",
    "errors",
    "warnings",
    "generated_by",
}
REQUIRED_QUEUE_FIELDS = {
    "set_id",
    "source_research_set_ingest_manifest",
    "generated_timestamp",
    "queue_status",
    "queued_phase_count",
    "excluded_phase_count",
    "queued_phases",
    "excluded_phases",
    "errors",
    "warnings",
    "generated_by",
}


class Audit:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def load_json(path: Path, audit: Audit, label: str) -> Optional[dict[str, object]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        audit.error(f"{label} is not valid JSON: {path} ({exc})")
        return None
    if not isinstance(data, dict):
        audit.error(f"{label} JSON must be an object: {path}")
        return None
    return data


def check_required_path(root: Path, relative: str, audit: Audit) -> None:
    path = root / relative
    if not path.exists():
        audit.error(f"missing required path: {relative}")


def packet_status(packet_path: Path) -> str:
    text = packet_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^## Current Status\s+(.+?)(?:\n## |\Z)", text, flags=re.MULTILINE | re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip().splitlines()[0].strip()


def text_allows_permission(text: str, name: str) -> bool:
    patterns = (
        rf"{name}_permission:\s*true",
        rf"{name}\s*permission:\s*true",
        rf"{name}:\s*true",
        rf"{name}_allowed:\s*true",
    )
    lowered = text.lower()
    return any(re.search(pattern, lowered) for pattern in patterns)


def audit_discovery_lane(root: Path, state_root: Optional[Path] = None) -> tuple[Audit, dict[str, int]]:
    audit = Audit()
    state = state_root or root
    counts = {
        "manifests": 0,
        "approval_records": 0,
        "branch_plans": 0,
        "handoffs": 0,
        "worker_prompts": 0,
        "phase_packets": 0,
        "research_set_manifests": 0,
        "intake_reports": 0,
        "research_set_ingests": 0,
        "research_set_ingest_reports": 0,
        "approval_review_plans": 0,
        "execution_queues": 0,
        "execution_queue_reports": 0,
    }

    for folder in REQUIRED_FOLDERS:
        check_required_path(root, folder, audit)
    for template in REQUIRED_TEMPLATES:
        check_required_path(root, f"templates/{template}", audit)
    for schema in REQUIRED_SCHEMAS:
        check_required_path(root, f"schemas/{schema}", audit)
    for tool in REQUIRED_TOOLS:
        check_required_path(root, f"tools/{tool}", audit)
    for doc in REQUIRED_SLASH_DOCS:
        check_required_path(root, f"slash_commands/{doc}", audit)

    slash_json = root / "slash_commands" / "discovery_commands.json"
    if slash_json.exists():
        load_json(slash_json, audit, "slash command spec")

    for path in sorted((state / "research_set_manifests").glob("*.json")):
        counts["research_set_manifests"] += 1
        data = load_json(path, audit, "research set manifest")
        if not data:
            continue
        missing_fields = sorted(REQUIRED_RESEARCH_SET_FIELDS.difference(data))
        if missing_fields:
            audit.error(f"research set manifest missing fields {missing_fields}: {path}")
        status = str(data.get("set_status", ""))
        if status not in VALID_SET_STATUSES:
            audit.error(f"research set manifest has invalid set_status {status!r}: {path}")
        reports = data.get("reports", [])
        if not isinstance(reports, list):
            audit.error(f"research set manifest reports must be a list: {path}")
            reports = []
        phase_ids: list[str] = []
        for index, report in enumerate(reports):
            if not isinstance(report, dict):
                audit.error(f"research set report entry must be an object at index {index}: {path}")
                continue
            if not report.get("sha256"):
                audit.error(f"research set report is missing sha256 at index {index}: {path}")
            phase_id = str(report.get("detected_phase_id", "")).strip()
            if phase_id:
                phase_ids.append(phase_id)
        duplicate_ids = sorted({phase_id for phase_id in phase_ids if phase_ids.count(phase_id) > 1})
        manifest_duplicates = sorted(str(value) for value in data.get("duplicate_phase_ids", []) or [])
        if duplicate_ids and not manifest_duplicates:
            audit.error(f"research set has duplicate phase ids that were not surfaced: {path}")
        if duplicate_ids and status == SET_READY:
            audit.error(f"research set with duplicate phase ids is marked READY_FOR_INGEST: {path}")
        if data.get("missing_or_unclear_phase_ids") and status == SET_READY:
            audit.error(f"research set with unclear phase ids is marked READY_FOR_INGEST: {path}")
        if status == SET_NOT_READY and data.get("recommended_next_action") == "Run `ws discovery ingest`.":
            audit.error(f"NOT_READY research set recommends ingest without remediation: {path}")

    counts["intake_reports"] = len(list((state / "intake_reports").glob("*.md")))
    counts["research_set_ingest_reports"] = len(list((state / "research_set_ingest_reports").glob("*.md")))

    for path in sorted((state / "research_set_ingests").glob("*.json")):
        counts["research_set_ingests"] += 1
        data = load_json(path, audit, "research set ingest manifest")
        if not data:
            continue
        missing_fields = sorted(REQUIRED_INGEST_FIELDS.difference(data))
        if missing_fields:
            audit.error(f"research set ingest manifest missing fields {missing_fields}: {path}")
        status = str(data.get("ingest_status", ""))
        if status not in VALID_INGEST_STATUSES:
            audit.error(f"research set ingest manifest has invalid ingest_status {status!r}: {path}")
        if not data.get("checksum_verification_status"):
            audit.error(f"research set ingest manifest missing checksum verification status: {path}")
        if status == "INGESTED":
            for key, label in (
                ("generated_phase_packets", "phase packet"),
                ("generated_worker_prompts", "worker prompt"),
                ("generated_manifests", "phase manifest"),
            ):
                values = data.get(key, [])
                if not isinstance(values, list) or not values:
                    audit.error(f"INGESTED record has no generated {label} entries: {path}")
                    continue
                for value in values:
                    target = state / str(value)
                    if not target.exists():
                        audit.error(f"INGESTED record references missing {label}: {target}")
        else:
            errors = data.get("errors", [])
            warnings = data.get("warnings", [])
            if not errors and not warnings:
                audit.error(f"NOT_INGESTED record has no errors or warnings: {path}")
        for forbidden in ("approvals_created", "handoffs_created", "branches_created"):
            if data.get(forbidden) is True:
                audit.error(f"research set ingest manifest claims {forbidden}: {path}")

    for path in sorted((state / "approval_records").glob("*_approval_review_plan.md")):
        counts["approval_review_plans"] += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        if "This review plan is advisory only." not in text:
            audit.error(f"approval review plan does not declare advisory-only status: {path}")
        if "This report is not an approval record." not in text:
            audit.error(f"approval review plan does not declare non-approval boundary: {path}")
        if "Batch approval is intentionally not implemented." not in text:
            audit.error(f"approval review plan does not declare batch approval boundary: {path}")

    for path in sorted((state / "approval_records").glob("*_approval_review_plan.json")):
        audit.error(f"dry-run approval review must not create JSON approval artifacts: {path}")

    counts["execution_queue_reports"] = len(list((state / "execution_queue_reports").glob("*.md")))

    for path in sorted((state / "execution_queues").glob("*.json")):
        counts["execution_queues"] += 1
        data = load_json(path, audit, "execution queue manifest")
        if not data:
            continue
        missing_fields = sorted(REQUIRED_QUEUE_FIELDS.difference(data))
        if missing_fields:
            audit.error(f"execution queue manifest missing fields {missing_fields}: {path}")
        status = str(data.get("queue_status", ""))
        if status not in VALID_QUEUE_STATUSES:
            audit.error(f"execution queue manifest has invalid queue_status {status!r}: {path}")
        queued = data.get("queued_phases", [])
        excluded = data.get("excluded_phases", [])
        if not isinstance(queued, list):
            audit.error(f"execution queue queued_phases must be a list: {path}")
            queued = []
        if not isinstance(excluded, list):
            audit.error(f"execution queue excluded_phases must be a list: {path}")
            excluded = []
        for index, row in enumerate(queued):
            if not isinstance(row, dict):
                audit.error(f"execution queue queued phase must be an object at index {index}: {path}")
                continue
            for field, label in (
                ("handoff_bundle", "handoff bundle"),
                ("branch_plan", "branch plan"),
                ("approval_record", "approval record"),
            ):
                ref = str(row.get(field, ""))
                if not ref or not (state / ref).exists():
                    audit.error(f"queued phase references missing {label}: {ref} ({path})")
            if row.get("execution_status") != "NOT_STARTED":
                audit.error(f"queued phase has unsupported execution_status: {path}")
            if row.get("branch_status") != PLANNED_BRANCH:
                audit.error(f"queued phase branch_status is not PLANNED_NOT_CREATED: {path}")
            if row.get("branches_created") is True:
                audit.error(f"queued phase claims branches were created: {path}")
        for index, row in enumerate(excluded):
            if not isinstance(row, dict):
                audit.error(f"execution queue excluded phase must be an object at index {index}: {path}")
                continue
            if not str(row.get("reason", "")).strip():
                audit.error(f"excluded phase is missing reason: {path}")
        for forbidden in ("approvals_created", "handoffs_created", "branches_created", "worker_prompts_executed", "git_actions_performed"):
            if data.get(forbidden) is True:
                audit.error(f"execution queue manifest claims {forbidden}: {path}")

    for path in sorted((state / "execution_queue_reports").glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if "This queue plan is not execution approval." not in text:
            audit.error(f"execution queue report does not declare non-approval boundary: {path}")
        if "This queue plan does not create branches." not in text:
            audit.error(f"execution queue report does not declare branch boundary: {path}")
        if "This queue plan does not run worker prompts." not in text:
            audit.error(f"execution queue report does not declare no-execution boundary: {path}")

    manifests: dict[str, dict[str, object]] = {}
    for path in sorted((state / "manifests").glob("*.json")):
        counts["manifests"] += 1
        data = load_json(path, audit, "manifest")
        if data:
            manifests[str(data.get("phase_id", path.stem))] = data

    approval_records = []
    for path in sorted((state / "approval_records").glob("*.json")):
        counts["approval_records"] += 1
        data = load_json(path, audit, "approval record")
        if data:
            data["_path"] = str(path)
            approval_records.append(data)

    branch_plans = []
    for path in sorted((state / "branch_plans").glob("*.json")):
        counts["branch_plans"] += 1
        data = load_json(path, audit, "branch plan")
        if not data:
            continue
        data["_path"] = str(path)
        branch_plans.append(data)
        if data.get("branch_status") != PLANNED_BRANCH:
            audit.error(f"branch plan has unsupported branch_status: {path}")
        for permission in ("commit_allowed", "push_allowed", "merge_allowed"):
            if data.get(permission) is True:
                audit.warn(f"branch plan explicitly allows {permission}: {path}")
            elif data.get(permission) is not False:
                audit.error(f"branch plan missing false {permission}: {path}")

    for path in sorted((state / "worker_prompts").glob("*.md")):
        counts["worker_prompts"] += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        for permission in ("commit", "push", "merge"):
            if text_allows_permission(text, permission):
                audit.error(f"worker prompt appears to allow {permission} by default: {path}")

    packet_statuses: dict[str, str] = {}
    for path in sorted((state / "phase_packets").glob("*.md")):
        counts["phase_packets"] += 1
        packet_statuses[path.name] = packet_status(path)

    for record in approval_records:
        status = str(record.get("approval_status", ""))
        packet_validation_status = str(record.get("packet_validation_status", ""))
        if status in {APPROVED, APPROVED_OVERRIDE}:
            if packet_validation_status == NOT_READY and status != APPROVED_OVERRIDE:
                audit.error(f"NOT_EXECUTION_READY packet approved without override: {record.get('_path')}")
            if packet_validation_status != READY and status == APPROVED:
                audit.error(f"non-ready packet approved without override: {record.get('_path')}")
        if status == REJECTED and record.get("handoff_bundle"):
            audit.error(f"rejected record points to a handoff bundle: {record.get('_path')}")

    rejected_names = {path.name for path in (state / "rejected_packets").glob("*.md")}
    for handoff_dir in sorted((state / "execution_handoffs").glob("*")):
        if not handoff_dir.is_dir():
            continue
        counts["handoffs"] += 1
        for required in REQUIRED_HANDOFF_FILES:
            if not (handoff_dir / required).exists():
                audit.error(f"handoff missing {required}: {handoff_dir}")
        if (handoff_dir / "phase_packet.md").name in rejected_names:
            audit.error(f"rejected packet appears in handoff bundle: {handoff_dir}")
        handoff_text = (handoff_dir / "HANDOFF.md").read_text(encoding="utf-8", errors="replace") if (handoff_dir / "HANDOFF.md").exists() else ""
        if "PLANNED_NOT_CREATED" not in handoff_text:
            audit.error(f"handoff does not declare PLANNED_NOT_CREATED branch status: {handoff_dir}")
        branch_plan = load_json(handoff_dir / "branch_plan.json", audit, "handoff branch plan") if (handoff_dir / "branch_plan.json").exists() else None
        if branch_plan and branch_plan.get("branch_status") != PLANNED_BRANCH:
            audit.error(f"handoff branch_plan.json has unsupported branch_status: {handoff_dir}")
        approval = load_json(handoff_dir / "approval_record.json", audit, "handoff approval record") if (handoff_dir / "approval_record.json").exists() else None
        if approval and approval.get("approval_status") not in {APPROVED, APPROVED_OVERRIDE}:
            audit.error(f"handoff approval record is not approved: {handoff_dir}")

    return audit, counts


def render_audit(root: Path, state_root: Path, audit: Audit, counts: dict[str, int]) -> str:
    status = "FAIL" if audit.errors else "PASS"
    lines = [
        "# Discovery Lane Audit",
        "",
        f"- root: `{root}`",
        f"- state_root: `{state_root}`",
        f"- result: {status}",
        f"- errors: {len(audit.errors)}",
        f"- warnings: {len(audit.warnings)}",
        "",
        "## Counts",
        "",
    ]
    for key in sorted(counts):
        lines.append(f"- {key}: {counts[key]}")
    lines.extend(["", "## Errors", ""])
    lines.extend([f"- {error}" for error in audit.errors] or ["None."])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {warning}" for warning in audit.warnings] or ["None."])
    lines.extend(
        [
            "",
            "## Execution Boundary",
            "",
            "- Audit is read-only.",
            "- No worker prompt was executed.",
            "- No branch was created, checked out, pushed, merged, or deleted.",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit Discovery Lane state without writing files.")
    parser.add_argument("--root", default="discovery_lane", help="Discovery Lane root to audit.")
    parser.add_argument("--state-root", default="", help="Optional generated state root, useful for example output audits.")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root)
    state_root = Path(args.state_root) if args.state_root else root
    audit, counts = audit_discovery_lane(root, state_root)
    print(render_audit(root, state_root, audit, counts))
    return 1 if audit.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
