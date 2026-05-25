#!/usr/bin/env python3
"""Runtime Session Lane metadata registry.

This tool records manually operated runtime sessions and blockers only. It does
not start terminals, execute CLIs, approve prompts, run worker prompts, or
perform git actions.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_ROOT = SCRIPT_PATH.parents[1]

SESSION_STATUSES = {
    "PLANNED",
    "READY",
    "RUNNING",
    "WAITING_FOR_OPERATOR_APPROVAL",
    "BLOCKED_QUOTA",
    "BLOCKED_ERROR",
    "BLOCKED_MISSING_CONTEXT",
    "COMPLETED_PENDING_REVIEW",
    "CLOSED",
}

BLOCKER_TYPES = {
    "WAITING_FOR_PERMISSION_PROMPT",
    "QUOTA_EXHAUSTED_OR_RATE_LIMITED",
    "CLI_AUTH_EXPIRED",
    "TOOL_REQUEST_OUT_OF_SCOPE",
    "TERMINAL_FROZEN_OR_UNRESPONSIVE",
    "FILE_CONFLICT_RISK",
    "GIT_DIRTY_UNEXPECTED",
    "VALIDATION_FAILED",
    "UNKNOWN_BLOCKER",
}

BLOCKER_STATUS_MAP = {
    "WAITING_FOR_PERMISSION_PROMPT": "WAITING_FOR_OPERATOR_APPROVAL",
    "QUOTA_EXHAUSTED_OR_RATE_LIMITED": "BLOCKED_QUOTA",
    "CLI_AUTH_EXPIRED": "BLOCKED_ERROR",
    "TOOL_REQUEST_OUT_OF_SCOPE": "BLOCKED_ERROR",
    "TERMINAL_FROZEN_OR_UNRESPONSIVE": "BLOCKED_ERROR",
    "FILE_CONFLICT_RISK": "BLOCKED_ERROR",
    "GIT_DIRTY_UNEXPECTED": "BLOCKED_ERROR",
    "VALIDATION_FAILED": "BLOCKED_ERROR",
    "UNKNOWN_BLOCKER": "BLOCKED_ERROR",
}

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class RuntimeSessionError(Exception):
    """Raised for operator-facing runtime metadata errors."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require_id(value: str, label: str) -> str:
    if not value or not ID_RE.fullmatch(value):
        raise RuntimeSessionError(f"{label} must use letters, numbers, '.', '_' or '-' and cannot be empty")
    return value


