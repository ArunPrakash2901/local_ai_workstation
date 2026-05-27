#!/usr/bin/env python3
"""Execution Lane MVP Slice 1 command surface (non-executing)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

SCRIPT_PATH = Path(__file__).resolve()
LANE_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = LANE_ROOT.parents[0]
TOOL_DIR = SCRIPT_PATH.parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import audit_execution_lane  # noqa: E402
from workstation_ids import check_path_length, make_artifact_id  # noqa: E402

ALLOWED_RUN_STATUSES = {
    "PLANNED_DRY_RUN",
    "PREPARED_NOT_EXECUTED",
    "BLOCKED_QUEUE_NOT_READY",
    "BLOCKED_INVALID_QUEUE",
    "BLOCKED_MISSING_ARTIFACTS",
    "BLOCKED_PRODUCT_DEV_VALIDATION",
    "CLOSED",
}

ALLOWED_TARGETS = {"codex_cli", "gemini_cli", "ollama_local"}
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
REQUIRED_PHASE_FIELDS = {
    "phase_id",
    "phase_title",
    "phase_packet",
    "worker_prompt",
    "phase_manifest",
    "approval_record",
    "handoff_bundle",
    "branch_plan",
    "proposed_branch_name",
    "branch_status",
    "execution_status",
    "commit_allowed",
    "push_allowed",
    "merge_allowed",
    "dependencies",
    "risk_notes",
    "recommended_execution_order",
}

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class ExecutionError(Exception):
    """Operator-facing execution lane error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require_id(value: str, label: str) -> str:
    if not value or not ID_RE.fullmatch(value):
        raise ExecutionError(f"{label} must use letters, numbers, '.', '_' or '-'")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ExecutionError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ExecutionError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ExecutionError(f"JSON root must be object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    length_check = check_path_length(path)
    if length_check["status"] == "fail":
        raise ExecutionError(f"refusing to write overlong path: {length_check['message']} -> {path}")
    if length_check["status"] == "warn":
        print(f"warning: {length_check['message']} -> {path}", file=sys.stderr)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ensure_execution_dirs(root: Path) -> None:
    for name in (
        "runs",
        "run_reports",
        "worker_task_packets",
        "handoff_previews",
        "manifests",
        "tools",
        "contracts",
    ):
        (root / name).mkdir(parents=True, exist_ok=True)


def resolve_relative(base: Path, raw_value: str) -> Path:
    value = Path(str(raw_value))
    if value.is_absolute():
        return value
    return (base / value).resolve()


def queue_discovery_root(queue_manifest: Path) -> Path:
    parent = queue_manifest.parent
    if parent.name == "execution_queues":
        return parent.parent
    return REPO_ROOT / "discovery_lane"


def find_product_dev_manifest(set_id: str) -> Path | None:
    candidate = REPO_ROOT / "product_development_lane" / "manifests" / f"{set_id}_product_development_manifest.json"
    if candidate.is_file():
        return candidate
    return None


def product_dev_outputs(manifest: dict[str, Any]) -> list[str]:
    outputs = manifest.get("outputs", {})
    if not isinstance(outputs, dict):
        return []
    values: list[str] = []
    for value in outputs.values():
        if isinstance(value, str) and value:
            values.append(value)
    return sorted(set(values))


def validate_queue(queue_path: Path) -> dict[str, Any]:
    queue = load_json(queue_path)
    missing_fields = sorted(REQUIRED_QUEUE_FIELDS - set(queue))
    if missing_fields:
        raise ExecutionError(f"queue manifest missing required fields: {', '.join(missing_fields)}")

    queue_status = str(queue.get("queue_status", ""))
    if queue_status != "READY_FOR_EXECUTION_LANE":
        raise ExecutionError(
            f"queue_status must be READY_FOR_EXECUTION_LANE for planning/preparation, found {queue_status}"
        )

    queued_phases = queue.get("queued_phases")
    if not isinstance(queued_phases, list):
        raise ExecutionError("queued_phases must be a list")

    discovery_root = queue_discovery_root(queue_path)
    missing_artifacts: list[str] = []
    product_dev_issues: list[str] = []
    validated_phases: list[dict[str, Any]] = []
    for index, phase in enumerate(queued_phases):
        if not isinstance(phase, dict):
            raise ExecutionError(f"queued_phases[{index}] must be an object")
        phase_missing = sorted(REQUIRED_PHASE_FIELDS - set(phase))
        if phase_missing:
            raise ExecutionError(
                f"queued_phases[{index}] missing required fields: {', '.join(phase_missing)}"
            )
        phase_id = str(phase.get("phase_id", ""))
        branch_status = str(phase.get("branch_status", ""))
        execution_status = str(phase.get("execution_status", ""))
        if branch_status != "PLANNED_NOT_CREATED":
            raise ExecutionError(
                f"phase {phase_id}: branch_status must be PLANNED_NOT_CREATED, found {branch_status}"
            )
        if execution_status != "NOT_STARTED":
            raise ExecutionError(
                f"phase {phase_id}: execution_status must be NOT_STARTED, found {execution_status}"
            )

        for permission_key in ("commit_allowed", "push_allowed", "merge_allowed"):
            permission_value = phase.get(permission_key)
            if not isinstance(permission_value, bool):
                raise ExecutionError(f"phase {phase_id}: {permission_key} must be boolean")
            if permission_value:
                product_dev_issues.append(f"phase {phase_id}: {permission_key} must be false for MVP slice 1")

        required_paths = (
            ("phase_packet", True),
            ("worker_prompt", True),
            ("phase_manifest", True),
            ("approval_record", True),
            ("handoff_bundle", False),
            ("branch_plan", True),
        )
        for field_name, should_be_file in required_paths:
            resolved = resolve_relative(discovery_root, str(phase.get(field_name, "")))
            if should_be_file:
                if not resolved.is_file():
                    missing_artifacts.append(f"phase {phase_id}: missing file {field_name} -> {resolved}")
            else:
                if not resolved.is_dir():
                    missing_artifacts.append(f"phase {phase_id}: missing folder {field_name} -> {resolved}")
        validated_phases.append(phase)

    if missing_artifacts:
        raise ExecutionError(
            "queue has missing referenced artifacts: " + "; ".join(missing_artifacts)
        )
    if product_dev_issues:
        raise ExecutionError("queue has non-conservative permissions: " + "; ".join(product_dev_issues))

    set_id = str(queue.get("set_id", ""))
    if not set_id:
        raise ExecutionError("queue set_id is required")
    manifest_path = find_product_dev_manifest(set_id)
    linked_product_manifest = ""
    linked_product_artifacts: list[str] = []
    if manifest_path is not None:
        product_manifest = load_json(manifest_path)
        manifest_set_id = str(product_manifest.get("set_id", ""))
        if manifest_set_id and manifest_set_id != set_id:
            raise ExecutionError(
                f"linked product development manifest set_id mismatch: expected {set_id}, found {manifest_set_id}"
            )
        linked_product_manifest = str(manifest_path.resolve())
        linked_product_artifacts = product_dev_outputs(product_manifest)

    return {
        "queue_path": str(queue_path.resolve()),
        "queue": queue,
        "validated_phases": validated_phases,
        "linked_product_development_manifest": linked_product_manifest,
        "linked_product_development_artifacts": linked_product_artifacts,
    }


def run_id_for_set(set_id: str) -> str:
    return require_id(
        make_artifact_id("run", [set_id], timestamp=utc_now(), max_len=64),
        "run_id",
    )


def run_manifest_path(root: Path, run_id: str) -> Path:
    return root / "runs" / f"{require_id(run_id, 'run_id')}.json"


def task_packet_path(root: Path, task_packet_id: str) -> Path:
    return root / "worker_task_packets" / f"{require_id(task_packet_id, 'task_packet_id')}.json"


def write_run_report(root: Path, run: dict[str, Any], task_packets: list[dict[str, Any]]) -> Path:
    lines = [
        "# Execution Run Preparation Report",
        "",
        "This report is preparation metadata only.",
        "No worker prompt was executed.",
        "No terminal/model/provider call occurred.",
        "No branch, commit, push, or merge occurred.",
        "",
        f"- run_id: `{run['run_id']}`",
        f"- set_id: `{run['set_id']}`",
        f"- run_status: `{run['run_status']}`",
        f"- source_queue_manifest: `{run['source_queue_manifest']}`",
        f"- queued_phase_count: {run['queued_phase_count']}",
        f"- prepared_task_count: {run['prepared_task_count']}",
        "",
        "## Worker Task Packets",
    ]
    if not task_packets:
        lines.append("- none")
    for packet in task_packets:
        lines.append(
            f"- `{packet['task_packet_id']}` | phase={packet['phase_id']} | prompt={packet['source_worker_prompt']}"
        )
    lines.extend(["", "## Safety Notes"])
    for note in run.get("safety_notes", []):
        lines.append(f"- {note}")
    out = root / "run_reports" / f"{run['run_id']}.md"
    report_len = check_path_length(out)
    if report_len["status"] == "fail":
        raise ExecutionError(f"refusing to write overlong run report path: {report_len['message']} -> {out}")
    if report_len["status"] == "warn":
        print(f"warning: {report_len['message']} -> {out}", file=sys.stderr)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def build_task_packet(
    *,
    execution_root: Path,
    run_id: str,
    discovery_root: Path,
    phase: dict[str, Any],
    linked_product_artifacts: list[str],
) -> dict[str, Any]:
    phase_id = require_id(str(phase.get("phase_id", "")), "phase_id")
    task_packet_id = require_id(
        make_artifact_id("task", [run_id, phase_id], timestamp=utc_now(), max_len=64),
        "task_packet_id",
    )
    product_paths = [
        str((REPO_ROOT / "product_development_lane" / rel).resolve())
        for rel in linked_product_artifacts
    ]
    packet = {
        "task_packet_id": task_packet_id,
        "run_id": run_id,
        "phase_id": phase_id,
        "phase_title": str(phase.get("phase_title", "")),
        "source_phase_packet": str(resolve_relative(discovery_root, str(phase.get("phase_packet", "")))),
        "source_worker_prompt": str(resolve_relative(discovery_root, str(phase.get("worker_prompt", "")))),
        "source_handoff_bundle": str(resolve_relative(discovery_root, str(phase.get("handoff_bundle", "")))),
        "source_branch_plan": str(resolve_relative(discovery_root, str(phase.get("branch_plan", "")))),
        "linked_product_dev_artifacts": product_paths,
        "bounded_objective": (
            f"Prepare non-executing task context for phase {phase_id}. "
            "Do not execute prompts, do not create branches, do not perform git actions."
        ),
        "allowed_write_roots": [
            str((execution_root / "runs").resolve()),
            str((execution_root / "run_reports").resolve()),
            str((execution_root / "worker_task_packets").resolve()),
            str((execution_root / "handoff_previews").resolve()),
        ],
        "forbidden_paths": [
            str((REPO_ROOT / ".git").resolve()),
            str((REPO_ROOT / "products").resolve()),
            str((REPO_ROOT / "apps").resolve()),
            str((REPO_ROOT / "src").resolve()),
        ],
        "forbidden_actions": [
            "execute_worker_prompt",
            "run_codex",
            "run_gemini",
            "run_ollama",
            "terminal_launch",
            "api_call",
            "browser_automation",
            "create_branch",
            "checkout_branch",
            "commit",
            "push",
            "merge",
        ],
        "expected_outputs": [
            "reviewed_handoff_preview",
            "exchange_packet_metadata_candidate",
        ],
        "validation_expectations": [
            "branch_status must remain PLANNED_NOT_CREATED",
            "execution_status must remain NOT_STARTED",
            "all permission flags must remain false",
        ],
        "target_adapters_allowed": ["codex_cli", "gemini_cli", "ollama_local"],
        "human_approval_required": True,
        "execution_allowed": False,
        "commit_allowed": False,
        "push_allowed": False,
        "merge_allowed": False,
    }
    write_json(task_packet_path(execution_root, task_packet_id), packet)
    return packet


def prepare_run(execution_root: Path, queue_manifest: Path) -> dict[str, Any]:
    ensure_execution_dirs(execution_root)
    validated = validate_queue(queue_manifest)
    queue = validated["queue"]
    set_id = str(queue.get("set_id", ""))
    run_id = run_id_for_set(set_id)
    discovery_root = queue_discovery_root(queue_manifest)
    linked_product_artifacts = list(validated["linked_product_development_artifacts"])

    task_packets: list[dict[str, Any]] = []
    task_packet_paths: list[str] = []
    for phase in validated["validated_phases"]:
        packet = build_task_packet(
            execution_root=execution_root,
            run_id=run_id,
            discovery_root=discovery_root,
            phase=phase,
            linked_product_artifacts=linked_product_artifacts,
        )
        task_packets.append(packet)
        task_packet_paths.append(str(task_packet_path(execution_root, str(packet["task_packet_id"])).resolve()))

    run = {
        "run_id": run_id,
        "source_queue_manifest": str(queue_manifest.resolve()),
        "source_queue_checksum": sha256_file(queue_manifest),
        "set_id": set_id,
        "queue_status": str(queue.get("queue_status", "")),
        "created_at": utc_now(),
        "created_by": "execution_command.py",
        "run_status": "PREPARED_NOT_EXECUTED",
        "queued_phase_count": len(validated["validated_phases"]),
        "prepared_task_count": len(task_packets),
        "source_discovery_handoffs": [
            str(resolve_relative(discovery_root, str(phase.get("handoff_bundle", ""))))
            for phase in validated["validated_phases"]
        ],
        "source_phase_packets": [
            str(resolve_relative(discovery_root, str(phase.get("phase_packet", ""))))
            for phase in validated["validated_phases"]
        ],
        "source_worker_prompts": [
            str(resolve_relative(discovery_root, str(phase.get("worker_prompt", ""))))
            for phase in validated["validated_phases"]
        ],
        "source_branch_plans": [
            str(resolve_relative(discovery_root, str(phase.get("branch_plan", ""))))
            for phase in validated["validated_phases"]
        ],
        "linked_product_development_manifest": str(validated["linked_product_development_manifest"]),
        "linked_product_development_artifacts": linked_product_artifacts,
        "branch_creation_allowed": False,
        "execution_allowed": False,
        "commit_allowed": False,
        "push_allowed": False,
        "merge_allowed": False,
        "worker_task_packets": task_packet_paths,
        "exchange_handoff_previews": [],
        "validation_summary": {
            "queue_validated": True,
            "queue_errors_count": len(queue.get("errors", [])) if isinstance(queue.get("errors"), list) else 0,
            "queue_warnings_count": len(queue.get("warnings", [])) if isinstance(queue.get("warnings"), list) else 0,
            "phase_count_validated": len(validated["validated_phases"]),
            "product_dev_manifest_linked": bool(validated["linked_product_development_manifest"]),
        },
        "human_review_required": True,
        "safety_notes": [
            "Preparation metadata only.",
            "No worker prompts executed.",
            "No terminal or model invocation.",
            "No branch creation or git write actions.",
            "No commit/push/merge.",
        ],
        "execution_occurred": False,
        "branch_created": False,
        "commit_performed": False,
        "push_performed": False,
        "merge_performed": False,
        "provider_called": False,
        "model_invoked": False,
    }
    write_json(run_manifest_path(execution_root, run_id), run)
    report_path = write_run_report(execution_root, run, task_packets)
    run["run_report_path"] = str(report_path.resolve())
    write_json(run_manifest_path(execution_root, run_id), run)
    return run


def list_runs(execution_root: Path) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for path in sorted((execution_root / "runs").glob("*.json")):
        data = load_json(path)
        data["_path"] = str(path)
        runs.append(data)
    return runs


def cmd_help(_args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    print(parser.format_help())
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    runs = list_runs(root)
    statuses = Counter(str(run.get("run_status", "UNKNOWN")) for run in runs)
    worker_packets = list((root / "worker_task_packets").glob("*.json"))
    handoff_previews = list((root / "handoff_previews").glob("*.json"))
    reports = list((root / "run_reports").glob("*.md"))
    print("Execution Lane Status")
    print("=====================")
    print(f"root: {root}")
    print(f"runs: {len(runs)}")
    for status in sorted(statuses):
        print(f"- {status}: {statuses[status]}")
    print(f"worker_task_packets: {len(worker_packets)}")
    print(f"handoff_previews: {len(handoff_previews)}")
    print(f"run_reports: {len(reports)}")
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    if not args.dry_run:
        raise ExecutionError("plan requires --dry-run in MVP Slice 1")
    queue_path = Path(args.queue).resolve()
    validated = validate_queue(queue_path)
    queue = validated["queue"]
    phases = validated["validated_phases"]
    print("Execution Lane Plan (Dry Run)")
    print("=============================")
    print("dry_run: true")
    print(f"queue_manifest: {queue_path}")
    print(f"set_id: {queue.get('set_id', '')}")
    print(f"queue_status: {queue.get('queue_status', '')}")
    print(f"queued_phase_count: {len(phases)}")
    print(f"linked_product_development_manifest: {validated['linked_product_development_manifest'] or 'not found'}")
    print("result: VALIDATION_PASS_NO_WRITE")
    print("safety: no execution, no branch creation, no git actions")
    return 0


def cmd_prepare(args: argparse.Namespace) -> int:
    if not args.confirm:
        raise ExecutionError("prepare requires --confirm")
    queue_path = Path(args.queue).resolve()
    run = prepare_run(Path(args.root).resolve(), queue_path)
    print("Execution Lane Prepare")
    print("======================")
    print(f"run_id: {run['run_id']}")
    print(f"run_status: {run['run_status']}")
    print(f"run_manifest: {run_manifest_path(Path(args.root).resolve(), str(run['run_id']))}")
    print(f"prepared_task_count: {run['prepared_task_count']}")
    print(f"run_report: {run['run_report_path']}")
    print("safety: no execution performed")
    return 0


def cmd_run_status(args: argparse.Namespace) -> int:
    run_id = require_id(args.run, "run_id")
    run_path = run_manifest_path(Path(args.root).resolve(), run_id)
    run = load_json(run_path)
    print("Execution Run Status")
    print("====================")
    print(f"run_id: {run.get('run_id', '')}")
    print(f"run_status: {run.get('run_status', '')}")
    print(f"source_queue_manifest: {run.get('source_queue_manifest', '')}")
    print(f"prepared_task_count: {run.get('prepared_task_count', 0)}")
    print(f"execution_allowed: {run.get('execution_allowed', '')}")
    print(f"branch_creation_allowed: {run.get('branch_creation_allowed', '')}")
    print(f"commit_allowed: {run.get('commit_allowed', '')}")
    print(f"push_allowed: {run.get('push_allowed', '')}")
    print(f"merge_allowed: {run.get('merge_allowed', '')}")
    print("next_step: review prepared run and use handoff-preview dry-run")
    return 0


def cmd_handoff_preview(args: argparse.Namespace) -> int:
    if not args.dry_run:
        raise ExecutionError("handoff-preview requires --dry-run in MVP Slice 1")
    target = str(args.target)
    if target not in ALLOWED_TARGETS:
        raise ExecutionError(f"target must be one of: {', '.join(sorted(ALLOWED_TARGETS))}")
    run_id = require_id(args.run, "run_id")
    run = load_json(run_manifest_path(Path(args.root).resolve(), run_id))
    run_status = str(run.get("run_status", ""))
    if run_status != "PREPARED_NOT_EXECUTED":
        raise ExecutionError(f"handoff-preview requires PREPARED_NOT_EXECUTED run, found {run_status}")
    task_packet_paths = run.get("worker_task_packets", [])
    if not isinstance(task_packet_paths, list) or not task_packet_paths:
        raise ExecutionError("run has no worker_task_packets")
    packets: list[dict[str, Any]] = []
    for raw in task_packet_paths:
        packet_path = Path(str(raw))
        if not packet_path.is_file():
            raise ExecutionError(f"missing worker task packet: {packet_path}")
        packets.append(load_json(packet_path))

    print("Execution Handoff Preview (Dry Run)")
    print("===================================")
    print("preview_only: true")
    print("dispatch_performed: false")
    print("model_invocation_performed: false")
    print(f"run_id: {run_id}")
    print(f"target_adapter: {target}")
    for packet in packets:
        phase_id = str(packet.get("phase_id", ""))
        preview_name = (
            make_artifact_id("handoff", [run_id, phase_id, target], max_len=56)
            + "_exchange_packet_preview.json"
        )
        prompt_name = (
            make_artifact_id("handoff", [run_id, phase_id, target], max_len=56)
            + "_prompt_preview.md"
        )
        preview_path = (Path(args.root).resolve() / "handoff_previews" / preview_name).resolve()
        prompt_path = (Path(args.root).resolve() / "handoff_previews" / prompt_name).resolve()
        print(
            f"- phase={phase_id} would_create_exchange_packet_preview={preview_path} "
            f"would_create_prompt_preview={prompt_path}"
        )
    print("result: DRY_RUN_ONLY_NO_WRITE")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    return audit_execution_lane.main(["--root", str(Path(args.root).resolve())])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Execution Lane MVP Slice 1 command surface.")
    parser.add_argument("--root", default=str(LANE_ROOT))
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("help", help="Show execution lane help.")
    sub.add_parser("status", help="Show execution lane status.")

    plan = sub.add_parser("plan", help="Validate a queue manifest without writing artifacts.")
    plan.add_argument("--queue", required=True)
    plan.add_argument("--dry-run", action="store_true")

    prepare = sub.add_parser("prepare", help="Create non-executing run preparation artifacts.")
    prepare.add_argument("--queue", required=True)
    prepare.add_argument("--confirm", action="store_true")

    run_status = sub.add_parser("run-status", help="Show one run status.")
    run_status.add_argument("--run", required=True)

    handoff = sub.add_parser("handoff-preview", help="Preview exchange handoff for one prepared run.")
    handoff.add_argument("--run", required=True)
    handoff.add_argument("--target", required=True)
    handoff.add_argument("--dry-run", action="store_true")
    sub.add_parser("audit", help="Audit execution lane artifacts.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command or "help"
    try:
        if command == "help":
            return cmd_help(args, parser)
        if command == "status":
            return cmd_status(args)
        if command == "plan":
            return cmd_plan(args)
        if command == "prepare":
            return cmd_prepare(args)
        if command == "run-status":
            return cmd_run_status(args)
        if command == "handoff-preview":
            return cmd_handoff_preview(args)
        if command == "audit":
            return cmd_audit(args)
        print(parser.format_help())
        return 1
    except ExecutionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
