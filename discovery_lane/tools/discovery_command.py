#!/usr/bin/env python3
"""Local ergonomic command surface for Discovery Lane.

This is not a global slash-command runtime. It is a thin local dispatcher that
maps the documented `/discovery ...` commands to the safe Python tools.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, Optional

import approve_phase_packet
import approve_research_set
import audit_discovery_lane
import build_execution_queue
import ingest_research_reports
import ingest_research_set
import intake_research_set


DEFAULT_ROOT = Path("discovery_lane")


def resolve_packet(output_root: Path, phase_or_packet_id: str) -> Path:
    raw = Path(phase_or_packet_id)
    if raw.exists():
        return raw

    phase_dir = output_root / "phase_packets"
    candidates = []
    for path in sorted(phase_dir.glob("*.md")):
        stem = path.stem
        normalized = stem.replace("_packet", "")
        if phase_or_packet_id in {stem, normalized, path.name}:
            candidates.append(path)
        elif phase_or_packet_id.replace("-", "_") in {stem, normalized}:
            candidates.append(path)

    if not candidates:
        raise FileNotFoundError(f"no phase packet found for {phase_or_packet_id!r}")
    if len(candidates) > 1:
        joined = ", ".join(str(path) for path in candidates)
        raise ValueError(f"ambiguous phase packet id {phase_or_packet_id!r}: {joined}")
    return candidates[0]


def load_json_records(directory: Path, pattern: str) -> list[dict[str, object]]:
    if not directory.exists():
        return []
    records = []
    for path in sorted(directory.glob(pattern)):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data["_path"] = str(path)
                records.append(data)
        except json.JSONDecodeError:
            continue
    return records


def latest_by_phase(records: list[dict[str, object]], timestamp_key: str) -> dict[str, dict[str, object]]:
    latest: dict[str, dict[str, object]] = {}
    for record in records:
        phase_id = str(record.get("phase_id", ""))
        if not phase_id:
            continue
        current = latest.get(phase_id)
        if current is None or str(record.get(timestamp_key, "")) >= str(current.get(timestamp_key, "")):
            latest[phase_id] = record
    return latest


def command_ingest(args: argparse.Namespace) -> int:
    analyses = ingest_research_reports.ingest_reports(Path(args.input), Path(args.output))
    print(ingest_research_reports.render_run_summary(analyses, Path(args.input), Path(args.output)))
    return 0


def command_intake_set(args: argparse.Namespace) -> int:
    manifest, paths = intake_research_set.intake_research_set(
        Path(args.input),
        Path(args.output),
        args.set_id or None,
    )
    print(intake_research_set.render_summary(manifest, paths, Path(args.output)))
    return 0


def command_ingest_set(args: argparse.Namespace) -> int:
    manifest, paths = ingest_research_set.ingest_research_set(
        Path(args.root),
        args.set_id,
        overwrite=args.overwrite,
    )
    print(ingest_research_set.render_summary(manifest, paths, Path(args.root)))
    return 0 if manifest.get("ingest_status") == ingest_research_set.STATUS_INGESTED else 1


def command_approve_set(args: argparse.Namespace) -> int:
    if not args.dry_run:
        print(approve_research_set.BATCH_APPROVAL_REFUSAL, file=sys.stderr)
        return 1
    plan, report_path = approve_research_set.approve_research_set(
        Path(args.root),
        args.set_id,
        dry_run=args.dry_run,
        write_report=args.write_report,
    )
    print(approve_research_set.render_summary(plan, report_path, Path(args.root)))
    return 0


def command_queue_plan(args: argparse.Namespace) -> int:
    queue, paths = build_execution_queue.build_execution_queue(
        Path(args.root),
        args.set_id,
        write_report=args.write_report,
    )
    print(build_execution_queue.render_summary(queue, paths, Path(args.root)))
    return 0


def command_status(args: argparse.Namespace) -> int:
    output_root = Path(args.output)
    index_path = output_root / "discovery_index.md"
    manifests = ingest_research_reports.load_manifests(output_root)
    research_set_manifests = load_json_records(output_root / "research_set_manifests", "*_manifest.json")
    research_set_ingests = load_json_records(output_root / "research_set_ingests", "*_ingest_manifest.json")
    execution_queues = load_json_records(output_root / "execution_queues", "*_execution_queue.json")
    approval_review_plans = sorted((output_root / "approval_records").glob("*_approval_review_plan.md"))
    approval_review_set_ids = {
        path.stem.replace("_approval_review_plan", "") for path in approval_review_plans
    }
    approvals = load_json_records(output_root / "approval_records", "*.json")
    branch_plans = load_json_records(output_root / "branch_plans", "*.json")
    inbox = output_root / "inbox"
    counts = {
        "inbox_reports": len(list(inbox.rglob("*.md"))) if inbox.exists() else 0,
        "research_sets": len([path for path in (output_root / "research_sets").glob("*") if path.is_dir()]),
        "research_set_manifests": len(research_set_manifests),
        "intake_reports": len(list((output_root / "intake_reports").glob("*.md"))),
        "research_set_ingest_manifests": len(research_set_ingests),
        "research_set_ingest_reports": len(list((output_root / "research_set_ingest_reports").glob("*.md"))),
        "set_approval_review_plans": len(approval_review_plans),
        "ingested_sets_without_approval_review_plan": 0,
        "execution_queue_manifests": len(execution_queues),
        "execution_queue_reports": len(list((output_root / "execution_queue_reports").glob("*.md"))),
        "execution_queues_READY_FOR_EXECUTION_LANE": 0,
        "execution_queues_EMPTY_NO_APPROVED_HANDOFFS": 0,
        "execution_queues_BLOCKED_MISSING_HANDOFFS": 0,
        "execution_queues_BLOCKED_INVALID_BRANCH_PLANS": 0,
        "execution_queues_BLOCKED_INVALID_APPROVALS": 0,
        "research_sets_READY_FOR_INGEST": 0,
        "research_sets_NEEDS_HUMAN_DECISION": 0,
        "research_sets_NOT_READY": 0,
        "research_set_ingests_INGESTED": 0,
        "research_set_ingests_NOT_INGESTED_SOURCE_CHANGED": 0,
        "research_set_ingests_NOT_INGESTED_SET_NOT_READY": 0,
        "research_set_ingests_NOT_INGESTED_MISSING_SOURCE": 0,
        "research_set_ingests_NOT_INGESTED_VALIDATION_FAILED": 0,
        "phase_packets": len(list((output_root / "phase_packets").glob("*.md"))),
        "worker_prompts": len(list((output_root / "worker_prompts").glob("*.md"))),
        "approval_records": len(approvals),
        "approved_handoffs": len([path for path in (output_root / "execution_handoffs").glob("*") if path.is_dir()]),
        "rejected_packets": len(list((output_root / "rejected_packets").glob("*.md"))),
        "branch_plans": len(branch_plans),
        "READY_FOR_HUMAN_REVIEW": 0,
        "NEEDS_HUMAN_DECISION": 0,
        "NOT_EXECUTION_READY": 0,
        "APPROVED_FOR_EXECUTION_HANDOFF": 0,
        "APPROVED_WITH_OVERRIDES": 0,
        "REJECTED_BY_HUMAN": 0,
    }
    for manifest in manifests:
        status = str(manifest.get("validation_status", ""))
        if status in counts:
            counts[status] += 1
    for manifest in research_set_manifests:
        status = str(manifest.get("set_status", ""))
        if status == "READY_FOR_INGEST":
            counts["research_sets_READY_FOR_INGEST"] += 1
        elif status == "NEEDS_HUMAN_DECISION":
            counts["research_sets_NEEDS_HUMAN_DECISION"] += 1
        elif status == "NOT_READY":
            counts["research_sets_NOT_READY"] += 1
    for manifest in research_set_ingests:
        status = str(manifest.get("ingest_status", ""))
        key = f"research_set_ingests_{status}"
        if key in counts:
            counts[key] += 1
        if status == "INGESTED" and str(manifest.get("set_id", "")) not in approval_review_set_ids:
            counts["ingested_sets_without_approval_review_plan"] += 1
    for manifest in execution_queues:
        status = str(manifest.get("queue_status", ""))
        key = f"execution_queues_{status}"
        if key in counts:
            counts[key] += 1
    for approval in approvals:
        status = str(approval.get("approval_status", ""))
        if status in counts:
            counts[status] += 1

    print("# Discovery Lane Status\n")
    for key, value in counts.items():
        print(f"- {key}: {value}")
    print("")
    if index_path.exists():
        print(index_path.read_text(encoding="utf-8", errors="replace"))
        return 0
    print(f"No discovery index found at {index_path}. Run ingest first.")
    return 0


def command_review_list(args: argparse.Namespace) -> int:
    output_root = Path(args.output)
    manifests = ingest_research_reports.load_manifests(output_root)
    research_sets = load_json_records(output_root / "research_set_manifests", "*_manifest.json")
    research_set_ingests = load_json_records(output_root / "research_set_ingests", "*_ingest_manifest.json")
    execution_queues = load_json_records(output_root / "execution_queues", "*_execution_queue.json")
    queue_set_ids = {str(queue.get("set_id", "")) for queue in execution_queues}
    approval_review_set_ids = {
        path.stem.replace("_approval_review_plan", "")
        for path in sorted((output_root / "approval_records").glob("*_approval_review_plan.md"))
    }
    approval_records = load_json_records(output_root / "approval_records", "*_record.json")
    approvals = latest_by_phase(approval_records, "approval_timestamp")
    priority = {
        "NEEDS_HUMAN_DECISION": 1,
        "READY_FOR_HUMAN_REVIEW": 2,
        "NOT_EXECUTION_READY": 3,
    }
    rows = []
    set_rows = []
    set_approval_rows = []
    queue_rows = []
    blocked_queue_rows = []
    handoff_issue_rows = []
    for manifest in research_sets:
        status = str(manifest.get("set_status", ""))
        duplicate_phase_ids = manifest.get("duplicate_phase_ids", [])
        unclear_ids = manifest.get("missing_or_unclear_phase_ids", [])
        unclear_titles = manifest.get("unclear_phase_titles", [])
        if status in {"NEEDS_HUMAN_DECISION", "NOT_READY"} or duplicate_phase_ids or unclear_ids or unclear_titles:
            set_priority = 0 if status == "NOT_READY" else 1
            set_rows.append((set_priority, str(manifest.get("set_id", "")), manifest))

    for ingest in research_set_ingests:
        set_id = str(ingest.get("set_id", ""))
        if str(ingest.get("ingest_status", "")) == "INGESTED" and set_id not in approval_review_set_ids:
            set_approval_rows.append((set_id, ingest))
        if str(ingest.get("ingest_status", "")) == "INGESTED" and set_id not in queue_set_ids:
            generated_packets = {str(path) for path in ingest.get("generated_phase_packets", []) or []}
            approved_packets = {
                str(record.get("source_phase_packet", ""))
                for record in approval_records
                if str(record.get("approval_status", "")) in {"APPROVED_FOR_EXECUTION_HANDOFF", "APPROVED_WITH_OVERRIDES"}
            }
            if generated_packets.intersection(approved_packets):
                queue_rows.append((set_id, ingest))

    for queue in execution_queues:
        status = str(queue.get("queue_status", ""))
        if status.startswith("BLOCKED"):
            queue_rows_for_status = queue.get("errors", [])
            blocked_queue_rows.append((str(queue.get("set_id", "")), status, queue_rows_for_status))

    for handoff_dir in sorted((output_root / "execution_handoffs").glob("*")):
        if not handoff_dir.is_dir():
            continue
        issues = []
        approval_file = handoff_dir / "approval_record.json"
        branch_file = handoff_dir / "branch_plan.json"
        worker_file = handoff_dir / "worker_prompt.md"
        if not approval_file.exists():
            issues.append("missing approval_record.json")
        if not worker_file.exists():
            issues.append("missing worker_prompt.md")
        if not branch_file.exists():
            issues.append("missing branch_plan.json")
        else:
            try:
                branch_plan = json.loads(branch_file.read_text(encoding="utf-8"))
                if branch_plan.get("branch_status") != "PLANNED_NOT_CREATED":
                    issues.append(f"invalid branch_status {branch_plan.get('branch_status')}")
            except Exception as exc:
                issues.append(f"unreadable branch_plan.json: {exc}")
        if issues:
            handoff_issue_rows.append((handoff_dir, issues))

    for manifest in manifests:
        phase_id = str(manifest.get("phase_id", ""))
        approval = approvals.get(phase_id, {})
        approval_status = str(approval.get("approval_status", "PENDING_HUMAN_REVIEW"))
        validation_status = str(manifest.get("validation_status", ""))
        if approval_status in {"APPROVED_FOR_EXECUTION_HANDOFF", "REJECTED_BY_HUMAN"}:
            continue
        if approval_status == "APPROVED_WITH_OVERRIDES" or validation_status in priority:
            rows.append((priority.get(validation_status, 4), phase_id, manifest, approval_status))
    set_rows.sort(key=lambda item: (item[0], item[1]))
    set_approval_rows.sort(key=lambda item: item[0])
    queue_rows.sort(key=lambda item: item[0])
    blocked_queue_rows.sort(key=lambda item: item[0])
    handoff_issue_rows.sort(key=lambda item: str(item[0]))
    rows.sort(key=lambda item: (item[0], item[1]))

    print("# Discovery Review List\n")
    if not set_rows and not set_approval_rows and not queue_rows and not blocked_queue_rows and not handoff_issue_rows and not rows:
        print("No Discovery Lane packets currently need review.")
        return 0
    if set_rows:
        print("## Research Sets Needing Attention\n")
        for _rank, set_id, manifest in set_rows:
            generated = manifest.get("generated_files", {})
            if not isinstance(generated, dict):
                generated = {}
            print(f"- {set_id}: {manifest.get('set_status', '')}")
            print(f"  intake_report: {output_root / str(generated.get('intake_report', ''))}")
            print(f"  manifest: {output_root / str(generated.get('research_set_manifest', ''))}")
            print(f"  duplicate_phase_ids: {manifest.get('duplicate_phase_ids', [])}")
            print(f"  missing_or_unclear_phase_ids: {manifest.get('missing_or_unclear_phase_ids', [])}")
            print(f"  unclear_phase_titles: {manifest.get('unclear_phase_titles', [])}")
        print("")
    if set_approval_rows:
        print("## Ingested Sets Needing Approval Review\n")
        for set_id, ingest in set_approval_rows:
            print(f"- {set_id}: run `ws discovery approve-set {set_id} --dry-run`")
            print(f"  ingest_manifest: {output_root / 'research_set_ingests' / (set_id + '_ingest_manifest.json')}")
            print(f"  generated_phase_packets: {ingest.get('generated_phase_packets', [])}")
        print("")
    if queue_rows:
        print("## Approved Sets Needing Queue Plan\n")
        for set_id, ingest in queue_rows:
            print(f"- {set_id}: run `ws discovery queue-plan {set_id} --write-report`")
            print(f"  ingest_manifest: {output_root / 'research_set_ingests' / (set_id + '_ingest_manifest.json')}")
            print(f"  generated_phase_packets: {ingest.get('generated_phase_packets', [])}")
        print("")
    if blocked_queue_rows:
        print("## Blocked Queue Plans\n")
        for set_id, status, errors in blocked_queue_rows:
            print(f"- {set_id}: {status}")
            print(f"  queue_manifest: {output_root / 'execution_queues' / (set_id + '_execution_queue.json')}")
            print(f"  errors: {errors}")
        print("")
    if handoff_issue_rows:
        print("## Approved Handoff Issues\n")
        for handoff_dir, issues in handoff_issue_rows:
            print(f"- {handoff_dir}")
            print(f"  issues: {issues}")
        print("")
    if rows:
        print("## Phase Packets Needing Review\n")
    current_set = None
    for _rank, phase_id, manifest, approval_status in rows:
        set_id = str(manifest.get("research_set_id", "unscoped"))
        if set_id != current_set:
            current_set = set_id
            print(f"### Research Set: {set_id}\n")
        files = manifest.get("generated_files", {})
        if not isinstance(files, dict):
            files = {}
        print(f"- {phase_id}: {manifest.get('phase_title', '')}")
        print(f"  validation_status: {manifest.get('validation_status', '')}")
        print(f"  approval_status: {approval_status}")
        print(f"  phase_packet: {output_root / str(files.get('phase_packet', ''))}")
        print(f"  worker_prompt: {output_root / str(files.get('worker_prompt', ''))}")
    return 0


def load_handoff_summary(handoff_dir: Path, output_root: Path) -> dict[str, object]:
    approval_path = handoff_dir / "approval_record.json"
    branch_path = handoff_dir / "branch_plan.json"
    manifest_path = handoff_dir / "manifest_snapshot.json"
    approval = json.loads(approval_path.read_text(encoding="utf-8")) if approval_path.exists() else {}
    branch = json.loads(branch_path.read_text(encoding="utf-8")) if branch_path.exists() else {}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    return {
        "phase_id": approval.get("phase_id", branch.get("phase_id", "")),
        "phase_title": approval.get("phase_title", branch.get("phase_title", "")),
        "research_set_id": manifest.get("research_set_id", ""),
        "approval_status": approval.get("approval_status", ""),
        "proposed_branch_name": branch.get("proposed_branch_name", approval.get("proposed_branch_name", "")),
        "branch_status": branch.get("branch_status", approval.get("branch_status", "")),
        "handoff_path": str(handoff_dir),
        "branch_plan_path": str(branch_path) if branch_path.exists() else "",
        "execution_status": approval.get("execution_lane_status", "NOT_STARTED") or "NOT_STARTED",
    }


def command_handoff_list(args: argparse.Namespace) -> int:
    output_root = Path(args.output)
    handoff_root = output_root / "execution_handoffs"
    handoffs = []
    if handoff_root.exists():
        for handoff_dir in sorted(handoff_root.glob("*")):
            if handoff_dir.is_dir():
                handoffs.append(load_handoff_summary(handoff_dir, output_root))

    print("# Discovery Handoff List\n")
    if not handoffs:
        print("No approved handoff bundles found.")
        return 0
    for handoff in handoffs:
        print(f"- {handoff.get('phase_id', '')}: {handoff.get('phase_title', '')}")
        if handoff.get("research_set_id"):
            print(f"  research_set_id: {handoff.get('research_set_id', '')}")
        print(f"  approval_status: {handoff.get('approval_status', '')}")
        print(f"  proposed_branch: `{handoff.get('proposed_branch_name', '')}`")
        print(f"  branch_status: {handoff.get('branch_status', '')}")
        print(f"  execution_status: {handoff.get('execution_status', 'NOT_STARTED')}")
        print(f"  handoff: {handoff.get('handoff_path', '')}")
        print(f"  branch_plan: {handoff.get('branch_plan_path', '')}")
    return 0


def command_approve(args: argparse.Namespace) -> int:
    output_root = Path(args.output)
    packet = resolve_packet(output_root, args.phase_or_packet_id)
    approve_args = argparse.Namespace(
        packet=str(packet),
        output=str(output_root),
        reject=False,
        override=args.override,
        reason=args.reason,
        allow_commit=args.allow_commit,
        allow_push=args.allow_push,
        allow_merge=args.allow_merge,
        branch_name=args.branch or "",
    )
    result = approve_phase_packet.approve_packet(approve_args)
    print(approve_phase_packet.render_result(result))
    return 0


def command_reject(args: argparse.Namespace) -> int:
    output_root = Path(args.output)
    packet = resolve_packet(output_root, args.phase_or_packet_id)
    approve_args = argparse.Namespace(
        packet=str(packet),
        output=str(output_root),
        reject=True,
        override=False,
        reason=args.reason,
        allow_commit=False,
        allow_push=False,
        allow_merge=False,
        branch_name="",
    )
    result = approve_phase_packet.approve_packet(approve_args)
    print(approve_phase_packet.render_result(result))
    return 0


def find_phase_record(output_root: Path, phase_or_packet_id: str, directory: str, pattern: str) -> Optional[Path]:
    normalized = phase_or_packet_id.replace("-", "_")
    for path in sorted((output_root / directory).glob(pattern)):
        stem = path.stem
        if phase_or_packet_id in {stem, path.name} or normalized in stem:
            return path
    return None


def command_handoff(args: argparse.Namespace) -> int:
    output_root = Path(args.output)
    handoff_root = output_root / "execution_handoffs"
    normalized = args.phase_or_packet_id.replace("_", "-")
    candidates = [
        path
        for path in sorted(handoff_root.glob("*"))
        if path.is_dir()
        and (args.phase_or_packet_id in {path.name, path.name.replace("-", "_")} or path.name.startswith(normalized))
    ]
    if not candidates:
        print(f"No handoff bundle found for {args.phase_or_packet_id!r}.")
        return 1
    if len(candidates) > 1:
        print("Ambiguous handoff id: " + ", ".join(str(path) for path in candidates))
        return 1
    print(candidates[0])
    handoff = candidates[0] / "HANDOFF.md"
    if handoff.exists():
        print("")
        print(handoff.read_text(encoding="utf-8", errors="replace"))
    return 0


def command_branch_plan(args: argparse.Namespace) -> int:
    output_root = Path(args.output)
    path = find_phase_record(output_root, args.phase_or_packet_id, "branch_plans", "*_branch_plan.json")
    if path is None:
        print(f"No branch plan found for {args.phase_or_packet_id!r}.")
        return 1
    print(path.read_text(encoding="utf-8", errors="replace"))
    return 0


def command_audit(args: argparse.Namespace) -> int:
    root = Path(args.root)
    state_root = Path(args.state_root) if args.state_root else root
    audit, counts = audit_discovery_lane.audit_discovery_lane(root, state_root)
    print(audit_discovery_lane.render_audit(root, state_root, audit, counts))
    return 1 if audit.errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Discovery Lane local command dispatcher.")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Ingest Markdown research reports.")
    ingest.add_argument("--input", default="discovery_lane/inbox")
    ingest.add_argument("--output", default=str(DEFAULT_ROOT))
    ingest.set_defaults(func=command_ingest)

    intake = sub.add_parser("intake-set", help="Validate a set of Markdown research reports.")
    intake.add_argument("input", help="Folder containing phase-wise Markdown research reports.")
    intake.add_argument("--output", default=str(DEFAULT_ROOT))
    intake.add_argument("--set-id", default="")
    intake.set_defaults(func=command_intake_set)

    ingest_set = sub.add_parser("ingest-set", help="Ingest one READY_FOR_INGEST research set.")
    ingest_set.add_argument("set_id")
    ingest_set.add_argument("--root", default=str(DEFAULT_ROOT))
    ingest_set.add_argument("--overwrite", action="store_true")
    ingest_set.set_defaults(func=command_ingest_set)

    approve_set = sub.add_parser("approve-set", help="Dry-run approval review plan for one ingested research set.")
    approve_set.add_argument("set_id")
    approve_set.add_argument("--root", default=str(DEFAULT_ROOT))
    approve_set.add_argument("--dry-run", action="store_true")
    approve_set.add_argument("--write-report", action="store_true")
    approve_set.set_defaults(func=command_approve_set)

    queue_plan = sub.add_parser("queue-plan", help="Build a non-executing execution queue plan for one research set.")
    queue_plan.add_argument("set_id")
    queue_plan.add_argument("--root", default=str(DEFAULT_ROOT))
    queue_plan.add_argument("--write-report", action="store_true")
    queue_plan.set_defaults(func=command_queue_plan)

    status = sub.add_parser("status", help="Show the discovery index.")
    status.add_argument("--output", default=str(DEFAULT_ROOT))
    status.set_defaults(func=command_status)

    review = sub.add_parser("review-list", help="List phase packets awaiting review.")
    review.add_argument("--output", default=str(DEFAULT_ROOT))
    review.set_defaults(func=command_review_list)

    handoff_list = sub.add_parser("handoff-list", help="List approved handoff bundles.")
    handoff_list.add_argument("--output", default=str(DEFAULT_ROOT))
    handoff_list.set_defaults(func=command_handoff_list)

    approve = sub.add_parser("approve", help="Approve a phase packet for future execution handoff.")
    approve.add_argument("phase_or_packet_id")
    approve.add_argument("--output", default=str(DEFAULT_ROOT))
    approve.add_argument("--branch", default="")
    approve.add_argument("--override", action="store_true")
    approve.add_argument("--reason", default="")
    approve.add_argument("--allow-commit", action="store_true")
    approve.add_argument("--allow-push", action="store_true")
    approve.add_argument("--allow-merge", action="store_true")
    approve.set_defaults(func=command_approve)

    reject = sub.add_parser("reject", help="Reject a phase packet after human review.")
    reject.add_argument("phase_or_packet_id")
    reject.add_argument("--output", default=str(DEFAULT_ROOT))
    reject.add_argument("--reason", required=True)
    reject.set_defaults(func=command_reject)

    handoff = sub.add_parser("handoff", help="Show a handoff bundle summary.")
    handoff.add_argument("phase_or_packet_id")
    handoff.add_argument("--output", default=str(DEFAULT_ROOT))
    handoff.set_defaults(func=command_handoff)

    branch = sub.add_parser("branch-plan", help="Show a branch plan JSON record.")
    branch.add_argument("phase_or_packet_id")
    branch.add_argument("--output", default=str(DEFAULT_ROOT))
    branch.set_defaults(func=command_branch_plan)

    audit = sub.add_parser("audit", help="Audit Discovery Lane state without writing files.")
    audit.add_argument("--root", default=str(DEFAULT_ROOT))
    audit.add_argument("--state-root", default="")
    audit.set_defaults(func=command_audit)

    help_cmd = sub.add_parser("help", help="Show Discovery Lane command help.")
    help_cmd.set_defaults(func=lambda args: (parser.print_help() or 0))
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
