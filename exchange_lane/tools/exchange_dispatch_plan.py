#!/usr/bin/env python3
"""Exchange Lane dispatch planning metadata (non-executing)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import exchange_packet  # noqa: E402


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_ROOT = DEFAULT_ROOT.parents[0] / "runtime_lane"

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

PLANNED_STATUSES = {
    "PLANNED_NOT_DISPATCHED",
    "BLOCKED_NO_SESSION",
    "BLOCKED_SESSION_NOT_READY",
    "BLOCKED_ADAPTER_MISMATCH",
    "BLOCKED_ASSIGNMENT_MISSING",
    "BLOCKED_SOURCE_CHANGED",
    "BLOCKED_PACKET_NOT_READY",
    "BLOCKED_OPERATOR_DECISION_REQUIRED",
}

PACKET_STATUSES_ALLOWED_FOR_PLAN = {"READY_FOR_REVIEW", "APPROVED_FOR_DISPATCH_PLANNING"}
SESSION_BLOCKING_STATUSES = {
    "WAITING_FOR_OPERATOR_APPROVAL",
    "BLOCKED_QUOTA",
    "BLOCKED_ERROR",
    "BLOCKED_MISSING_CONTEXT",
    "CLOSED",
}
MANUAL_ADAPTER_ALIASES = {"manual", "unknown", ""}
PLANNED_STATUS_PRECEDENCE = (
    "BLOCKED_NO_SESSION",
    "BLOCKED_SESSION_NOT_READY",
    "BLOCKED_ASSIGNMENT_MISSING",
    "BLOCKED_ADAPTER_MISMATCH",
    "BLOCKED_SOURCE_CHANGED",
    "BLOCKED_OPERATOR_DECISION_REQUIRED",
)


class DispatchPlanError(Exception):
    """Operator-facing dispatch planning error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require_id(value: str, label: str) -> str:
    if not value or not ID_RE.fullmatch(value):
        raise DispatchPlanError(f"{label} must use letters, numbers, '.', '_' or '-' and cannot be empty")
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
        raise DispatchPlanError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DispatchPlanError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DispatchPlanError(f"JSON root must be an object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def dispatch_plan_path(root: Path, dispatch_plan_id: str) -> Path:
    return root / "dispatch_plans" / f"{require_id(dispatch_plan_id, 'dispatch_plan_id')}.json"


def normalize(path_text: str) -> Path:
    return Path(path_text).expanduser().resolve()


def same_path(left: str, right: str) -> bool:
    try:
        return normalize(left) == normalize(right)
    except Exception:
        return left == right


def choose_planned_status(blocked_statuses: set[str]) -> str:
    for status in PLANNED_STATUS_PRECEDENCE:
        if status in blocked_statuses:
            return status
    return "PLANNED_NOT_DISPATCHED"


def build_dispatch_plan_id(packet_id: str, session_id: str, assignment_id: str) -> str:
    stamp = utc_now().replace(":", "").replace("-", "").replace("Z", "z")
    return require_id(f"{packet_id}__{session_id}__{assignment_id}__{stamp}", "dispatch_plan_id")


def render_report(plan: dict[str, Any]) -> str:
    lines = [
        "# Exchange Dispatch Plan",
        "",
        f"- dispatch_plan_id: `{plan['dispatch_plan_id']}`",
        f"- packet_id: `{plan['packet_id']}`",
        f"- planned_status: `{plan['planned_status']}`",
        f"- compatibility_status: `{plan['compatibility_status']}`",
        f"- target_adapter: `{plan['target_adapter']}`",
        f"- target_session_id: `{plan['target_session_id']}`",
        f"- target_assignment_id: `{plan['target_assignment_id']}`",
        "",
        "## Safety Boundary",
        "",
        "- Dispatch plan is not execution approval.",
        "- Dispatch plan does not dispatch.",
        "- Dispatch plan does not execute.",
        "- Dispatch plan does not start terminals.",
        "- Dispatch plan does not start sessions.",
        "- Dispatch plan does not approve permission prompts.",
        "- Dispatch plan does not run CLIs, models, or browsers.",
        "- Dispatch plan does not create branches, commits, pushes, or merges.",
        "",
        "## Blocked Reasons",
    ]
    blocked = plan.get("blocked_reasons") or []
    if blocked:
        lines.extend(f"- {item}" for item in blocked)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Next Operator Action",
            "",
            str(plan.get("next_operator_action", "")),
        ]
    )
    return "\n".join(lines)


