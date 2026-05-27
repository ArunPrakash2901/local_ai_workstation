#!/usr/bin/env python3
"""Read-only Local AI Workstation status dashboard."""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
REPORTS = (
    "MVP_FINAL_RELEASE_AUDIT.md",
    "MVP_PATH_LENGTH_HARDENING_REPORT.md",
    "MVP_REAL_CODEX_ACCEPTANCE_REPORT.md",
    "MVP_REAL_GEMINI_ACCEPTANCE_REPORT.md",
)
GENERATED_PREFIXES = (
    "exchange_lane/dispatch_plan_reports/",
    "exchange_lane/dispatch_plans/",
    "exchange_lane/loop_decisions/",
    "exchange_lane/outbox/",
    "exchange_lane/packets/",
    "exchange_lane/result_packets/",
    "exchange_lane/result_validations/",
    "execution_lane/run_reports/",
    "execution_lane/worker_task_packets/",
    "runtime_lane/assignments/",
    "runtime_lane/sessions/",
)
BLOCKED_SESSION_STATUSES = {
    "WAITING_FOR_OPERATOR_APPROVAL",
    "BLOCKED_QUOTA",
    "BLOCKED_ERROR",
    "BLOCKED_MISSING_CONTEXT",
    "CLOSED",
}
BLOCKED_ASSIGNMENT_STATUSES = {
    "WAITING_FOR_OPERATOR_APPROVAL",
    "BLOCKED_SESSION",
    "BLOCKED_QUOTA",
    "BLOCKED_DEPENDENCY",
    "BLOCKED_MISSING_CONTEXT",
    "CLOSED",
    "ABANDONED",
}


def load_json(path: Path, warnings: list[str]) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        warnings.append(f"malformed JSON: {path.relative_to(path.parents[2] if len(path.parents) > 2 else path)}: {exc}")
        return None
    except OSError as exc:
        warnings.append(f"could not read {path}: {exc}")
        return None
    if not isinstance(data, dict):
        warnings.append(f"JSON root is not an object: {path}")
        return None
    return data


def json_records(root: Path, relative_dir: str, warnings: list[str]) -> list[dict[str, Any]]:
    directory = root / relative_dir
    if not directory.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        data = load_json(path, warnings)
        if data is not None:
            data["_path"] = str(path)
            records.append(data)
    return records


def count_by(records: list[dict[str, Any]], field: str, default: str = "UNKNOWN") -> Counter[str]:
    return Counter(str(record.get(field) or default) for record in records)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def packed_refs(git_dir: Path) -> dict[str, str]:
    refs: dict[str, str] = {}
    packed = git_dir / "packed-refs"
    if not packed.is_file():
        return refs
    for line in read_text(packed).splitlines():
        if not line or line.startswith("#") or line.startswith("^"):
            continue
        parts = line.split(" ", 1)
        if len(parts) == 2:
            refs[parts[1].strip()] = parts[0].strip()
    return refs


def git_ref(git_dir: Path, ref: str, packed: dict[str, str]) -> str:
    path = git_dir / ref
    if path.is_file():
        return read_text(path).strip()
    return packed.get(ref, "")


def git_alignment(root: Path) -> str:
    git_dir = root / ".git"
    if not git_dir.is_dir():
        return "UNKNOWN"
    refs = packed_refs(git_dir)
    local = git_ref(git_dir, "refs/heads/main", refs)
    origin = git_ref(git_dir, "refs/remotes/origin/main", refs)
    if not local or not origin:
        return "UNKNOWN"
    return "aligned" if local == origin else "not aligned"


