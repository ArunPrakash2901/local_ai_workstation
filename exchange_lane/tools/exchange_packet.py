#!/usr/bin/env python3
"""Exchange Lane packet registry (non-executing)."""

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

SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = SCRIPT_PATH.parents[2]

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

PACKET_STATUSES = {
    "DRAFT",
    "READY_FOR_REVIEW",
    "APPROVED_FOR_DISPATCH_PLANNING",
    "DISPATCH_PLANNED",
    "BLOCKED",
    "REJECTED",
    "RESULT_IMPORTED",
    "CLOSED",
}

TASK_TYPES = {
    "code_review",
    "implementation_planning",
    "product_review",
    "design_review",
    "validation_review",
    "refactor_planning",
    "documentation_update",
    "local_model_summary",
    "manual_operator_task",
    "other",
}


class ExchangePacketError(Exception):
    """Operator-facing exchange packet error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require_id(value: str, label: str) -> str:
    if not value or not ID_RE.fullmatch(value):
        raise ExchangePacketError(f"{label} must use letters, numbers, '.', '_' or '-' and cannot be empty")
    return value


def ensure_dirs(root: Path) -> None:
    for name in ("packets", "result_packets", "routing", "manifests", "reports", "contracts", "tools", "examples"):
        (root / name).mkdir(parents=True, exist_ok=True)


def packet_path(root: Path, packet_id: str) -> Path:
    return root / "packets" / f"{require_id(packet_id, 'packet_id')}.json"


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ExchangePacketError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ExchangePacketError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ExchangePacketError(f"JSON root must be an object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def target_adapter_known(adapter_id: str) -> bool:
    profile = REPO_ROOT / "runtime_lane" / "adapters" / f"{adapter_id}_profile.json"
    return profile.exists()


def rel_to_repo(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except Exception:
        return str(path.resolve())


def create_packet(
    root: Path,
    *,
    source_artifact: str,
    source_lane: str,
    target_adapter: str,
    task_type: str,
    objective: str,
) -> Path:
    ensure_dirs(root)
    if task_type not in TASK_TYPES:
        raise ExchangePacketError(f"invalid task_type: {task_type}")
    if not objective.strip():
        raise ExchangePacketError("objective cannot be empty")
    source_path = Path(source_artifact).expanduser().resolve()
    if not source_path.exists():
        raise ExchangePacketError(f"source artifact does not exist: {source_artifact}")
    checksum = sha256_file(source_path) if source_path.is_file() else ""
    now = utc_now()
    base = source_path.stem[:48] or "artifact"
    packet_id = require_id(
        f"{source_lane}__{target_adapter}__{task_type}__{base}__{now.replace(':', '').replace('-', '').replace('Z', 'z')}",
        "packet_id",
    )
    packet = {
        "packet_id": packet_id,
        "packet_version": "v0.1",
        "created_at": now,
        "created_by": "exchange_packet.py",
        "source_lane": source_lane,
        "source_artifact_type": source_path.suffix.lower().lstrip(".") or "artifact",
        "source_artifact_path": str(source_path),
        "source_artifact_checksum": checksum,
        "target_adapter": target_adapter,
        "target_session_id": "",
        "target_assignment_id": "",
        "task_type": task_type,
        "objective": objective,
        "input_artifacts": [str(source_path)],
        "expected_outputs": [],
        "allowed_write_roots": [],
        "forbidden_paths": ["src/", "app/", "components/", "package.json"],
        "forbidden_actions": [
            "run_models",
            "dispatch_packets",
            "execute_prompts",
            "create_branches",
            "commit",
            "push",
            "merge",
        ],
        "human_approval_required": True,
        "execution_allowed": False,
        "commit_allowed": False,
        "push_allowed": False,
        "merge_allowed": False,
        "safety_class": "LOCAL_REPORT_WRITE",
        "packet_status": "DRAFT",
        "blocker_ids": [],
        "quota_notes": "",
        "operator_notes": [
            f"target_adapter_known={target_adapter_known(target_adapter)}",
        ],
        "lineage": {
            "parent_packet_ids": [],
            "derived_from": rel_to_repo(source_path),
        },
        "execution_occurred": False,
        "branch_created": False,
        "commit_performed": False,
        "push_performed": False,
        "merge_performed": False,
    }
    out = packet_path(root, packet_id)
    write_json(out, packet)
    return out


def list_packets(root: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted((root / "packets").glob("*.json")):
        data = load_json(path)
        data["_path"] = str(path)
        items.append(data)
    return items


def get_packet(root: Path, packet_id: str) -> dict[str, Any]:
    return load_json(packet_path(root, packet_id))


def update_packet_status(root: Path, packet_id: str, status: str, note: str) -> Path:
    data = get_packet(root, packet_id)
    if status not in PACKET_STATUSES:
        raise ExchangePacketError(f"invalid packet status: {status}")
    data["packet_status"] = status
    notes = data.setdefault("operator_notes", [])
    if not isinstance(notes, list):
        notes = []
        data["operator_notes"] = notes
    if note.strip():
        notes.append({"timestamp": utc_now(), "note": note})
    data["updated_at"] = utc_now()
    out = packet_path(root, packet_id)
    write_json(out, data)
    return out


def cmd_create(args: argparse.Namespace) -> int:
    out = create_packet(
        Path(args.root).resolve(),
        source_artifact=args.source_artifact,
        source_lane=args.source_lane,
        target_adapter=args.target_adapter,
        task_type=args.task_type,
        objective=args.objective,
    )
    print(f"created packet: {out}")
    return 0


def cmd_packet_list(args: argparse.Namespace) -> int:
    packets = list_packets(Path(args.root).resolve())
    if not packets:
        print("no exchange packets")
        return 0
    print("exchange packets:")
    for item in packets:
        print(
            f"- {item.get('packet_id', '')} | source_lane={item.get('source_lane', '')} | "
            f"source_artifact={item.get('source_artifact_path', '')} | target_adapter={item.get('target_adapter', '')} | "
            f"task_type={item.get('task_type', '')} | status={item.get('packet_status', '')}"
        )
    return 0


def cmd_packet_status(args: argparse.Namespace) -> int:
    packet = get_packet(Path(args.root).resolve(), args.packet_id)
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


def cmd_mark_ready(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    packet = get_packet(root, args.packet_id)
    if packet.get("packet_status") != "DRAFT":
        raise ExchangePacketError("mark-ready only supports DRAFT -> READY_FOR_REVIEW")
    out = update_packet_status(root, args.packet_id, "READY_FOR_REVIEW", args.note or "")
    print(f"updated packet: {out}")
    return 0


def cmd_block(args: argparse.Namespace) -> int:
    out = update_packet_status(Path(args.root).resolve(), args.packet_id, "BLOCKED", args.reason or "")
    print(f"blocked packet: {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exchange Lane packet registry (non-executing).")
    sub = parser.add_subparsers(dest="command")

    help_parser = sub.add_parser("help", help="Show command help.")
    help_parser.set_defaults(func=lambda _args: (print(parser.format_help()), 0)[1])

    create = sub.add_parser("create", help="Create exchange packet metadata.")
    create.add_argument("--root", default=str(DEFAULT_ROOT))
    create.add_argument("--source-artifact", required=True)
    create.add_argument("--source-lane", required=True)
    create.add_argument("--target-adapter", required=True)
    create.add_argument("--task-type", required=True, choices=sorted(TASK_TYPES))
    create.add_argument("--objective", required=True)
    create.set_defaults(func=cmd_create)

    list_cmd = sub.add_parser("packet-list", help="List exchange packets.")
    list_cmd.add_argument("--root", default=str(DEFAULT_ROOT))
    list_cmd.set_defaults(func=cmd_packet_list)

    status_cmd = sub.add_parser("packet-status", help="Show one packet.")
    status_cmd.add_argument("--root", default=str(DEFAULT_ROOT))
    status_cmd.add_argument("--packet-id", required=True)
    status_cmd.set_defaults(func=cmd_packet_status)

    ready = sub.add_parser("mark-ready", help="Move packet from DRAFT to READY_FOR_REVIEW.")
    ready.add_argument("--root", default=str(DEFAULT_ROOT))
    ready.add_argument("--packet-id", required=True)
    ready.add_argument("--note", default="")
    ready.set_defaults(func=cmd_mark_ready)

    block = sub.add_parser("block", help="Block a packet.")
    block.add_argument("--root", default=str(DEFAULT_ROOT))
    block.add_argument("--packet-id", required=True)
    block.add_argument("--reason", required=True)
    block.set_defaults(func=cmd_block)
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
    except ExchangePacketError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