def evaluate_plan(
    root: Path,
    runtime_root: Path,
    *,
    packet_id: str,
    session_id: str,
    assignment_id: str,
) -> dict[str, Any]:
    packet_id = require_id(packet_id, "packet_id")
    session_id = require_id(session_id, "session_id")
    assignment_id = require_id(assignment_id, "assignment_id")

    packet_file = exchange_packet.packet_path(root, packet_id)
    if not packet_file.exists():
        raise DispatchPlanError(f"exchange packet not found: {packet_id}")
    packet = exchange_packet.load_json(packet_file)
    packet_status = str(packet.get("packet_status", ""))
    if packet_status not in PACKET_STATUSES_ALLOWED_FOR_PLAN:
        raise DispatchPlanError(
            "dispatch planning requires packet status READY_FOR_REVIEW or APPROVED_FOR_DISPATCH_PLANNING"
        )

    session_file = runtime_root / "sessions" / f"{session_id}.json"
    assignment_file = runtime_root / "assignments" / f"{assignment_id}.json"
    session = load_json(session_file) if session_file.exists() else None
    assignment = load_json(assignment_file) if assignment_file.exists() else None

    blocked: list[str] = []
    blocked_statuses: set[str] = set()
    compatibility_notes: list[str] = []

    packet_checksum = sha256_file(packet_file)
    source_artifact_path = str(packet.get("source_artifact_path", ""))
    recorded_source_checksum = str(packet.get("source_artifact_checksum", ""))
    current_source_checksum = recorded_source_checksum
    source_artifact = Path(source_artifact_path).expanduser() if source_artifact_path else None
    if source_artifact and source_artifact.exists() and source_artifact.is_file():
        current_source_checksum = sha256_file(source_artifact)
        if recorded_source_checksum and current_source_checksum != recorded_source_checksum:
            blocked_statuses.add("BLOCKED_SOURCE_CHANGED")
            blocked.append("source artifact checksum changed")
    elif source_artifact_path:
        compatibility_notes.append("source artifact is missing or not a file; checksum could not be recomputed")

    if session is None:
        blocked_statuses.add("BLOCKED_NO_SESSION")
        blocked.append(f"runtime session missing: {session_id}")
    else:
        session_status = str(session.get("status", ""))
        if session_status in SESSION_BLOCKING_STATUSES:
            blocked_statuses.add("BLOCKED_SESSION_NOT_READY")
            blocked.append(f"runtime session not ready: {session_status}")

    if assignment is None:
        blocked_statuses.add("BLOCKED_ASSIGNMENT_MISSING")
        blocked.append(f"runtime assignment missing: {assignment_id}")
    else:
        assignment_source = str(assignment.get("task_source_path", ""))
        assignment_checksum = str(assignment.get("task_source_checksum", ""))
        if assignment_source and source_artifact_path:
            if same_path(assignment_source, source_artifact_path):
                compatibility_notes.append("assignment task source path matches packet source artifact")
            elif assignment_checksum and current_source_checksum and assignment_checksum == current_source_checksum:
                compatibility_notes.append("assignment checksum matches packet source artifact checksum")
            else:
                blocked_statuses.add("BLOCKED_OPERATOR_DECISION_REQUIRED")
                blocked.append("assignment task source does not match packet source artifact")
        elif assignment_checksum and current_source_checksum and assignment_checksum == current_source_checksum:
            compatibility_notes.append("assignment checksum matches packet source artifact checksum")
        else:
            compatibility_notes.append("assignment source compatibility could not be fully validated")
        if assignment.get("session_id") != session_id:
            blocked_statuses.add("BLOCKED_OPERATOR_DECISION_REQUIRED")
            blocked.append("assignment is not owned by target session")

    packet_adapter = str(packet.get("target_adapter", ""))
    session_adapter = str(session.get("adapter_type", "")) if session else ""
    assignment_adapter = str(assignment.get("adapter_id", "")) if assignment else ""
    if session and not session_adapter:
        blocked_statuses.add("BLOCKED_OPERATOR_DECISION_REQUIRED")
        blocked.append("runtime session adapter is missing")
    if session and assignment and assignment_adapter and assignment_adapter != session_adapter:
        blocked_statuses.add("BLOCKED_ADAPTER_MISMATCH")
        blocked.append("runtime assignment adapter does not match runtime session adapter")
    if session and packet_adapter not in MANUAL_ADAPTER_ALIASES and packet_adapter != session_adapter:
        blocked_statuses.add("BLOCKED_ADAPTER_MISMATCH")
        blocked.append("packet target adapter does not match runtime session adapter")

    planned_status = choose_planned_status(blocked_statuses)
    plan_id = build_dispatch_plan_id(packet_id, session_id, assignment_id)
    compatibility_status = "PASS" if planned_status == "PLANNED_NOT_DISPATCHED" else "BLOCKED"
    target_adapter = session_adapter or packet_adapter
    plan = {
        "dispatch_plan_id": plan_id,
        "packet_id": packet_id,
        "packet_path": str(packet_file.resolve()),
        "packet_checksum": packet_checksum,
        "source_artifact_path": source_artifact_path,
        "source_artifact_checksum": current_source_checksum,
        "target_adapter": target_adapter,
        "target_session_id": session_id,
        "target_assignment_id": assignment_id,
        "runtime_session_path": str(session_file.resolve()) if session_file.exists() else "",
        "runtime_assignment_path": str(assignment_file.resolve()) if assignment_file.exists() else "",
        "planned_status": planned_status,
        "generated_at": utc_now(),
        "generated_by": "exchange_dispatch_plan.py",
        "compatibility_status": compatibility_status,
        "compatibility_notes": compatibility_notes,
        "quota_notes": str(session.get("quota_status", "")) if session else "",
        "approval_notes": (
            f"packet_status={packet_status}; dispatch planning records intent only and is not execution approval"
        ),
        "operator_notes": [],
        "execution_allowed": False,
        "commit_allowed": False,
        "push_allowed": False,
        "merge_allowed": False,
        "blocked_reasons": blocked,
        "next_operator_action": (
            "Review dispatch plan; future execution lane may consume this plan."
            if not blocked
            else "Resolve blocked reasons, then generate a new dispatch plan."
        ),
        "execution_occurred": False,
        "session_started": False,
        "terminal_started": False,
        "cli_executed": False,
        "model_invoked": False,
        "browser_automated": False,
        "branch_created": False,
        "commit_performed": False,
        "push_performed": False,
        "merge_performed": False,
    }
    return plan


