#!/usr/bin/env python3
"""Exchange Lane loop decision metadata writer."""

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

TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import exchange_validate_result  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from workstation_ids import check_path_length, make_artifact_id  # noqa: E402

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

DECISIONS = {
    "AUTO_CONTINUE",
    "AUTO_REPAIR_ONCE",
    "AUTO_REPAIR_RETRY_AVAILABLE",
    "BLOCKED_NEEDS_OPERATOR",
    "BLOCKED_QUOTA_OR_AUTH",
    "BLOCKED_PERMISSION_PROMPT",
    "BLOCKED_FORBIDDEN_ACTION",
    "BLOCKED_VALIDATION_FAILED",
    "COMPLETED_PENDING_DAILY_REVIEW",
    "READY_FOR_FINAL_HUMAN_REVIEW",
}
REPAIR_DECISIONS = {"AUTO_REPAIR_ONCE", "AUTO_REPAIR_RETRY_AVAILABLE"}


class LoopDecisionError(Exception):
    """Operator-facing loop decision error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require_id(value: str, label: str) -> str:
    if not value or not ID_RE.fullmatch(value):
        raise LoopDecisionError(f"{label} must use letters, numbers, '.', '_' or '-' and cannot be empty")
    return value


def safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._-") or "record"


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LoopDecisionError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LoopDecisionError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise LoopDecisionError(f"JSON root must be an object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    length_check = check_path_length(path)
    if length_check["status"] == "fail":
        raise LoopDecisionError(f"refusing to write overlong path: {length_check['message']} -> {path}")
    if length_check["status"] == "warn":
        print(f"warning: {length_check['message']} -> {path}", file=sys.stderr)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def loop_decision_path(root: Path, loop_decision_id: str) -> Path:
    return root / "loop_decisions" / f"{require_id(loop_decision_id, 'loop_decision_id')}.json"


def repair_packet_path(root: Path, repair_packet_id: str) -> Path:
    return root / "repair_packets" / f"{require_id(repair_packet_id, 'repair_packet_id')}.json"


def build_loop_decision_id(validation: dict[str, Any]) -> str:
    validation_id = str(validation.get("validation_id", "validation"))
    return require_id(
        make_artifact_id(
            "loop",
            [validation_id, str(validation.get("result_id", ""))],
            timestamp=utc_now(),
            max_len=64,
        ),
        "loop_decision_id",
    )


def build_repair_packet_id(loop_decision_id: str) -> str:
    return require_id(
        make_artifact_id("repair", [loop_decision_id], max_len=64),
        "repair_packet_id",
    )


def validation_path(root: Path, validation_id: str) -> Path:
    return exchange_validate_result.validation_path(root, validation_id)


def decide(root: Path, validation_id: str) -> Path:
    root = root.resolve()
    validation_id = require_id(validation_id, "validation_id")
    validation = load_json(validation_path(root, validation_id))
    decision = str(validation.get("recommended_loop_decision", "BLOCKED_VALIDATION_FAILED"))
    if decision not in DECISIONS:
        decision = "BLOCKED_VALIDATION_FAILED"

    safety_flags = validation.get("safety_flags", {})
    if not isinstance(safety_flags, dict):
        safety_flags = {}
    retry = validation.get("retry_eligibility", {})
    if not isinstance(retry, dict):
        retry = {}
    retry_count = int(retry.get("retry_count", 0) or 0)
    retry_budget = int(retry.get("retry_budget", 1) or 1)
    fake_execution = bool(safety_flags.get("fake_execution"))
    human_required = bool(validation.get("human_escalation_required"))
    if decision.startswith("BLOCKED_"):
        human_required = True

    auto_continue_allowed = decision == "AUTO_CONTINUE" and not fake_execution and not human_required
    auto_repair_allowed = decision in REPAIR_DECISIONS and retry_count < retry_budget and not fake_execution

    if decision == "COMPLETED_PENDING_DAILY_REVIEW":
        next_action = "Record completion in loop status; wait for daily/final gate if this was the last packet."
    elif decision in REPAIR_DECISIONS:
        next_action = "Create bounded repair metadata with repair-plan; do not dispatch in this slice."
    elif decision == "AUTO_CONTINUE":
        next_action = "Future real-dispatch slice may continue if another approved packet exists."
    else:
        next_action = "Escalate to operator with validation reasons."

    record = {
        "loop_decision_id": build_loop_decision_id(validation),
        "result_id": str(validation.get("result_id", "")),
        "validation_id": validation_id,
        "source_packet_id": str(validation.get("source_packet_id", "")),
        "dispatch_plan_id": str(validation.get("dispatch_plan_id", "")),
        "decision": decision,
        "decision_reasons": validation.get("reasons", []),
        "retry_count": retry_count,
        "retry_budget": retry_budget,
        "next_action": next_action,
        "auto_continue_allowed": auto_continue_allowed,
        "auto_repair_allowed": auto_repair_allowed,
        "human_escalation_required": human_required,
        "followup_packet_planned": False,
        "followup_packet_path": "",
        "runtime_assignment_update_planned": False,
        "safety_notes": [
            "Loop decision is metadata only.",
            "No dispatch, provider call, source application, branch action, commit, push, or merge is allowed by this record.",
        ],
        "created_at": utc_now(),
        "generated_by": "exchange_loop_decision.py",
    }
    out = loop_decision_path(root, str(record["loop_decision_id"]))
    write_json(out, record)
    return out


def iter_json(root: Path, folder: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted((root / folder).glob("*.json")):
        try:
            data = load_json(path)
        except LoopDecisionError:
            continue
        data["_path"] = str(path)
        records.append(data)
    return records


def loop_status(root: Path) -> str:
    root = root.resolve()
    results = iter_json(root, "result_packets")
    validations = iter_json(root, "result_validations")
    decisions = iter_json(root, "loop_decisions")
    repairs = iter_json(root, "repair_packets")

    validated_results = {str(item.get("result_id", "")) for item in validations}
    pending_validation = [
        item for item in results if str(item.get("result_status", "")) in exchange_validate_result.ALLOWED_RESULT_STATUSES
        and str(item.get("result_id", "")) not in validated_results
    ]
    validation_counts = Counter(str(item.get("validation_status", "UNKNOWN")) for item in validations)
    decision_counts = Counter(str(item.get("decision", "UNKNOWN")) for item in decisions)

    lines = [
        "Exchange Loop Status",
        "====================",
        f"root: {root}",
        f"total_imported_results: {len(results)}",
        f"pending_validation: {len(pending_validation)}",
        f"validation_passed: {validation_counts.get('VALIDATION_PASSED', 0)}",
        f"blocked: {validation_counts.get('VALIDATION_BLOCKED', 0) + decision_counts.get('BLOCKED_NEEDS_OPERATOR', 0) + decision_counts.get('BLOCKED_FORBIDDEN_ACTION', 0) + decision_counts.get('BLOCKED_VALIDATION_FAILED', 0)}",
        f"completed_pending_daily_review: {decision_counts.get('COMPLETED_PENDING_DAILY_REVIEW', 0)}",
        f"ready_for_final_human_review: {decision_counts.get('READY_FOR_FINAL_HUMAN_REVIEW', 0)}",
        f"repair_packets_planned: {len(repairs)}",
        "scope: metadata only; no dispatch, model call, source write, or git action.",
    ]
    return "\n".join(lines)


def repair_plan(root: Path, loop_decision_id: str) -> Path:
    root = root.resolve()
    loop_decision_id = require_id(loop_decision_id, "loop_decision_id")
    decision = load_json(loop_decision_path(root, loop_decision_id))
    decision_value = str(decision.get("decision", ""))
    if decision_value not in REPAIR_DECISIONS:
        raise LoopDecisionError(f"repair-plan requires repairable decision; got {decision_value}")

    repair_packet_id = build_repair_packet_id(loop_decision_id)
    out = repair_packet_path(root, repair_packet_id)
    if out.exists():
        raise LoopDecisionError(f"repair packet already exists: {out}")

    packet = {
        "repair_packet_id": repair_packet_id,
        "loop_decision_id": loop_decision_id,
        "result_id": str(decision.get("result_id", "")),
        "validation_id": str(decision.get("validation_id", "")),
        "source_packet_id": str(decision.get("source_packet_id", "")),
        "dispatch_plan_id": str(decision.get("dispatch_plan_id", "")),
        "validation_failure_reason": decision.get("decision_reasons", []),
        "bounded_repair_objective": "Prepare a metadata-only repair packet for a future guarded retry.",
        "allowed_target_adapter": "codex_cli",
        "execution_allowed": False,
        "dispatch_allowed": False,
        "branch_creation_allowed": False,
        "commit_allowed": False,
        "push_allowed": False,
        "merge_allowed": False,
        "created_at": utc_now(),
        "generated_by": "exchange_loop_decision.py",
    }
    write_json(out, packet)
    return out


def cmd_decide(args: argparse.Namespace) -> int:
    out = decide(Path(args.root), args.validation_id)
    print(f"loop decision written: {out}")
    return 0


def cmd_loop_status(args: argparse.Namespace) -> int:
    print(loop_status(Path(args.root)))
    return 0


def cmd_repair_plan(args: argparse.Namespace) -> int:
    out = repair_plan(Path(args.root), args.loop_decision_id)
    print(f"repair packet written: {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exchange loop decision metadata writer.")
    sub = parser.add_subparsers(dest="command")

    help_parser = sub.add_parser("help", help="Show command help.")
    help_parser.set_defaults(func=lambda _args: (print(parser.format_help()), 0)[1])

    decide_parser = sub.add_parser("decide", help="Create a loop decision from a validation record.")
    decide_parser.add_argument("--validation-id", required=True)
    decide_parser.add_argument("--root", default=str(DEFAULT_ROOT))
    decide_parser.set_defaults(func=cmd_decide)

    status_parser = sub.add_parser("loop-status", help="Summarize result validation and loop decisions.")
    status_parser.add_argument("--root", default=str(DEFAULT_ROOT))
    status_parser.set_defaults(func=cmd_loop_status)

    repair_parser = sub.add_parser("repair-plan", help="Create a metadata-only repair packet for repair decisions.")
    repair_parser.add_argument("--loop-decision-id", required=True)
    repair_parser.add_argument("--root", default=str(DEFAULT_ROOT))
    repair_parser.set_defaults(func=cmd_repair_plan)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        print(parser.format_help())
        return 0
    func = getattr(args, "func", None)
    if func is None:
        print(parser.format_help())
        return 0
    try:
        return int(func(args))
    except (LoopDecisionError, exchange_validate_result.ValidateResultError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