def parse_git_index(root: Path) -> set[str] | None:
    index = root / ".git" / "index"
    if not index.is_file():
        return None
    try:
        data = index.read_bytes()
    except OSError:
        return None
    if len(data) < 12 or data[:4] != b"DIRC":
        return None
    version, entries = struct.unpack(">II", data[4:12])
    if version not in {2, 3}:
        return None
    tracked: set[str] = set()
    offset = 12
    for _ in range(entries):
        start = offset
        if offset + 62 > len(data):
            return None
        flags = struct.unpack(">H", data[offset + 60 : offset + 62])[0]
        offset += 62
        if flags & 0x4000:
            offset += 2
        name_length = flags & 0x0FFF
        if name_length < 0x0FFF:
            name_end = offset + name_length
        else:
            name_end = data.find(b"\x00", offset)
            if name_end < 0:
                return None
        try:
            tracked.add(data[offset:name_end].decode("utf-8", errors="replace"))
        except UnicodeDecodeError:
            return None
        offset = name_end + 1
        offset = start + ((offset - start + 7) // 8) * 8
    return tracked


def generated_artifact_summary(root: Path) -> tuple[int, int | None]:
    files: list[str] = []
    for prefix in GENERATED_PREFIXES:
        directory = root / prefix
        if directory.is_dir():
            files.extend(str(path.relative_to(root)).replace("\\", "/") for path in directory.rglob("*") if path.is_file())
    tracked = parse_git_index(root)
    if tracked is None:
        return len(files), None
    return len(files), sum(1 for path in files if path not in tracked)


def adapter_status(root: Path, warnings: list[str]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for adapter in ("codex_cli", "gemini_cli"):
        path = root / "exchange_lane" / "adapter_commands" / f"{adapter}_command.json"
        data = load_json(path, warnings)
        if data is None:
            statuses[adapter] = "missing"
        elif data.get("enabled") is True:
            executable = str(data.get("executable") or "")
            statuses[adapter] = f"enabled ({Path(executable).name or 'no executable'})"
        else:
            statuses[adapter] = "disabled"
    statuses["ollama_local"] = "planned" if not (root / "exchange_lane" / "adapter_commands" / "ollama_local_command.json").exists() else "configured"
    return statuses


def report_status(root: Path) -> tuple[str, dict[str, bool]]:
    present = {name: (root / name).is_file() for name in REPORTS}
    final_text = read_text(root / "MVP_FINAL_RELEASE_AUDIT.md")
    complete = all(present.values())
    if complete and "Verdict:** **PASS" in final_text:
        return "PASS", present
    if any(present.values()):
        return "UNKNOWN", present
    return "UNKNOWN", present


def latest_id(records: list[dict[str, Any]], id_field: str) -> str:
    if not records:
        return ""
    sorted_records = sorted(
        records,
        key=lambda item: str(item.get("created_at") or item.get("imported_at") or item.get("generated_at") or ""),
    )
    return str(sorted_records[-1].get(id_field) or "")


def choose_next_action(
    adapters: dict[str, str],
    result_packets: list[dict[str, Any]],
    validations: list[dict[str, Any]],
    loop_decisions: list[dict[str, Any]],
    dispatch_plans: list[dict[str, Any]],
    warnings: list[str],
) -> tuple[str, str, bool]:
    if any(status.startswith("enabled") for status in adapters.values()):
        return "Inspect adapter configs and restore disabled state.", "A real adapter is enabled.", False
    if warnings:
        return "Inspect workstation status warnings.", "Malformed or unreadable metadata needs operator attention.", False

    validation_result_ids = {str(item.get("result_id") or "") for item in validations}
    pending_validation = [
        item for item in result_packets
        if item.get("trusted") is False and str(item.get("result_id") or "") not in validation_result_ids
    ]
    if pending_validation:
        result_id = str(pending_validation[0].get("result_id") or "<result_id>")
        return f"ws exchange validate-result --result-id {result_id}", "Imported untrusted result has no validation record.", False

    decision_validation_ids = {str(item.get("validation_id") or "") for item in loop_decisions}
    pending_decision = [
        item for item in validations
        if str(item.get("validation_id") or "") not in decision_validation_ids
    ]
    if pending_decision:
        validation_id = str(pending_decision[0].get("validation_id") or "<validation_id>")
        return f"ws exchange decide-loop --validation-id {validation_id}", "Validation record is awaiting loop decision.", False

    blocked = [item for item in loop_decisions if str(item.get("decision") or "").startswith("BLOCKED")]
    if blocked:
        return "ws exchange loop-status", "Blocked loop decisions require operator review before more dispatch.", False

    ready_plans = [item for item in dispatch_plans if item.get("planned_status") == "PLANNED_NOT_DISPATCHED"]
    if ready_plans:
        plan_id = str(ready_plans[0].get("dispatch_plan_id") or "<dispatch_plan_id>")
        return f"ws exchange real-dispatch --dispatch-plan-id {plan_id} --dry-run", "Ready dispatch plan exists; dry-run is the next safe gate.", True

    return "ws execution status", "No pending Exchange operator gate found.", True


def render_counter(counter: Counter[str]) -> str:
    if not counter:
        return "none"
    return ", ".join(f"{key}={counter[key]}" for key in sorted(counter))


def build_status(root: Path) -> str:
    warnings: list[str] = []
    adapters = adapter_status(root, warnings)
    safety_baseline, reports = report_status(root)

    execution_runs = json_records(root, "execution_lane/runs", warnings)
    worker_tasks = json_records(root, "execution_lane/worker_task_packets", warnings)
    handoff_previews = json_records(root, "execution_lane/handoff_previews", warnings)
    sessions = json_records(root, "runtime_lane/sessions", warnings)
    assignments = json_records(root, "runtime_lane/assignments", warnings)
    blockers = json_records(root, "runtime_lane/blockers", warnings)
    packets = json_records(root, "exchange_lane/packets", warnings)
    dispatch_plans = json_records(root, "exchange_lane/dispatch_plans", warnings)
    results = json_records(root, "exchange_lane/result_packets", warnings)
    validations = json_records(root, "exchange_lane/result_validations", warnings)
    loop_decisions = json_records(root, "exchange_lane/loop_decisions", warnings)

    untrusted = [item for item in results if item.get("trusted") is False]
    blocked_validations = [item for item in validations if str(item.get("validation_status") or "").startswith("VALIDATION_BLOCKED")]
    blocked_loops = [item for item in loop_decisions if str(item.get("decision") or "").startswith("BLOCKED")]
    daily_review = [item for item in loop_decisions if item.get("decision") == "COMPLETED_PENDING_DAILY_REVIEW"]
    ready_for_review = [item for item in loop_decisions if item.get("decision") == "READY_FOR_OPERATOR_REVIEW"]
    blocked_sessions = [item for item in sessions if str(item.get("status") or "") in BLOCKED_SESSION_STATUSES]
    blocked_assignments = [item for item in assignments if str(item.get("assignment_status") or "") in BLOCKED_ASSIGNMENT_STATUSES]
    ready_plans = [item for item in dispatch_plans if item.get("planned_status") == "PLANNED_NOT_DISPATCHED"]
    validation_ids_with_decisions = {str(item.get("validation_id") or "") for item in loop_decisions}
    validations_awaiting_decision = [
        item for item in validations if str(item.get("validation_id") or "") not in validation_ids_with_decisions
    ]
    generated_count, untracked_generated = generated_artifact_summary(root)
    next_action, next_reason, dispatch_safe = choose_next_action(adapters, results, validations, loop_decisions, dispatch_plans, warnings)
    report_summary = ", ".join(f"{name}={'present' if exists else 'missing'}" for name, exists in reports.items())

    generated_line = f"generated artifact files: {generated_count}"
    if untracked_generated is None:
        generated_line += "; untracked status: UNKNOWN"
    else:
        generated_line += f"; untracked generated files: {untracked_generated}"

    autonomy_mode = "MANUAL_REVIEW_ONLY"

    lines = [
        "# Local AI Workstation Status",
        "",
        "## Baseline",
        f"- MVP v0.1: {'COMPLETE' if all(reports.values()) else 'UNKNOWN'}",
        f"- origin/main: {git_alignment(root)}",
        f"- safety baseline: {safety_baseline}",
        f"- reports: {report_summary}",
        f"- autonomy mode: {autonomy_mode}",
        "",
        "## Adapters",
        f"- codex_cli: {adapters['codex_cli']}",
        f"- gemini_cli: {adapters['gemini_cli']}",
        f"- ollama_local: {adapters['ollama_local']}",
        f"- warning: {'real adapter enabled' if any(status.startswith('enabled') for status in adapters.values()) else 'none'}",
        "",
        "## Execution Lane",
        f"- prepared runs: {sum(1 for item in execution_runs if item.get('run_status') == 'PREPARED_NOT_EXECUTED')}",
        f"- runs by status: {render_counter(count_by(execution_runs, 'run_status'))}",
        f"- worker task packets: {len(worker_tasks)}",
        f"- pending handoff previews: {len(handoff_previews)}",
        "",
        "## Runtime Lane",
        f"- sessions: {len(sessions)}",
        f"- sessions by status: {render_counter(count_by(sessions, 'status'))}",
        f"- active assignments: {sum(1 for item in assignments if item.get('assignment_status') == 'ASSIGNED_NOT_STARTED')}",
        f"- assignments by status: {render_counter(count_by(assignments, 'assignment_status'))}",
        f"- blocked sessions: {len(blocked_sessions)}",
        f"- blocked assignments: {len(blocked_assignments)}",
        f"- runtime blockers: {len(blockers)}",
        "",
        "## Exchange Lane",
        f"- packets by status: {render_counter(count_by(packets, 'packet_status'))}",
        f"- dispatch plans by status: {render_counter(count_by(dispatch_plans, 'planned_status'))}",
        f"- ready dispatch plans: {len(ready_plans)}",
        f"- result packets by status: {render_counter(count_by(results, 'result_status'))}",
        f"- validations by status: {render_counter(count_by(validations, 'validation_status'))}",
        f"- loop decisions by status: {render_counter(count_by(loop_decisions, 'decision'))}",
        "",
        "## Review Queue",
        f"- raw imported results: {len(untrusted)}",
        f"- blocked validations: {len(blocked_validations)}",
        f"- ready-for-operator-review summaries: {len(ready_for_review)}",
        f"- BLOCKED_NEEDS_OPERATOR decisions: {sum(1 for item in loop_decisions if item.get('decision') == 'BLOCKED_NEEDS_OPERATOR')}",
        f"- results validated but awaiting decision: {len(validations_awaiting_decision)}",
        f"- daily review candidates: {len(daily_review)}",
        f"- latest result: {latest_id(results, 'result_id') or 'none'}",
        f"- latest validation: {latest_id(validations, 'validation_id') or 'none'}",
        f"- latest loop decision: {latest_id(loop_decisions, 'loop_decision_id') or 'none'}",
        "",
        "## Generated Artifacts",
        f"- {generated_line}",
        "",
        "## Next Safe Action",
        f"- command: {next_action}",
        f"- reason: {next_reason}",
        f"- safe for another guarded dispatch: {'YES' if dispatch_safe else 'NO'}",
    ]
    if warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only Local AI Workstation status dashboard.")
    subparsers = parser.add_subparsers(dest="command")
    status = subparsers.add_parser("status", help="Show unified workstation status.")
    status.add_argument("--root", default=str(ROOT), help="Repository root.")
    subparsers.add_parser("help", help="Show help.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in {None, "help"}:
        parser.print_help()
        return 0
    if args.command == "status":
        print(build_status(Path(args.root).resolve()), end="")
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