def create_plan(
    root: Path,
    runtime_root: Path,
    *,
    packet_id: str,
    session_id: str,
    assignment_id: str,
    write_report: bool = False,
    mark_dispatch_planned: bool = False,
) -> Path:
    root = root.resolve()
    runtime_root = runtime_root.resolve()
    (root / "dispatch_plans").mkdir(parents=True, exist_ok=True)
    (root / "dispatch_plan_reports").mkdir(parents=True, exist_ok=True)
    plan = evaluate_plan(root, runtime_root, packet_id=packet_id, session_id=session_id, assignment_id=assignment_id)
    out = dispatch_plan_path(root, plan["dispatch_plan_id"])
    write_json(out, plan)
    if write_report:
        report_path = root / "dispatch_plan_reports" / f"{plan['dispatch_plan_id']}.md"
        report_path.write_text(render_report(plan) + "\n", encoding="utf-8")

    if mark_dispatch_planned:
        packet = exchange_packet.get_packet(root, packet_id)
        if packet.get("packet_status") != "APPROVED_FOR_DISPATCH_PLANNING":
            raise DispatchPlanError("--mark-dispatch-planned requires APPROVED_FOR_DISPATCH_PLANNING packet status")
        if plan["planned_status"] != "PLANNED_NOT_DISPATCHED":
            raise DispatchPlanError("--mark-dispatch-planned requires an unblocked plan")
        packet["packet_status"] = "DISPATCH_PLANNED"
        packet["dispatch_plan_id"] = plan["dispatch_plan_id"]
        packet["dispatch_plan_path"] = str(out.resolve())
        packet["updated_at"] = utc_now()
        exchange_packet.write_json(exchange_packet.packet_path(root, packet_id), packet)
    return out