def ensure_dirs(root: Path) -> None:
    for name in ("sessions", "blockers"):
        (root / name).mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeSessionError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeSessionError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeSessionError(f"JSON root must be an object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def session_path(root: Path, session_id: str) -> Path:
    return root / "sessions" / f"{require_id(session_id, 'session_id')}.json"


def blocker_path(root: Path, blocker_id: str) -> Path:
    return root / "blockers" / f"{require_id(blocker_id, 'blocker_id')}.json"


def adapter_profiles(root: Path) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    adapter_root = root / "adapters"
    for path in sorted(adapter_root.glob("*_profile.json")):
        data = load_json(path)
        adapter_id = str(data.get("adapter_id", ""))
        if adapter_id:
            profiles[adapter_id] = data
    return profiles


def register_session(
    root: Path,
    *,
    session_id: str,
    adapter: str,
    label: str,
    cwd: str,
    lane: str,
    task: str,
) -> Path:
    ensure_dirs(root)
    session_id = require_id(session_id, "session_id")
    profiles = adapter_profiles(root)
    if adapter not in profiles:
        raise RuntimeSessionError(f"unknown adapter: {adapter}")
    path = session_path(root, session_id)
    if path.exists():
        raise RuntimeSessionError(f"session already exists: {session_id}")

    profile = profiles[adapter]
    now = utc_now()
    data = {
        "session_id": session_id,
        "session_label": label,
        "adapter_type": adapter,
        "terminal_type": profile.get("launch_mode", "manual_terminal"),
        "cwd": cwd,
        "lane": lane,
        "assigned_task": task,
        "status": "PLANNED",
        "auth_mode": profile.get("auth_mode", "unknown"),
        "quota_policy": profile.get("quota_model", "unknown"),
        "quota_status": "UNKNOWN",
        "approval_mode": "MANUAL_OPERATOR",
        "blocked_reason": "",
        "current_prompt_packet": "",
        "allowed_write_roots": [cwd],
        "forbidden_paths": [".git/", "private_config/", "model_weights/", "raw_generated_graph_outputs/"],
        "started_at": now,
        "last_updated": now,
        "operator_notes": [],
        "safety_class": "METADATA_ONLY",
        "commit_allowed": False,
        "push_allowed": False,
        "merge_allowed": False,
        "automated_terminal_control": False,
        "runtime_lane_git_actions_performed": False,
    }
    write_json(path, data)
    return path


def update_status(root: Path, *, session_id: str, status: str, note: str) -> Path:
    if status not in SESSION_STATUSES:
        raise RuntimeSessionError(f"invalid status: {status}")
    path = session_path(root, session_id)
    data = load_json(path)
    data["status"] = status
    data["last_updated"] = utc_now()
    if status not in {"WAITING_FOR_OPERATOR_APPROVAL", "BLOCKED_QUOTA", "BLOCKED_ERROR", "BLOCKED_MISSING_CONTEXT"}:
        data["blocked_reason"] = ""
    if note:
        notes = data.setdefault("operator_notes", [])
        if not isinstance(notes, list):
            notes = []
            data["operator_notes"] = notes
        notes.append({"timestamp": data["last_updated"], "note": note})
    write_json(path, data)
    return path


def report_blocker(root: Path, *, session_id: str, blocker_type: str, description: str) -> Path:
    if blocker_type not in BLOCKER_TYPES:
        raise RuntimeSessionError(f"invalid blocker type: {blocker_type}")
    session_file = session_path(root, session_id)
    session = load_json(session_file)
    now = utc_now()
    safe_type = blocker_type.lower()
    blocker_id = f"{session_id}__{safe_type}__{now.replace(':', '').replace('-', '').replace('Z', 'z')}"
    blocker = {
        "blocker_id": blocker_id,
        "session_id": session_id,
        "blocker_type": blocker_type,
        "detected_or_reported_at": now,
        "description": description,
        "operator_action_required": "Review the session manually and decide the next safe action.",
        "suggested_safe_response": suggested_response(blocker_type),
        "resolved_at": "",
        "resolution": "",
        "followup_required": True,
    }
    session["status"] = BLOCKER_STATUS_MAP[blocker_type]
    session["blocked_reason"] = f"{blocker_type}: {description}"
    session["last_updated"] = now
    write_json(blocker_path(root, blocker_id), blocker)
    write_json(session_file, session)
    return blocker_path(root, blocker_id)


def suggested_response(blocker_type: str) -> str:
    responses = {
        "WAITING_FOR_PERMISSION_PROMPT": "Operator must approve or deny the prompt in the CLI directly.",
        "QUOTA_EXHAUSTED_OR_RATE_LIMITED": "Pause or switch tasks; do not assume alternate provider access.",
        "CLI_AUTH_EXPIRED": "Operator must re-authenticate in the CLI manually.",
        "TOOL_REQUEST_OUT_OF_SCOPE": "Stop the session and revise task boundaries before continuing.",
        "TERMINAL_FROZEN_OR_UNRESPONSIVE": "Inspect the terminal manually; record whether retry is safe.",
        "FILE_CONFLICT_RISK": "Review changed files and ownership before proceeding.",
        "GIT_DIRTY_UNEXPECTED": "Inspect git status before any further writes.",
        "VALIDATION_FAILED": "Review validation output and assign a bounded fix task.",
        "UNKNOWN_BLOCKER": "Collect more context without executing additional work.",
    }
    return responses.get(blocker_type, "Manual operator review required.")


def unresolved_blockers(root: Path, session_id: str) -> list[dict[str, Any]]:
    blockers = []
    for path in sorted((root / "blockers").glob("*.json")):
        data = load_json(path)
        if data.get("session_id") == session_id and not data.get("resolved_at"):
            blockers.append(data)
    return blockers


def resolve_blocker(root: Path, *, blocker_id: str, resolution: str) -> Path:
    path = blocker_path(root, blocker_id)
    blocker = load_json(path)
    if blocker.get("resolved_at"):
        raise RuntimeSessionError(f"blocker already resolved: {blocker_id}")
    now = utc_now()
    blocker["resolved_at"] = now
    blocker["resolution"] = resolution
    blocker["followup_required"] = False
    write_json(path, blocker)

    session_id = str(blocker.get("session_id", ""))
    session_file = session_path(root, session_id)
    session = load_json(session_file)
    if not unresolved_blockers(root, session_id):
        if session.get("status") in {"WAITING_FOR_OPERATOR_APPROVAL", "BLOCKED_QUOTA", "BLOCKED_ERROR", "BLOCKED_MISSING_CONTEXT"}:
            session["status"] = "READY"
            session["blocked_reason"] = ""
    session["last_updated"] = now
    notes = session.setdefault("operator_notes", [])
    if isinstance(notes, list):
        notes.append({"timestamp": now, "note": f"Resolved blocker {blocker_id}: {resolution}"})
    write_json(session_file, session)
    return path


def list_sessions(root: Path) -> list[dict[str, Any]]:
    return [load_json(path) for path in sorted((root / "sessions").glob("*.json"))]


def list_blockers(root: Path) -> list[dict[str, Any]]:
    return [load_json(path) for path in sorted((root / "blockers").glob("*.json"))]


def render_adapter_list(root: Path) -> str:
    lines = ["Runtime Adapter Profiles", "========================", ""]
    profiles = adapter_profiles(root)
    if not profiles:
        lines.append("No adapter profiles found.")
        return "\n".join(lines)
    for adapter_id, data in sorted(profiles.items()):
        lines.append(f"- {adapter_id}: {data.get('display_name', '')}")
        lines.append(f"  launch_mode: {data.get('launch_mode', '')}")
        lines.append(f"  auth_mode: {data.get('auth_mode', '')}")
        lines.append(f"  quota_model: {data.get('quota_model', '')}")
    return "\n".join(lines)


def render_status(root: Path) -> str:
    sessions = list_sessions(root)
    blockers = list_blockers(root)
    open_blockers = [b for b in blockers if not b.get("resolved_at")]
    lines = [
        "Runtime Session Lane Status",
        "===========================",
        f"root: {root}",
        f"sessions: {len(sessions)}",
        f"blockers: {len(blockers)}",
        f"open_blockers: {len(open_blockers)}",
        "",
        "Sessions:",
    ]
    if not sessions:
        lines.append("- none")
    for data in sessions:
        lines.append(
            "- {session_id} | {session_label} | {adapter_type} | {lane} | {status} | quota={quota_status}".format(
                **{key: data.get(key, "") for key in ("session_id", "session_label", "adapter_type", "lane", "status", "quota_status")}
            )
        )
        lines.append(f"  task: {data.get('assigned_task', '')}")
        if data.get("blocked_reason"):
            lines.append(f"  blocked_reason: {data.get('blocked_reason')}")
        lines.append(f"  last_updated: {data.get('last_updated', '')}")
    lines.append("")
    lines.append("Open Blockers:")
    if not open_blockers:
        lines.append("- none")
    for data in open_blockers:
        lines.append(f"- {data.get('blocker_id')} | {data.get('session_id')} | {data.get('blocker_type')}")
        lines.append(f"  description: {data.get('description', '')}")
    return "\n".join(lines)


def render_help() -> str:
    return """Runtime Session Lane commands
=============================

python runtime_lane/tools/runtime_session.py help
python runtime_lane/tools/runtime_session.py adapter-list
python runtime_lane/tools/runtime_session.py status --root runtime_lane
python runtime_lane/tools/runtime_session.py register --session-id <id> --adapter <adapter_id> --label "<label>" --cwd <path> --lane <lane> --task "<task>"
python runtime_lane/tools/runtime_session.py update-status --session-id <id> --status <status> --note "<note>"
python runtime_lane/tools/runtime_session.py report-blocker --session-id <id> --type <blocker_type> --description "<description>"
python runtime_lane/tools/runtime_session.py resolve-blocker --blocker-id <id> --resolution "<resolution>"

Safety boundary:
- metadata only
- no terminal launch
- no CLI/model execution
- no prompt approval
- no worker execution
- no branch, commit, push, or merge
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Runtime Session Lane metadata registry.")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("help")
    adapter_list = sub.add_parser("adapter-list")
    adapter_list.add_argument("--root", default=str(DEFAULT_ROOT))
    status = sub.add_parser("status")
    status.add_argument("--root", default=str(DEFAULT_ROOT))

    register = sub.add_parser("register")
    register.add_argument("--root", default=str(DEFAULT_ROOT))
    register.add_argument("--session-id", required=True)
    register.add_argument("--adapter", required=True)
    register.add_argument("--label", required=True)
    register.add_argument("--cwd", required=True)
    register.add_argument("--lane", required=True)
    register.add_argument("--task", required=True)

    update = sub.add_parser("update-status")
    update.add_argument("--root", default=str(DEFAULT_ROOT))
    update.add_argument("--session-id", required=True)
    update.add_argument("--status", required=True)
    update.add_argument("--note", default="")

    blocker = sub.add_parser("report-blocker")
    blocker.add_argument("--root", default=str(DEFAULT_ROOT))
    blocker.add_argument("--session-id", required=True)
    blocker.add_argument("--type", required=True)
    blocker.add_argument("--description", required=True)

    resolve = sub.add_parser("resolve-blocker")
    resolve.add_argument("--root", default=str(DEFAULT_ROOT))
    resolve.add_argument("--blocker-id", required=True)
    resolve.add_argument("--resolution", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command in {None, "help"}:
            print(render_help())
            return 0
        root = Path(args.root).resolve()
        if args.command == "adapter-list":
            print(render_adapter_list(root))
            return 0
        if args.command == "status":
            print(render_status(root))
            return 0
        if args.command == "register":
            path = register_session(
                root,
                session_id=args.session_id,
                adapter=args.adapter,
                label=args.label,
                cwd=args.cwd,
                lane=args.lane,
                task=args.task,
            )
            print(f"Registered runtime session: {path}")
            return 0
        if args.command == "update-status":
            path = update_status(root, session_id=args.session_id, status=args.status, note=args.note)
            print(f"Updated runtime session: {path}")
            return 0
        if args.command == "report-blocker":
            path = report_blocker(root, session_id=args.session_id, blocker_type=args.type, description=args.description)
            print(f"Recorded runtime blocker: {path}")
            return 0
        if args.command == "resolve-blocker":
            path = resolve_blocker(root, blocker_id=args.blocker_id, resolution=args.resolution)
            print(f"Resolved runtime blocker: {path}")
            return 0
    except RuntimeSessionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

