#!/usr/bin/env python3
"""Runtime Session Lane metadata registry.

This tool records manually operated runtime sessions and blockers only. It does
not start terminals, execute CLIs, approve prompts, run worker prompts, or
perform git actions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
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

ASSIGNMENT_STATUSES = {
    "PLANNED",
    "ASSIGNED_NOT_STARTED",
    "IN_PROGRESS",
    "WAITING_FOR_OPERATOR_APPROVAL",
    "BLOCKED_SESSION",
    "BLOCKED_QUOTA",
    "BLOCKED_DEPENDENCY",
    "BLOCKED_MISSING_CONTEXT",
    "COMPLETED_PENDING_REVIEW",
    "CLOSED",
    "ABANDONED",
}

ACTIVE_ASSIGNMENT_STATUSES = {
    "PLANNED",
    "ASSIGNED_NOT_STARTED",
    "IN_PROGRESS",
    "WAITING_FOR_OPERATOR_APPROVAL",
    "BLOCKED_SESSION",
    "BLOCKED_QUOTA",
    "BLOCKED_DEPENDENCY",
    "BLOCKED_MISSING_CONTEXT",
    "COMPLETED_PENDING_REVIEW",
}

BLOCKED_ASSIGNMENT_STATUSES = {
    "WAITING_FOR_OPERATOR_APPROVAL",
    "BLOCKED_SESSION",
    "BLOCKED_QUOTA",
    "BLOCKED_DEPENDENCY",
    "BLOCKED_MISSING_CONTEXT",
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

TASK_SOURCE_TYPES = {
    "discovery_execution_queue",
    "discovery_handoff_bundle",
    "product_development_manifest",
    "product_development_implementation_plan",
    "product_review_artifact",
    "product_design_run_packet",
    "manual_operator_task",
    "other_metadata_artifact",
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
    for name in ("sessions", "blockers", "assignments", "workload_reports"):
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


def assignment_path(root: Path, assignment_id: str) -> Path:
    return root / "assignments" / f"{require_id(assignment_id, 'assignment_id')}.json"


def adapter_profiles(root: Path) -> dict[str, dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}
    adapter_root = root / "adapters"
    for path in sorted(adapter_root.glob("*_profile.json")):
        data = load_json(path)
        adapter_id = str(data.get("adapter_id", ""))
        if adapter_id:
            profiles[adapter_id] = data
    return profiles


def load_session(root: Path, session_id: str) -> dict[str, Any]:
    return load_json(session_path(root, session_id))


def load_assignment(root: Path, assignment_id: str) -> dict[str, Any]:
    return load_json(assignment_path(root, assignment_id))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_path_for_compare(path_text: str) -> Path:
    path = Path(path_text).expanduser()
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


def open_blocker_ids(root: Path, session_id: str) -> list[str]:
    blocker_ids: list[str] = []
    for path in sorted((root / "blockers").glob("*.json")):
        data = load_json(path)
        if data.get("session_id") == session_id and not data.get("resolved_at"):
            blocker_ids.append(str(data.get("blocker_id", path.stem)))
    return blocker_ids


def assignment_status_for_session(session: dict[str, Any], blocker_ids: list[str]) -> str:
    session_status = str(session.get("status", ""))
    if session_status == "BLOCKED_QUOTA":
        return "BLOCKED_QUOTA"
    if session_status == "WAITING_FOR_OPERATOR_APPROVAL":
        return "WAITING_FOR_OPERATOR_APPROVAL"
    if session_status in {"BLOCKED_ERROR", "BLOCKED_MISSING_CONTEXT"}:
        return "BLOCKED_SESSION"
    if blocker_ids:
        return "BLOCKED_SESSION"
    if session_status == "READY":
        return "ASSIGNED_NOT_STARTED"
    return "ASSIGNED_NOT_STARTED"


def load_assignments(root: Path) -> list[dict[str, Any]]:
    assignments: list[dict[str, Any]] = []
    assignments_root = root / "assignments"
    for path in sorted(assignments_root.glob("*.json")):
        assignments.append(load_json(path))
    return assignments


def assignment_display_blockers(root: Path, assignment: dict[str, Any]) -> list[str]:
    blockers = [str(blocker_id) for blocker_id in assignment.get("blocker_ids", []) if blocker_id]
    if blockers:
        return blockers
    session_id = str(assignment.get("session_id", ""))
    if session_id:
        return open_blocker_ids(root, session_id)
    return []


def duplicate_active_assignment_exists(root: Path, session_id: str, task_source_path: Path) -> bool:
    target = normalize_path_for_compare(str(task_source_path))
    for assignment in load_assignments(root):
        if assignment.get("session_id") != session_id:
            continue
        if str(assignment.get("assignment_status", "")) not in ACTIVE_ASSIGNMENT_STATUSES:
            continue
        existing_path = str(assignment.get("task_source_path", ""))
        if existing_path and normalize_path_for_compare(existing_path) == target:
            return True
    return False


def derive_task_source_checksum(path: Path) -> str:
    if path.is_file():
        return sha256_file(path)
    return ""


def assignment_is_blocked(assignment: dict[str, Any]) -> bool:
    status = str(assignment.get("assignment_status", ""))
    return status in BLOCKED_ASSIGNMENT_STATUSES


def create_assignment(
    root: Path,
    *,
    session_id: str,
    task_source: str,
    label: str,
    task_source_type: str,
    allow_duplicate: bool = False,
) -> Path:
    ensure_dirs(root)
    session = load_session(root, session_id)
    profiles = adapter_profiles(root)
    adapter_id = str(session.get("adapter_type", ""))
    if adapter_id not in profiles:
        raise RuntimeSessionError(f"session references unknown adapter: {adapter_id}")
    if task_source_type not in TASK_SOURCE_TYPES:
        raise RuntimeSessionError(f"invalid task source type: {task_source_type}")
    source_path = Path(task_source).expanduser()
    if not source_path.exists():
        raise RuntimeSessionError(f"task source does not exist: {task_source}")
    resolved_source = normalize_path_for_compare(str(source_path))
    if duplicate_active_assignment_exists(root, session_id, resolved_source) and not allow_duplicate:
        raise RuntimeSessionError(f"active assignment already exists for session {session_id} and task source {resolved_source}")

    blockers = open_blocker_ids(root, session_id)
    now = utc_now()
    assignment_id = require_id(
        f"{session_id}__{task_source_type}__{source_path.stem}__{now.replace(':', '').replace('-', '').replace('Z', 'z')}",
        "assignment_id",
    )
    session_status = assignment_status_for_session(session, blockers)
    assignment = {
        "assignment_id": assignment_id,
        "session_id": session_id,
        "adapter_id": adapter_id,
        "assignment_label": label,
        "task_source_type": task_source_type,
        "task_source_path": str(resolved_source),
        "task_source_checksum": derive_task_source_checksum(resolved_source),
        "lane": session.get("lane", ""),
        "intended_worker": adapter_id,
        "assigned_at": now,
        "last_updated": now,
        "assignment_status": session_status if session_status.startswith("BLOCKED") or session_status == "WAITING_FOR_OPERATOR_APPROVAL" else "ASSIGNED_NOT_STARTED",
        "priority": "normal",
        "expected_outputs": [],
        "allowed_write_roots": list(session.get("allowed_write_roots", [])) or [session.get("cwd", "")],
        "forbidden_paths": list(session.get("forbidden_paths", [])),
        "human_approval_required": True,
        "depends_on_assignments": [],
        "blocker_ids": blockers,
        "quota_notes": session.get("quota_status", ""),
        "operator_notes": [],
        "execution_allowed": False,
        "commit_allowed": False,
        "push_allowed": False,
        "merge_allowed": False,
        "task_source_missing": False,
    }
    write_json(assignment_path(root, assignment_id), assignment)
    return assignment_path(root, assignment_id)


def update_assignment(root: Path, *, assignment_id: str, status: str, note: str) -> Path:
    if status not in ASSIGNMENT_STATUSES:
        raise RuntimeSessionError(f"invalid assignment status: {status}")
    path = assignment_path(root, assignment_id)
    data = load_json(path)
    data["assignment_status"] = status
    data["last_updated"] = utc_now()
    notes = data.setdefault("operator_notes", [])
    if not isinstance(notes, list):
        notes = []
        data["operator_notes"] = notes
    if note:
        notes.append({"timestamp": data["last_updated"], "note": note})
    write_json(path, data)
    return path


def list_assignments(root: Path) -> list[dict[str, Any]]:
    return load_assignments(root)


def assignment_summary_line(assignment: dict[str, Any]) -> tuple[str, str]:
    blockers = assignment.get("blocker_ids", [])
    blocker_text = ", ".join(str(item) for item in blockers) if blockers else "none"
    return (
        f"- {assignment.get('assignment_id', '')} | session={assignment.get('session_id', '')} | "
        f"adapter={assignment.get('adapter_id', '')} | status={assignment.get('assignment_status', '')} | "
        f"last_updated={assignment.get('last_updated', '')}"
    ), blocker_text


def render_assignment_list(root: Path) -> str:
    assignments = sorted(
        list_assignments(root),
        key=lambda item: (
            str(item.get("last_updated", "")),
            str(item.get("assignment_id", "")),
        ),
    )
    lines = [
        "Runtime Assignment Registry",
        "===========================",
        f"root: {root}",
        f"assignments: {len(assignments)}",
        "",
    ]
    if not assignments:
        lines.append("- none")
        return "\n".join(lines)
    for assignment in assignments:
        line, blocker_text = assignment_summary_line(assignment)
        lines.append(line)
        lines.append(f"  label: {assignment.get('assignment_label', '')}")
        lines.append(f"  source: {assignment.get('task_source_path', '')}")
        lines.append(f"  blockers: {blocker_text}")
    return "\n".join(lines)


def render_assignment_status(root: Path, assignment_id: str) -> str:
    assignment = load_assignment(root, assignment_id)
    session_id = str(assignment.get("session_id", ""))
    session = load_session(root, session_id)
    blockers = assignment_display_blockers(root, assignment)
    lines = [
        "Runtime Assignment Status",
        "=========================",
        f"root: {root}",
        f"assignment_id: {assignment.get('assignment_id', '')}",
        f"assignment_status: {assignment.get('assignment_status', '')}",
        f"assignment_label: {assignment.get('assignment_label', '')}",
        f"session_id: {session_id}",
        f"session_status: {session.get('status', '')}",
        f"session_blocked_reason: {session.get('blocked_reason', '')}",
        f"adapter_id: {assignment.get('adapter_id', '')}",
        f"intended_worker: {assignment.get('intended_worker', '')}",
        f"task_source_type: {assignment.get('task_source_type', '')}",
        f"task_source_path: {assignment.get('task_source_path', '')}",
        f"task_source_checksum: {assignment.get('task_source_checksum', '')}",
        f"lane: {assignment.get('lane', '')}",
        f"priority: {assignment.get('priority', '')}",
        f"quota_notes: {assignment.get('quota_notes', '')}",
        f"human_approval_required: {assignment.get('human_approval_required', '')}",
        f"execution_allowed: {assignment.get('execution_allowed', '')}",
        f"commit_allowed: {assignment.get('commit_allowed', '')}",
        f"push_allowed: {assignment.get('push_allowed', '')}",
        f"merge_allowed: {assignment.get('merge_allowed', '')}",
        f"blocked_by_session: {'yes' if session.get('status') in {'WAITING_FOR_OPERATOR_APPROVAL', 'BLOCKED_QUOTA', 'BLOCKED_ERROR', 'BLOCKED_MISSING_CONTEXT'} else 'no'}",
        f"linked_blockers: {', '.join(blockers) if blockers else 'none'}",
        "operator_notes:",
    ]
    notes = assignment.get("operator_notes", [])
    if isinstance(notes, list) and notes:
        for note in notes:
            if isinstance(note, dict):
                lines.append(f"- {note.get('timestamp', '')}: {note.get('note', '')}")
            else:
                lines.append(f"- {note}")
    else:
        lines.append("- none")
    lines.extend([
        "",
        "Session Notes:",
    ])
    session_notes = session.get("operator_notes", [])
    if isinstance(session_notes, list) and session_notes:
        for note in session_notes:
            if isinstance(note, dict):
                lines.append(f"- {note.get('timestamp', '')}: {note.get('note', '')}")
            else:
                lines.append(f"- {note}")
    else:
        lines.append("- none")
    return "\n".join(lines)


def scan_unassigned_candidates(root: Path) -> list[dict[str, str]]:
    repo_root = root.parent
    candidates: list[tuple[str, Path]] = []
    patterns = [
        ("discovery_execution_queue", repo_root / "discovery_lane" / "execution_queues", "*.json"),
        ("product_development_implementation_plan", repo_root / "product_development_lane" / "implementation_plans", "*.md"),
        ("product_development_manifest", repo_root / "product_development_lane" / "manifests", "*.json"),
        ("product_review_artifact_manifest", repo_root / "product_development_lane" / "review_artifacts" / "manifests", "*.json"),
        ("product_design_run_packet", repo_root / "products", "*"),
    ]
    for source_type, base, pattern in patterns:
        if source_type == "product_design_run_packet":
            if base.exists():
                for product_dir in sorted(base.glob("*")):
                    if not product_dir.is_dir():
                        continue
                    run_base = product_dir / "design_runs" / "open_design"
                    if not run_base.exists():
                        continue
                    for run_dir in sorted(run_base.glob("*")):
                        design_run = run_dir / "design_run.yaml"
                        if design_run.is_file():
                            candidates.append((source_type, design_run))
            continue
        if base.exists():
            for path in sorted(base.glob(pattern)):
                if path.is_file():
                    candidates.append((source_type, path))

    assigned_paths = {
        normalize_path_for_compare(str(assignment.get("task_source_path", "")))
        for assignment in load_assignments(root)
        if assignment.get("task_source_path")
    }
    visible: list[dict[str, str]] = []
    for source_type, candidate in candidates:
        candidate_path = normalize_path_for_compare(str(candidate))
        if candidate_path not in assigned_paths:
            visible.append({"task_source_type": source_type, "task_source_path": str(candidate_path)})
    return visible


def render_unassigned(root: Path) -> str:
    candidates = scan_unassigned_candidates(root)
    lines = [
        "Runtime Unassigned Candidate Tasks",
        "==================================",
        f"root: {root}",
        f"unassigned_candidates: {len(candidates)}",
        "",
    ]
    if not candidates:
        lines.append("- none")
        return "\n".join(lines)
    for candidate in candidates:
        lines.append(f"- {candidate['task_source_type']} | {candidate['task_source_path']}")
    return "\n".join(lines)


def render_workload(root: Path) -> str:
    sessions = list_sessions(root)
    assignments = list_assignments(root)
    assignments_by_session: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for assignment in assignments:
        assignments_by_session[str(assignment.get("session_id", ""))].append(assignment)
    blocked_sessions = [session for session in sessions if str(session.get("status", "")) in {"WAITING_FOR_OPERATOR_APPROVAL", "BLOCKED_QUOTA", "BLOCKED_ERROR", "BLOCKED_MISSING_CONTEXT"}]
    pending_review = [assignment for assignment in assignments if str(assignment.get("assignment_status", "")) == "COMPLETED_PENDING_REVIEW"]
    overloaded_sessions: list[tuple[str, int]] = []
    for session in sessions:
        active_assignments = [assignment for assignment in assignments_by_session.get(str(session.get("session_id", "")), []) if str(assignment.get("assignment_status", "")) in ACTIVE_ASSIGNMENT_STATUSES]
        if len(active_assignments) > 3:
            overloaded_sessions.append((str(session.get("session_id", "")), len(active_assignments)))
    unassigned_candidates = scan_unassigned_candidates(root)

    lines = [
        "Runtime Workload Dashboard",
        "==========================",
        f"root: {root}",
        f"generated_at: {utc_now()}",
        f"sessions: {len(sessions)}",
        f"assignments: {len(assignments)}",
        f"blocked_sessions: {len(blocked_sessions)}",
        f"blocked_assignments: {len([assignment for assignment in assignments if assignment_is_blocked(assignment)])}",
        f"completed_pending_review: {len(pending_review)}",
        f"overloaded_sessions: {len(overloaded_sessions)}",
        f"unassigned_candidates: {len(unassigned_candidates)}",
        "",
        "Sessions:",
    ]
    if not sessions:
        lines.append("- none")
    for session in sessions:
        session_id = str(session.get("session_id", ""))
        session_assignments = sorted(assignments_by_session.get(session_id, []), key=lambda item: (str(item.get("assignment_status", "")), str(item.get("assignment_id", ""))))
        active_assignments = [assignment for assignment in session_assignments if str(assignment.get("assignment_status", "")) in ACTIVE_ASSIGNMENT_STATUSES]
        blocked_assignments = [assignment for assignment in session_assignments if assignment_is_blocked(assignment)]
        completed_pending = [assignment for assignment in session_assignments if str(assignment.get("assignment_status", "")) == "COMPLETED_PENDING_REVIEW"]
        overloaded = len(active_assignments) > 3
        lines.append(
            f"- {session_id} | adapter={session.get('adapter_type', '')} | status={session.get('status', '')} | "
            f"active={len(active_assignments)} | blocked={len(blocked_assignments)} | pending_review={len(completed_pending)} | overloaded={'yes' if overloaded else 'no'}"
        )
        lines.append(f"  label: {session.get('session_label', '')}")
        lines.append(f"  task: {session.get('assigned_task', '')}")
        lines.append(f"  quota: {session.get('quota_status', '')}")
        lines.append(f"  auth: {session.get('auth_mode', '')}")
        if session.get("blocked_reason"):
            lines.append(f"  blocked_reason: {session.get('blocked_reason')}")
        if active_assignments:
            lines.append("  active_assignments:")
            for assignment in active_assignments:
                lines.append(
                    f"  - {assignment.get('assignment_id', '')} | {assignment.get('assignment_label', '')} | {assignment.get('assignment_status', '')} | {assignment.get('task_source_path', '')}"
                )
        else:
            lines.append("  active_assignments: none")
        if blocked_assignments:
            lines.append("  blocked_assignments:")
            for assignment in blocked_assignments:
                lines.append(
                    f"  - {assignment.get('assignment_id', '')} | {assignment.get('assignment_label', '')} | {assignment.get('assignment_status', '')}"
                )
        else:
            lines.append("  blocked_assignments: none")
        if completed_pending:
            lines.append("  completed_pending_review:")
            for assignment in completed_pending:
                lines.append(
                    f"  - {assignment.get('assignment_id', '')} | {assignment.get('assignment_label', '')}"
                )
        else:
            lines.append("  completed_pending_review: none")
        if overloaded:
            lines.append("  recommended_attention: session has more than 3 active assignments; review ownership and split work if needed.")
        elif blocked_assignments:
            lines.append("  recommended_attention: investigate blockers before continuing.")
        else:
            lines.append("  recommended_attention: none")
    lines.extend(
        [
            "",
            "Blocked Sessions:",
        ]
    )
    if not blocked_sessions:
        lines.append("- none")
    else:
        for session in blocked_sessions:
            lines.append(f"- {session.get('session_id', '')} | {session.get('status', '')} | {session.get('blocked_reason', '')}")
    lines.extend(
        [
            "",
            "Completed Pending Review Assignments:",
        ]
    )
    if not pending_review:
        lines.append("- none")
    else:
        for assignment in pending_review:
            lines.append(
                f"- {assignment.get('assignment_id', '')} | session={assignment.get('session_id', '')} | {assignment.get('assignment_label', '')}"
            )
    lines.extend(
        [
            "",
            "Unassigned Candidate Tasks:",
        ]
    )
    if not unassigned_candidates:
        lines.append("- none")
    else:
        for candidate in unassigned_candidates:
            lines.append(f"- {candidate['task_source_type']} | {candidate['task_source_path']}")
    lines.extend(
        [
            "",
            "Safety Reminder:",
            "- workload is metadata only",
            "- workload does not execute CLIs",
            "- workload does not start terminals",
            "- workload does not approve prompts",
            "- workload does not create branches",
            "- workload does not commit, push, or merge",
        ]
    )
    return "\n".join(lines)


def write_workload_report(root: Path, content: str) -> Path:
    ensure_dirs(root)
    path = root / "workload_reports" / "runtime_workload_report.md"
    path.write_text(content + "\n", encoding="utf-8")
    return path


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
python runtime_lane/tools/runtime_session.py assign --session-id <id> --task-source <path> --label "<label>" --type <task_source_type> [--allow-duplicate]
python runtime_lane/tools/runtime_session.py assignment-list --root runtime_lane
python runtime_lane/tools/runtime_session.py assignment-status --assignment-id <id>
python runtime_lane/tools/runtime_session.py update-assignment --assignment-id <id> --status <status> --note "<note>"
python runtime_lane/tools/runtime_session.py workload --root runtime_lane [--write-report]
python runtime_lane/tools/runtime_session.py unassigned --root runtime_lane

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

    assign = sub.add_parser("assign")
    assign.add_argument("--root", default=str(DEFAULT_ROOT))
    assign.add_argument("--session-id", required=True)
    assign.add_argument("--task-source", required=True)
    assign.add_argument("--label", required=True)
    assign.add_argument("--type", required=True)
    assign.add_argument("--allow-duplicate", action="store_true")

    assignment_list = sub.add_parser("assignment-list")
    assignment_list.add_argument("--root", default=str(DEFAULT_ROOT))

    assignment_status = sub.add_parser("assignment-status")
    assignment_status.add_argument("--root", default=str(DEFAULT_ROOT))
    assignment_status.add_argument("--assignment-id", required=True)

    update_assignment = sub.add_parser("update-assignment")
    update_assignment.add_argument("--root", default=str(DEFAULT_ROOT))
    update_assignment.add_argument("--assignment-id", required=True)
    update_assignment.add_argument("--status", required=True)
    update_assignment.add_argument("--note", default="")

    workload = sub.add_parser("workload")
    workload.add_argument("--root", default=str(DEFAULT_ROOT))
    workload.add_argument("--write-report", action="store_true")

    unassigned = sub.add_parser("unassigned")
    unassigned.add_argument("--root", default=str(DEFAULT_ROOT))

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
        if args.command == "assign":
            path = create_assignment(
                root,
                session_id=args.session_id,
                task_source=args.task_source,
                label=args.label,
                task_source_type=args.type,
                allow_duplicate=args.allow_duplicate,
            )
            print(f"Registered runtime assignment: {path}")
            return 0
        if args.command == "assignment-list":
            print(render_assignment_list(root))
            return 0
        if args.command == "assignment-status":
            print(render_assignment_status(root, args.assignment_id))
            return 0
        if args.command == "update-assignment":
            path = update_assignment(root, assignment_id=args.assignment_id, status=args.status, note=args.note)
            print(f"Updated runtime assignment: {path}")
            return 0
        if args.command == "workload":
            content = render_workload(root)
            print(content)
            if args.write_report:
                path = write_workload_report(root, content)
                print(f"Workload report written: {path}")
            return 0
        if args.command == "unassigned":
            print(render_unassigned(root))
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
