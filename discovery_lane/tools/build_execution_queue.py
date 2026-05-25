#!/usr/bin/env python3
"""Build a non-executing execution queue plan for one Discovery research set.

The queue manifest is the final Discovery Lane planning artifact before a
future execution lane. It records approved handoffs and planned branches, but it
does not execute worker prompts, create or checkout branches, approve packets,
commit, push, merge, or call models.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import approve_phase_packet
import ingest_research_reports


INGESTED = "INGESTED"
APPROVED = "APPROVED_FOR_EXECUTION_HANDOFF"
APPROVED_OVERRIDE = "APPROVED_WITH_OVERRIDES"
REJECTED = "REJECTED_BY_HUMAN"
READY = "READY_FOR_HUMAN_REVIEW"
NOT_STARTED = "NOT_STARTED"
PLANNED_BRANCH = "PLANNED_NOT_CREATED"

QUEUE_READY = "READY_FOR_EXECUTION_LANE"
QUEUE_EMPTY = "EMPTY_NO_APPROVED_HANDOFFS"
QUEUE_MISSING_HANDOFFS = "BLOCKED_MISSING_HANDOFFS"
QUEUE_INVALID_BRANCH_PLANS = "BLOCKED_INVALID_BRANCH_PLANS"
QUEUE_INVALID_APPROVALS = "BLOCKED_INVALID_APPROVALS"
VALID_QUEUE_STATUSES = {
    QUEUE_READY,
    QUEUE_EMPTY,
    QUEUE_MISSING_HANDOFFS,
    QUEUE_INVALID_BRANCH_PLANS,
    QUEUE_INVALID_APPROVALS,
}

OUTPUT_DIRS = ("execution_queues", "execution_queue_reports")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_relative(path: Optional[Path], root: Path) -> str:
    return ingest_research_reports.safe_relative(path, root) if path else ""


def ensure_output_dirs(root: Path) -> None:
    for directory in OUTPUT_DIRS:
        (root / directory).mkdir(parents=True, exist_ok=True)


def resolve_path(root: Path, value: str) -> Path:
    raw = Path(value)
    candidates = [raw] if raw.is_absolute() else [root / raw, Path.cwd() / raw]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def load_ingest_manifest(root: Path, set_id: str) -> tuple[dict[str, object], Path]:
    path = root / "research_set_ingests" / f"{set_id}_ingest_manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"research set ingest manifest not found: {path}")
    data = load_json(path)
    if str(data.get("ingest_status", "")) != INGESTED:
        raise PermissionError(f"research set {set_id!r} has ingest_status {data.get('ingest_status', '')}; expected INGESTED")
    return data, path


def load_json_records(directory: Path, pattern: str) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in sorted(directory.glob(pattern)):
        try:
            data = load_json(path)
        except Exception:
            continue
        data["_path"] = safe_relative(path, directory.parent)
        records.append(data)
    return records


def packet_fields(packet_path: Path) -> tuple[str, str, str, str, str]:
    if not packet_path.exists():
        return "", "", "UNKNOWN_STATUS", "", ""
    text = packet_path.read_text(encoding="utf-8", errors="replace")
    sections = approve_phase_packet.parse_markdown_sections(text)
    phase_id = approve_phase_packet.section(sections, "Phase ID").splitlines()[0].strip()
    phase_title = approve_phase_packet.section(sections, "Phase Title").splitlines()[0].strip()
    validation_status = approve_phase_packet.section(sections, "Current Status").splitlines()[0].strip() or "UNKNOWN_STATUS"
    dependencies = approve_phase_packet.section(sections, "Dependencies").strip()
    risks = approve_phase_packet.section(sections, "Risks").strip()
    return phase_id, phase_title, validation_status, dependencies, risks


def matching_approval(records: list[dict[str, object]], phase_id: str, packet_rel: str) -> Optional[dict[str, object]]:
    exact = [record for record in records if str(record.get("source_phase_packet", "")) == packet_rel]
    candidates = exact or [record for record in records if str(record.get("phase_id", "")) == phase_id]
    if not candidates:
        return None
    return sorted(candidates, key=lambda record: str(record.get("approval_timestamp", "")))[-1]


def matching_branch_plan(root: Path, approval: dict[str, object], phase_id: str) -> tuple[Optional[dict[str, object]], Optional[Path]]:
    plan_ref = str(approval.get("branch_plan", "")).strip()
    if plan_ref:
        path = resolve_path(root, plan_ref)
        if path.exists():
            return load_json(path), path
        return None, path
    for path in sorted((root / "branch_plans").glob("*_branch_plan.json")):
        try:
            data = load_json(path)
        except Exception:
            continue
        if str(data.get("phase_id", "")) == phase_id:
            return data, path
    return None, None


def phase_order_key(row: dict[str, object]) -> tuple[int, str]:
    phase_id = str(row.get("phase_id", ""))
    match = re.search(r"(\d+)", phase_id)
    if match:
        return int(match.group(1)), phase_id
    return 999999, phase_id


def exclusion(phase_id: str, phase_title: str, packet_rel: str, reason: str) -> dict[str, object]:
    return {
        "phase_id": phase_id,
        "phase_title": phase_title,
        "phase_packet": packet_rel,
        "reason": reason,
    }


def build_phase_rows(root: Path, ingest_manifest: dict[str, object]) -> tuple[list[dict[str, object]], list[dict[str, object]], list[str], list[str]]:
    packets = ingest_manifest.get("generated_phase_packets", [])
    prompts = ingest_manifest.get("generated_worker_prompts", [])
    manifests = ingest_manifest.get("generated_manifests", [])
    if not isinstance(packets, list) or not isinstance(prompts, list) or not isinstance(manifests, list):
        raise ValueError("ingest manifest generated artifact fields must be lists")

    approvals = load_json_records(root / "approval_records", "*.json")
    queued: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []
    errors: list[str] = []
    warnings: list[str] = []

    max_len = max(len(packets), len(prompts), len(manifests))
    for index in range(max_len):
        packet_rel = str(packets[index]) if index < len(packets) else ""
        prompt_rel = str(prompts[index]) if index < len(prompts) else ""
        manifest_rel = str(manifests[index]) if index < len(manifests) else ""
        packet_path = resolve_path(root, packet_rel) if packet_rel else Path("")
        prompt_path = resolve_path(root, prompt_rel) if prompt_rel else Path("")
        phase_manifest_path = resolve_path(root, manifest_rel) if manifest_rel else Path("")
        phase_id, phase_title, validation_status, dependencies, risks = packet_fields(packet_path)
        phase_label = phase_id or packet_rel or f"index_{index}"

        if not packet_rel or not packet_path.exists():
            errors.append(f"missing generated phase packet for {phase_label}")
            excluded.append(exclusion(phase_id, phase_title, packet_rel, "missing generated phase packet"))
            continue
        if validation_status != READY:
            excluded.append(exclusion(phase_id, phase_title, packet_rel, f"packet validation status is {validation_status}"))
            continue

        packet_rel_resolved = safe_relative(packet_path, root)
        approval = matching_approval(approvals, phase_id, packet_rel_resolved)
        approval_status = str(approval.get("approval_status", "")) if approval else "PENDING_HUMAN_REVIEW"
        if approval_status == REJECTED:
            excluded.append(exclusion(phase_id, phase_title, packet_rel_resolved, "packet was rejected by human"))
            continue
        if approval_status not in {APPROVED, APPROVED_OVERRIDE}:
            excluded.append(exclusion(phase_id, phase_title, packet_rel_resolved, f"packet approval status is {approval_status}"))
            continue

        approval_path = root / str(approval.get("_path", ""))
        if not approval_path.exists():
            errors.append(f"approved phase {phase_id} has missing approval record")
            excluded.append(exclusion(phase_id, phase_title, packet_rel_resolved, "missing approval record"))
            continue

        handoff_ref = str(approval.get("handoff_bundle", "")).strip()
        handoff_path = resolve_path(root, handoff_ref) if handoff_ref else Path("")
        if not handoff_ref or not handoff_path.exists() or not handoff_path.is_dir():
            errors.append(f"approved phase {phase_id} has missing handoff bundle")
            excluded.append(exclusion(phase_id, phase_title, packet_rel_resolved, "missing approved handoff bundle"))
            continue

        branch_plan, branch_plan_path = matching_branch_plan(root, approval, phase_id)
        if not branch_plan or not branch_plan_path or not branch_plan_path.exists():
            errors.append(f"approved phase {phase_id} has missing branch plan")
            excluded.append(exclusion(phase_id, phase_title, packet_rel_resolved, "missing branch plan"))
            continue

        branch_status = str(branch_plan.get("branch_status", ""))
        if branch_status != PLANNED_BRANCH:
            errors.append(f"approved phase {phase_id} has invalid branch_status {branch_status}")
            excluded.append(exclusion(phase_id, phase_title, packet_rel_resolved, f"invalid branch_status {branch_status}"))
            continue

        if not prompt_path.exists():
            errors.append(f"approved phase {phase_id} has missing worker prompt")
            excluded.append(exclusion(phase_id, phase_title, packet_rel_resolved, "missing worker prompt"))
            continue
        if not phase_manifest_path.exists():
            warnings.append(f"approved phase {phase_id} has missing phase manifest")

        queued.append(
            {
                "phase_id": phase_id,
                "phase_title": phase_title,
                "phase_packet": packet_rel_resolved,
                "worker_prompt": safe_relative(prompt_path, root),
                "phase_manifest": safe_relative(phase_manifest_path, root) if phase_manifest_path.exists() else manifest_rel,
                "approval_record": safe_relative(approval_path, root),
                "handoff_bundle": safe_relative(handoff_path, root),
                "branch_plan": safe_relative(branch_plan_path, root),
                "proposed_branch_name": str(branch_plan.get("proposed_branch_name", "")),
                "branch_status": branch_status,
                "execution_status": NOT_STARTED,
                "commit_allowed": bool(branch_plan.get("commit_allowed", False)),
                "push_allowed": bool(branch_plan.get("push_allowed", False)),
                "merge_allowed": bool(branch_plan.get("merge_allowed", False)),
                "dependencies": dependencies or "None recorded.",
                "risk_notes": risks or str(branch_plan.get("conflict_risk_notes", "No specific risk notes recorded.")),
                "recommended_execution_order": 0,
                "branches_created": False,
            }
        )

    queued.sort(key=phase_order_key)
    for order, row in enumerate(queued, start=1):
        row["recommended_execution_order"] = order
    return queued, excluded, errors, warnings


def queue_status(queued: list[dict[str, object]], errors: list[str]) -> str:
    lowered_errors = " ".join(errors).lower()
    if "invalid branch_status" in lowered_errors or "missing branch plan" in lowered_errors:
        return QUEUE_INVALID_BRANCH_PLANS
    if "missing approval record" in lowered_errors:
        return QUEUE_INVALID_APPROVALS
    if "missing handoff" in lowered_errors or "missing worker prompt" in lowered_errors:
        return QUEUE_MISSING_HANDOFFS
    if queued:
        return QUEUE_READY
    return QUEUE_EMPTY


def build_queue_manifest(root: Path, set_id: str) -> dict[str, object]:
    ingest_manifest, ingest_path = load_ingest_manifest(root, set_id)
    queued, excluded, errors, warnings = build_phase_rows(root, ingest_manifest)
    return {
        "set_id": set_id,
        "source_research_set_ingest_manifest": safe_relative(ingest_path, root),
        "generated_timestamp": utc_now(),
        "queue_status": queue_status(queued, errors),
        "queued_phase_count": len(queued),
        "excluded_phase_count": len(excluded),
        "queued_phases": queued,
        "excluded_phases": excluded,
        "errors": errors,
        "warnings": warnings,
        "generated_by": "Discovery Lane execution queue planner v1.6",
        "approvals_created": False,
        "handoffs_created": False,
        "branches_created": False,
        "worker_prompts_executed": False,
        "git_actions_performed": False,
    }


def write_json(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def render_queue_report(queue: dict[str, object]) -> str:
    queued = queue.get("queued_phases", [])
    excluded = queue.get("excluded_phases", [])
    if not isinstance(queued, list):
        queued = []
    if not isinstance(excluded, list):
        excluded = []

    lines = [
        f"# Execution Queue Report: {queue.get('set_id', '')}",
        "",
        "This queue plan is not execution approval.",
        "This queue plan does not create branches.",
        "This queue plan does not run worker prompts.",
        "This queue plan is only an input contract for a future execution lane.",
        "",
        "## Research Set ID",
        "",
        str(queue.get("set_id", "")),
        "",
        "## Queue Status",
        "",
        str(queue.get("queue_status", "")),
        "",
        "## Source Ingest Manifest",
        "",
        f"`{queue.get('source_research_set_ingest_manifest', '')}`",
        "",
        "## Counts",
        "",
        f"- Queued Phase Count: {queue.get('queued_phase_count', 0)}",
        f"- Excluded Phase Count: {queue.get('excluded_phase_count', 0)}",
        "",
        "## Ready Phases",
        "",
    ]
    if queued:
        for row in queued:
            if not isinstance(row, dict):
                continue
            lines.append(f"- {row.get('recommended_execution_order', '')}. {row.get('phase_id', '')}: {row.get('phase_title', '')}")
            lines.append(f"  - handoff: `{row.get('handoff_bundle', '')}`")
            lines.append(f"  - worker_prompt: `{row.get('worker_prompt', '')}`")
            lines.append(f"  - proposed_branch: `{row.get('proposed_branch_name', '')}`")
            lines.append(f"  - branch_status: {row.get('branch_status', '')}")
            lines.append(f"  - execution_status: {row.get('execution_status', '')}")
    else:
        lines.append("None.")

    lines.extend(["", "## Excluded Phases And Reasons", ""])
    if excluded:
        for row in excluded:
            if isinstance(row, dict):
                lines.append(f"- {row.get('phase_id', '')}: {row.get('phase_title', '')}")
                lines.append(f"  - packet: `{row.get('phase_packet', '')}`")
                lines.append(f"  - reason: {row.get('reason', '')}")
    else:
        lines.append("None.")

    lines.extend(["", "## Proposed Branches", ""])
    lines.extend([f"- `{row.get('proposed_branch_name', '')}`" for row in queued if isinstance(row, dict)] or ["None."])

    lines.extend(["", "## Execution Permissions Summary", ""])
    if queued:
        for row in queued:
            if isinstance(row, dict):
                lines.append(
                    f"- {row.get('phase_id', '')}: commit={str(row.get('commit_allowed', False)).lower()}, "
                    f"push={str(row.get('push_allowed', False)).lower()}, merge={str(row.get('merge_allowed', False)).lower()}"
                )
    else:
        lines.append("None.")

    lines.extend(["", "## Dependency Notes", ""])
    lines.extend([f"- {row.get('phase_id', '')}: {row.get('dependencies', '')}" for row in queued if isinstance(row, dict)] or ["None."])

    lines.extend(["", "## Risks", ""])
    lines.extend([f"- {row.get('phase_id', '')}: {row.get('risk_notes', '')}" for row in queued if isinstance(row, dict)] or ["None."])

    lines.extend(
        [
            "",
            "## Required Human Review Before Execution",
            "",
            "Yes. The future execution lane must re-check this queue, handoff bundles, branch plans, and permissions before doing any work.",
            "",
            "## Next Suggested Command Placeholder",
            "",
            "`/discovery execution-start <queue_id>` (planned; not implemented)",
            "",
            "## Execution Boundary",
            "",
            "- No worker prompt was executed.",
            "- No branch was created or checked out.",
            "- No commit, push, or merge was performed.",
            "- No packet was approved by this queue plan.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_queue_records(root: Path, queue: dict[str, object], write_report: bool) -> dict[str, Path]:
    ensure_output_dirs(root)
    set_id = str(queue.get("set_id", "research_set"))
    queue_path = root / "execution_queues" / f"{set_id}_execution_queue.json"
    write_json(queue_path, queue)
    paths = {"queue_manifest": queue_path}
    if write_report:
        report_path = root / "execution_queue_reports" / f"{set_id}_execution_queue_report.md"
        report_path.write_text(render_queue_report(queue), encoding="utf-8", newline="\n")
        paths["queue_report"] = report_path
    return paths


def build_execution_queue(root: Path, set_id: str, write_report: bool = False) -> tuple[dict[str, object], dict[str, Path]]:
    root.mkdir(parents=True, exist_ok=True)
    queue = build_queue_manifest(root, set_id)
    paths = write_queue_records(root, queue, write_report)
    return queue, paths


def render_summary(queue: dict[str, object], paths: dict[str, Path], root: Path) -> str:
    lines = [
        "# Discovery Execution Queue Plan",
        "",
        "No worker prompt was executed. No branch was created. No git action was performed.",
        "",
        f"- set_id: {queue.get('set_id', '')}",
        f"- queue_status: {queue.get('queue_status', '')}",
        f"- queued_phase_count: {queue.get('queued_phase_count', 0)}",
        f"- excluded_phase_count: {queue.get('excluded_phase_count', 0)}",
        "",
        "## Generated Files",
        "",
    ]
    for label, path in sorted(paths.items()):
        lines.append(f"- {label}: `{safe_relative(path, root)}`")
    lines.extend(["", "## Queued Phases", ""])
    queued = queue.get("queued_phases", [])
    if isinstance(queued, list) and queued:
        for row in queued:
            if isinstance(row, dict):
                lines.append(f"- {row.get('recommended_execution_order', '')}. {row.get('phase_id', '')}: {row.get('phase_title', '')}")
                lines.append(f"  branch: `{row.get('proposed_branch_name', '')}`")
                lines.append(f"  handoff: `{row.get('handoff_bundle', '')}`")
    else:
        lines.append("None.")
    lines.extend(["", "## Excluded Phases", ""])
    excluded = queue.get("excluded_phases", [])
    if isinstance(excluded, list) and excluded:
        for row in excluded:
            if isinstance(row, dict):
                lines.append(f"- {row.get('phase_id', '')}: {row.get('reason', '')}")
    else:
        lines.append("None.")
    lines.extend(["", "## Errors", ""])
    lines.extend([f"- {error}" for error in queue.get("errors", []) or []] or ["None."])
    lines.extend(["", "This queue plan is not execution approval."])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a non-executing Discovery Lane execution queue plan.")
    parser.add_argument("--set-id", required=True, help="Research set id with an INGESTED set manifest.")
    parser.add_argument("--root", default="discovery_lane", help="Discovery Lane root.")
    parser.add_argument("--write-report", action="store_true", help="Also write a Markdown queue report.")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        queue, paths = build_execution_queue(Path(args.root), args.set_id, write_report=args.write_report)
        print(render_summary(queue, paths, Path(args.root)))
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
