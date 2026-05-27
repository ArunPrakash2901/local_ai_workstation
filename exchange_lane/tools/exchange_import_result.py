#!/usr/bin/env python3
"""Exchange Lane result capture importer.

Imports a fake or future real capture manifest into an untrusted result packet.
It never applies output, executes commands, or updates app/source repositories.
"""

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

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from workstation_ids import check_path_length, make_artifact_id  # noqa: E402

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
REQUIRED_CAPTURE_FILES = (
    "raw_output_path",
    "parsed_result_path",
    "validation_path",
    "operator_report_path",
)


class ImportResultError(Exception):
    """Operator-facing result import error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require_id(value: str, label: str) -> str:
    if not value or not ID_RE.fullmatch(value):
        raise ImportResultError(f"{label} must use letters, numbers, '.', '_' or '-' and cannot be empty")
    return value


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ImportResultError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ImportResultError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ImportResultError(f"JSON root must be an object: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    length_check = check_path_length(path)
    if length_check["status"] == "fail":
        raise ImportResultError(f"refusing to write overlong path: {length_check['message']} -> {path}")
    if length_check["status"] == "warn":
        print(f"warning: {length_check['message']} -> {path}", file=sys.stderr)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def result_packet_path(root: Path, result_id: str) -> Path:
    return root / "result_packets" / f"{require_id(result_id, 'result_id')}.json"


def build_result_id(capture_id: str, packet_id: str) -> str:
    return require_id(
        make_artifact_id("res", [capture_id, packet_id], max_len=64),
        "result_id",
    )


def iter_result_packets(root: Path) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for path in sorted((root / "result_packets").glob("*.json")):
        data = load_json(path)
        data["_path"] = str(path)
        packets.append(data)
    return packets


def validate_capture_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    for field in (
        "capture_id",
        "packet_id",
        "dispatch_plan_id",
        "source_dispatch_plan",
        "source_packet",
        "target_adapter",
        "fake_execution",
        "real_cli_execution",
        "import_status",
    ):
        if field not in manifest:
            raise ImportResultError(f"capture manifest missing field: {field}")
    for field in REQUIRED_CAPTURE_FILES:
        path_text = str(manifest.get(field, ""))
        if not path_text:
            raise ImportResultError(f"capture manifest missing field: {field}")
        if not Path(path_text).is_file():
            raise ImportResultError(f"capture artifact missing: {path_text}")
    return manifest


def import_capture(root: Path, capture_manifest: Path) -> Path:
    root = root.resolve()
    capture_manifest = capture_manifest.resolve()
    manifest = validate_capture_manifest(capture_manifest)
    capture_id = require_id(str(manifest.get("capture_id", "")), "capture_id")
    packet_id = require_id(str(manifest.get("packet_id", "")), "packet_id")
    dispatch_plan_id = require_id(str(manifest.get("dispatch_plan_id", "")), "dispatch_plan_id")
    if manifest.get("import_status") == "IMPORTED":
        raise ImportResultError("capture manifest is already IMPORTED")
    for packet in iter_result_packets(root):
        if packet.get("capture_id") == capture_id:
            raise ImportResultError(f"capture already imported by result packet: {packet.get('result_id')}")

    parsed_result = load_json(Path(str(manifest["parsed_result_path"])))
    result_id = build_result_id(capture_id, packet_id)
    out = result_packet_path(root, result_id)
    if out.exists():
        raise ImportResultError(f"result packet already exists: {out}")

    result_packet = {
        "result_id": result_id,
        "capture_id": capture_id,
        "source_packet_id": packet_id,
        "source_dispatch_plan_id": dispatch_plan_id,
        "source_capture_manifest": str(capture_manifest),
        "source_packet": str(manifest.get("source_packet", "")),
        "source_dispatch_plan": str(manifest.get("source_dispatch_plan", "")),
        "source_session_id": "",
        "source_assignment_id": "",
        "adapter_id": str(manifest.get("target_adapter", "")),
        "result_status": "IMPORTED_PENDING_REVIEW",
        "summary": str(parsed_result.get("result_summary", "")),
        "files_created": parsed_result.get("files_created", []),
        "files_modified": parsed_result.get("files_modified", []),
        "commands_run": parsed_result.get("commands_run", []),
        "tests_run": parsed_result.get("tests_run", []),
        "validation_run": str(parsed_result.get("validation_status", "UNKNOWN")),
        "output_artifacts": {
            "raw_output": str(manifest.get("raw_output_path", "")),
            "parsed_result": str(manifest.get("parsed_result_path", "")),
            "validation": str(manifest.get("validation_path", "")),
            "operator_report": str(manifest.get("operator_report_path", "")),
        },
        "errors": [],
        "warnings": [],
        "blockers": parsed_result.get("blockers", []),
        "trusted": False,
        "human_review_required": True,
        "fake_execution": bool(manifest.get("fake_execution")),
        "real_cli_execution": bool(manifest.get("real_cli_execution")),
        "execution_occurred": bool(manifest.get("execution_occurred")),
        "model_or_provider_called": bool(manifest.get("model_or_provider_called")),
        "terminal_started": bool(manifest.get("terminal_started")),
        "branch_created": bool(manifest.get("branch_created")),
        "commit_performed": bool(manifest.get("commit_performed")),
        "push_performed": bool(manifest.get("push_performed")),
        "merge_performed": bool(manifest.get("merge_performed")),
        "app_source_modified": bool(manifest.get("app_source_modified")),
        "imported_at": utc_now(),
        "operator_notes": [
            "Imported result remains untrusted pending automated validation and loop decision metadata.",
            "Import does not apply code changes and does not approve execution output.",
            "Operator escalation is required only if validation or loop decision metadata reports blockers, risk, or a final gate.",
        ],
        "generated_by": "exchange_import_result.py",
    }
    write_json(out, result_packet)
    manifest["import_status"] = "IMPORTED"
    manifest["imported_at"] = result_packet["imported_at"]
    manifest["imported_result_id"] = result_id
    manifest["imported_result_packet"] = str(out.resolve())
    write_json(capture_manifest, manifest)
    return out


def cmd_import_result(args: argparse.Namespace) -> int:
    if not args.confirm:
        raise ImportResultError("import-result requires --confirm")
    result_path = import_capture(Path(args.root), Path(args.capture_manifest))
    print(f"result packet imported: {result_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exchange result capture importer.")
    sub = parser.add_subparsers(dest="command")

    help_parser = sub.add_parser("help", help="Show command help.")
    help_parser.set_defaults(func=lambda _args: (print(parser.format_help()), 0)[1])

    import_result = sub.add_parser("import-result", help="Import a capture manifest as an untrusted result packet.")
    import_result.add_argument("--capture-manifest", required=True)
    import_result.add_argument("--root", default=str(DEFAULT_ROOT))
    import_result.add_argument("--confirm", action="store_true")
    import_result.set_defaults(func=cmd_import_result)
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
    except ImportResultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