def list_plans(root: Path) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    for path in sorted((root / "dispatch_plans").glob("*.json")):
        data = load_json(path)
        data["_path"] = str(path)
        plans.append(data)
    return plans


def cmd_plan(args: argparse.Namespace) -> int:
    out = create_plan(
        Path(args.root),
        Path(args.runtime_root),
        packet_id=args.packet_id,
        session_id=args.session_id,
        assignment_id=args.assignment_id,
        write_report=args.write_report,
        mark_dispatch_planned=args.mark_dispatch_planned,
    )
    print(f"dispatch plan written: {out}")
    return 0


def cmd_plan_list(args: argparse.Namespace) -> int:
    plans = list_plans(Path(args.root).resolve())
    if not plans:
        print("no dispatch plans")
        return 0
    print("dispatch plans:")
    for plan in plans:
        print(
            f"- {plan.get('dispatch_plan_id', '')} | packet={plan.get('packet_id', '')} | "
            f"session={plan.get('target_session_id', '')} | assignment={plan.get('target_assignment_id', '')} | "
            f"status={plan.get('planned_status', '')}"
        )
    return 0


def cmd_plan_status(args: argparse.Namespace) -> int:
    plan = load_json(dispatch_plan_path(Path(args.root).resolve(), args.dispatch_plan_id))
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exchange dispatch planning metadata (non-executing).")
    sub = parser.add_subparsers(dest="command")

    help_parser = sub.add_parser("help", help="Show command help.")
    help_parser.set_defaults(func=lambda _args: (print(parser.format_help()), 0)[1])

    plan = sub.add_parser("plan", help="Create dispatch plan metadata.")
    plan.add_argument("--packet-id", required=True)
    plan.add_argument("--session-id", required=True)
    plan.add_argument("--assignment-id", required=True)
    plan.add_argument("--root", default=str(DEFAULT_ROOT))
    plan.add_argument("--runtime-root", default=str(DEFAULT_RUNTIME_ROOT))
    plan.add_argument("--write-report", action="store_true")
    plan.add_argument("--mark-dispatch-planned", action="store_true")
    plan.set_defaults(func=cmd_plan)

    plan_status = sub.add_parser("plan-status", help="Show one dispatch plan.")
    plan_status.add_argument("--dispatch-plan-id", required=True)
    plan_status.add_argument("--root", default=str(DEFAULT_ROOT))
    plan_status.set_defaults(func=cmd_plan_status)

    plan_list = sub.add_parser("plan-list", help="List dispatch plans.")
    plan_list.add_argument("--root", default=str(DEFAULT_ROOT))
    plan_list.set_defaults(func=cmd_plan_list)
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
    except (DispatchPlanError, exchange_packet.ExchangePacketError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
