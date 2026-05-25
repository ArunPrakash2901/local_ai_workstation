#!/usr/bin/env python3
"""Plan human approval review for one ingested Discovery Lane research set.

This v1.5 tool is intentionally not a batch approval command. It reads the
set-level ingest manifest, inspects generated phase packets, and tells the
operator which packets are ready to review in VS Code. It does not approve
packets, create handoffs, create branch plans, execute worker prompts, call
models, or run git commands.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, Optional

import approve_phase_packet
import ingest_research_reports


STATUS_READY = "READY_FOR_HUMAN_REVIEW"
STATUS_NEEDS_DECISION = "NEEDS_HUMAN_DECISION"
STATUS_NOT_READY = "NOT_EXECUTION_READY"
STATUS_UNKNOWN = "UNKNOWN_STATUS"
STATUS_INGESTED = "INGESTED"

APPROVED_STATUSES = {"APPROVED_FOR_EXECUTION_HANDOFF", "APPROVED_WITH_OVERRIDES"}
REJECTED_STATUS = "REJECTED_BY_HUMAN"
BLOCKED_STATUS = "BLOCKED_NEEDS_REVISION"
NON_PENDING_APPROVAL_STATUSES = APPROVED_STATUSES | {REJECTED_STATUS, BLOCKED_STATUS}

BATCH_APPROVAL_REFUSAL = (
    "Batch approval is intentionally not implemented. "
    "Review packets and approve phases individually."
)


def safe_relative(path: Optional[Path], root: Path) -> str:
    return ingest_research_reports.safe_relative(path, root) if path else ""


def resolve_path(root: Path, path_text: str) -> Path:
    raw = Path(path_text)
    candidates = [raw] if raw.is_absolute() else [root / raw, Path.cwd() / raw]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must be an object: {path}")
    return data


def load_ingest_manifest(root: Path, set_id: str) -> tuple[dict[str, object], Path]:
    path = root / "research_set_ingests" / f"{set_id}_ingest_manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"research set ingest manifest not found: {path}")
    return load_json(path), path


def packet_metadata(packet_path: Path) -> dict[str, str]:
    if not packet_path.exists():
        return {
            "phase_id": "",
            "phase_title": "",
            "validation_status": STATUS_UNKNOWN,
        }
    text = packet_path.read_text(encoding="utf-8", errors="replace")
    sections = approve_phase_packet.parse_markdown_sections(text)
    phase_id = approve_phase_packet.section(sections, "Phase ID").splitlines()[0].strip()
    phase_title = approve_phase_packet.section(sections, "Phase Title").splitlines()[0].strip()
    status = approve_phase_packet.section(sections, "Current Status").splitlines()[0].strip()
    if status not in {STATUS_READY, STATUS_NEEDS_DECISION, STATUS_NOT_READY}:
        status = STATUS_UNKNOWN
    return {
        "phase_id": phase_id,
        "phase_title": phase_title,
        "validation_status": status,
    }


def load_approval_records(root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in sorted((root / "approval_records").glob("*.json")):
        try:
            data = load_json(path)
        except Exception:
            continue
        data["_path"] = safe_relative(path, root)
        records.append(data)
    return records


def matching_approval_record(
    records: list[dict[str, object]],
    *,
    phase_id: str,
    packet_rel: str,
) -> Optional[dict[str, object]]:
    exact = [
        record
        for record in records
        if str(record.get("source_phase_packet", "")) == packet_rel
    ]
    candidates = exact or [record for record in records if str(record.get("phase_id", "")) == phase_id]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: str(item.get("approval_timestamp", "")))[-1]


def handoff_exists(root: Path, record: Optional[dict[str, object]]) -> bool:
    if not record:
        return False
    handoff = str(record.get("handoff_bundle", "")).strip()
    return bool(handoff and (root / handoff).exists())


def path_exists(root: Path, path_text: str) -> bool:
    return bool(path_text and resolve_path(root, path_text).exists())


def recommended_action(
    *,
    validation_status: str,
    approval_status: str,
    has_handoff: bool,
    has_worker_prompt: bool,
    has_phase_manifest: bool,
) -> str:
    if approval_status in APPROVED_STATUSES:
        return "Already approved; inspect handoff before execution lane use."
    if approval_status == REJECTED_STATUS:
        return "Rejected; revise the research report or packet before any future approval."
    if approval_status == BLOCKED_STATUS:
        return "Blocked; resolve the recorded issue before approval."
    if has_handoff:
        return "Handoff already exists; do not approve again."
    if not has_worker_prompt or not has_phase_manifest:
        return "Regenerate or repair ingest artifacts before approval."
    if validation_status == STATUS_READY:
        return "Open packet and worker prompt in VS Code, then approve this packet individually if acceptable."
    if validation_status == STATUS_NEEDS_DECISION:
        return "Resolve human-decision flags before individual approval."
    if validation_status == STATUS_NOT_READY:
        return "Do not approve; revise source research or packet first."
    return "Inspect manually; packet status is unknown."


def inspect_packet_row(
    *,
    root: Path,
    packet_rel: str,
    worker_rel: str,
    manifest_rel: str,
    approval_records: list[dict[str, object]],
) -> dict[str, object]:
    packet_path = resolve_path(root, packet_rel)
    worker_path = resolve_path(root, worker_rel)
    phase_manifest_path = resolve_path(root, manifest_rel)
    metadata = packet_metadata(packet_path)
    phase_id = metadata["phase_id"]
    packet_rel_resolved = safe_relative(packet_path, root) if packet_path.exists() else packet_rel
    approval = matching_approval_record(approval_records, phase_id=phase_id, packet_rel=packet_rel_resolved)
    approval_status = str(approval.get("approval_status", "PENDING_HUMAN_REVIEW")) if approval else "PENDING_HUMAN_REVIEW"
    has_handoff = handoff_exists(root, approval)
    has_worker_prompt = worker_path.exists()
    has_phase_manifest = phase_manifest_path.exists()
    return {
        "phase_id": phase_id,
        "phase_title": metadata["phase_title"],
        "packet_path": packet_rel_resolved,
        "worker_prompt_path": safe_relative(worker_path, root) if worker_path.exists() else worker_rel,
        "phase_manifest_path": safe_relative(phase_manifest_path, root) if phase_manifest_path.exists() else manifest_rel,
        "validation_status": metadata["validation_status"],
        "approval_status": approval_status,
        "approval_record_path": str(approval.get("_path", "")) if approval else "",
        "handoff_status": "EXISTS" if has_handoff else "NOT_CREATED",
        "has_worker_prompt": has_worker_prompt,
        "has_phase_manifest": has_phase_manifest,
        "recommended_action": recommended_action(
            validation_status=metadata["validation_status"],
            approval_status=approval_status,
            has_handoff=has_handoff,
            has_worker_prompt=has_worker_prompt,
            has_phase_manifest=has_phase_manifest,
        ),
    }


def count_rows(rows: list[dict[str, object]]) -> dict[str, int]:
    counts = {
        "total_packets": len(rows),
        "ready_for_approval": 0,
        "needs_human_decision": 0,
        "not_execution_ready": 0,
        "unknown_status": 0,
        "already_approved": 0,
        "already_handed_off": 0,
        "missing_worker_prompt": 0,
        "missing_phase_manifest": 0,
    }
    for row in rows:
        status = str(row.get("validation_status", ""))
        approval_status = str(row.get("approval_status", ""))
        if status == STATUS_READY and approval_status not in NON_PENDING_APPROVAL_STATUSES:
            counts["ready_for_approval"] += 1
        elif status == STATUS_NEEDS_DECISION:
            counts["needs_human_decision"] += 1
        elif status == STATUS_NOT_READY:
            counts["not_execution_ready"] += 1
        elif status == STATUS_UNKNOWN:
            counts["unknown_status"] += 1
        if approval_status in APPROVED_STATUSES:
            counts["already_approved"] += 1
        if row.get("handoff_status") == "EXISTS":
            counts["already_handed_off"] += 1
        if not row.get("has_worker_prompt"):
            counts["missing_worker_prompt"] += 1
        if not row.get("has_phase_manifest"):
            counts["missing_phase_manifest"] += 1
    return counts


def next_action(counts: dict[str, int], ingest_status: str) -> str:
    if ingest_status != STATUS_INGESTED:
        return "Do not approve packets; fix the set ingest before review."
    if counts["missing_worker_prompt"] or counts["missing_phase_manifest"] or counts["unknown_status"]:
        return "Repair generated artifacts or inspect unknown statuses before approval."
    if counts["needs_human_decision"]:
        return "Resolve NEEDS_HUMAN_DECISION packets before approval."
    if counts["not_execution_ready"]:
        return "Revise NOT_EXECUTION_READY packets before approval."
    if counts["ready_for_approval"]:
        return "Review listed packet and worker prompt files in VS Code, then approve phases individually."
    if counts["already_approved"]:
        return "No pending packets found; inspect existing handoffs before execution lane use."
    return "No approval action recommended."


def build_approval_review_plan(root: Path, set_id: str) -> dict[str, object]:
    ingest_manifest, ingest_manifest_path = load_ingest_manifest(root, set_id)
    ingest_status = str(ingest_manifest.get("ingest_status", ""))
    if ingest_status != STATUS_INGESTED:
        raise PermissionError(f"research set {set_id!r} has ingest_status {ingest_status}; expected INGESTED")

    packets = ingest_manifest.get("generated_phase_packets", [])
    prompts = ingest_manifest.get("generated_worker_prompts", [])
    manifests = ingest_manifest.get("generated_manifests", [])
    if not isinstance(packets, list) or not isinstance(prompts, list) or not isinstance(manifests, list):
        raise ValueError("ingest manifest generated artifact fields must be lists")

    max_len = max(len(packets), len(prompts), len(manifests))
    approval_records = load_approval_records(root)
    rows: list[dict[str, object]] = []
    for index in range(max_len):
        packet_rel = str(packets[index]) if index < len(packets) else ""
        worker_rel = str(prompts[index]) if index < len(prompts) else ""
        manifest_rel = str(manifests[index]) if index < len(manifests) else ""
        rows.append(
            inspect_packet_row(
                root=root,
                packet_rel=packet_rel,
                worker_rel=worker_rel,
                manifest_rel=manifest_rel,
                approval_records=approval_records,
            )
        )

    counts = count_rows(rows)
    return {
        "set_id": set_id,
        "ingest_manifest": safe_relative(ingest_manifest_path, root),
        "ingest_status": ingest_status,
        "counts": counts,
        "packets": rows,
        "recommended_next_action": next_action(counts, ingest_status),
        "execution_boundary": {
            "approvals_created": False,
            "handoffs_created": False,
            "branch_plans_created": False,
            "worker_prompts_executed": False,
            "branches_created": False,
        },
    }


def md_escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def render_review_plan(plan: dict[str, object]) -> str:
    counts = plan.get("counts", {})
    if not isinstance(counts, dict):
        counts = {}
    rows = plan.get("packets", [])
    if not isinstance(rows, list):
        rows = []
    lines = [
        f"# Approval Review Plan: {plan.get('set_id', '')}",
        "",
        "This review plan is advisory only. It does not approve packets, create handoffs, create branch plans, execute worker prompts, create branches, commit, push, or merge.",
        "",
        "## Research Set ID",
        "",
        str(plan.get("set_id", "")),
        "",
        "## Ingest Manifest",
        "",
        f"`{plan.get('ingest_manifest', '')}`",
        "",
        "## Ingest Status",
        "",
        str(plan.get("ingest_status", "")),
        "",
        "## Summary",
        "",
        f"- Total Packets: {counts.get('total_packets', 0)}",
        f"- Ready For Approval: {counts.get('ready_for_approval', 0)}",
        f"- Needs Human Decision: {counts.get('needs_human_decision', 0)}",
        f"- Not Execution Ready: {counts.get('not_execution_ready', 0)}",
        f"- Unknown Status: {counts.get('unknown_status', 0)}",
        f"- Already Approved: {counts.get('already_approved', 0)}",
        f"- Already Handed Off: {counts.get('already_handed_off', 0)}",
        f"- Missing Worker Prompt: {counts.get('missing_worker_prompt', 0)}",
        f"- Missing Phase Manifest: {counts.get('missing_phase_manifest', 0)}",
        "",
        "## Recommended Next Action",
        "",
        str(plan.get("recommended_next_action", "")),
        "",
        "## Packet Review Table",
        "",
        "| Phase | Packet | Worker Prompt | Phase Manifest | Validation Status | Approval Status | Handoff Status | Recommended Action |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        if not isinstance(row, dict):
            continue
        phase = f"{row.get('phase_id', '')} - {row.get('phase_title', '')}".strip(" -")
        lines.append(
            "| {phase} | `{packet}` | `{worker}` | `{manifest}` | {validation} | {approval} | {handoff} | {action} |".format(
                phase=md_escape(phase),
                packet=md_escape(row.get("packet_path", "")),
                worker=md_escape(row.get("worker_prompt_path", "")),
                manifest=md_escape(row.get("phase_manifest_path", "")),
                validation=md_escape(row.get("validation_status", "")),
                approval=md_escape(row.get("approval_status", "")),
                handoff=md_escape(row.get("handoff_status", "")),
                action=md_escape(row.get("recommended_action", "")),
            )
        )

    lines.extend(["", "## VS Code Review Paths", ""])
    for row in rows:
        if not isinstance(row, dict):
            continue
        lines.append(f"- packet: `{row.get('packet_path', '')}`")
        lines.append(f"- worker_prompt: `{row.get('worker_prompt_path', '')}`")
        lines.append(f"- phase_manifest: `{row.get('phase_manifest_path', '')}`")
    if not rows:
        lines.append("None.")
    lines.extend(
        [
            "",
            "## Approval Boundary",
            "",
            "- This report is not an approval record.",
            "- Individual packet approval remains the human gate.",
            "- Use `ws discovery approve <phase_or_packet_id>` only after VS Code review.",
            "- Batch approval is intentionally not implemented.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_review_report(root: Path, plan: dict[str, object]) -> Path:
    (root / "approval_records").mkdir(parents=True, exist_ok=True)
    set_id = str(plan.get("set_id", "research_set"))
    report_path = root / "approval_records" / f"{set_id}_approval_review_plan.md"
    report_path.write_text(render_review_plan(plan), encoding="utf-8", newline="\n")
    return report_path


def render_summary(plan: dict[str, object], report_path: Optional[Path], root: Path) -> str:
    counts = plan.get("counts", {})
    if not isinstance(counts, dict):
        counts = {}
    lines = [
        "# Discovery Research Set Approval Review",
        "",
        "DRY RUN: no packets approved, no handoffs created, no branch plans created, no worker prompts executed.",
        "",
        f"- set_id: {plan.get('set_id', '')}",
        f"- ingest_manifest: `{plan.get('ingest_manifest', '')}`",
        f"- ingest_status: {plan.get('ingest_status', '')}",
        f"- total_packets: {counts.get('total_packets', 0)}",
        f"- ready_for_approval: {counts.get('ready_for_approval', 0)}",
        f"- needs_human_decision: {counts.get('needs_human_decision', 0)}",
        f"- not_execution_ready: {counts.get('not_execution_ready', 0)}",
        f"- unknown_status: {counts.get('unknown_status', 0)}",
        f"- already_approved: {counts.get('already_approved', 0)}",
        f"- already_handed_off: {counts.get('already_handed_off', 0)}",
        f"- missing_worker_prompt: {counts.get('missing_worker_prompt', 0)}",
        f"- missing_phase_manifest: {counts.get('missing_phase_manifest', 0)}",
        "",
        "## Recommended Next Action",
        "",
        str(plan.get("recommended_next_action", "")),
        "",
        "## Packets",
        "",
    ]
    rows = plan.get("packets", [])
    if isinstance(rows, list) and rows:
        for row in rows:
            if not isinstance(row, dict):
                continue
            lines.append(f"- {row.get('phase_id', '')}: {row.get('phase_title', '')}")
            lines.append(f"  validation_status: {row.get('validation_status', '')}")
            lines.append(f"  approval_status: {row.get('approval_status', '')}")
            lines.append(f"  handoff_status: {row.get('handoff_status', '')}")
            lines.append(f"  packet: `{row.get('packet_path', '')}`")
            lines.append(f"  worker_prompt: `{row.get('worker_prompt_path', '')}`")
            lines.append(f"  phase_manifest: `{row.get('phase_manifest_path', '')}`")
            lines.append(f"  recommended_action: {row.get('recommended_action', '')}")
    else:
        lines.append("None.")
    if report_path:
        lines.extend(["", f"- review_plan_report: `{safe_relative(report_path, root)}`"])
    lines.extend(["", BATCH_APPROVAL_REFUSAL])
    return "\n".join(lines)


def approve_research_set(
    root: Path,
    set_id: str,
    *,
    dry_run: bool,
    write_report: bool,
) -> tuple[dict[str, object], Optional[Path]]:
    if not dry_run:
        raise PermissionError(BATCH_APPROVAL_REFUSAL)
    plan = build_approval_review_plan(root, set_id)
    report_path = write_review_report(root, plan) if write_report else None
    return plan, report_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan human approval review for one ingested Discovery Lane research set.")
    parser.add_argument("--set-id", required=True, help="Research set id with an INGESTED set manifest.")
    parser.add_argument("--root", default="discovery_lane", help="Discovery Lane root.")
    parser.add_argument("--dry-run", action="store_true", help="Required. Review only; no approval or handoff creation.")
    parser.add_argument("--write-report", action="store_true", help="With --dry-run, write an advisory Markdown review plan.")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        plan, report_path = approve_research_set(
            Path(args.root),
            args.set_id,
            dry_run=args.dry_run,
            write_report=args.write_report,
        )
        print(render_summary(plan, report_path, Path(args.root)))
        return 0
    except PermissionError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
