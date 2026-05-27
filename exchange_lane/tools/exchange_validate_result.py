#!/usr/bin/env python3
"""Exchange Lane automated result validator.

This tool reads imported Exchange result metadata and writes validation records.
It never applies output, dispatches packets, runs models, starts terminals, or
performs branch or repository actions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from workstation_ids import check_path_length, make_artifact_id  # noqa: E402

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

ALLOWED_RESULT_STATUSES = {"IMPORTED_PENDING_REVIEW", "IMPORTED_PENDING_VALIDATION"}
VALIDATION_STATUSES = {
    "VALIDATION_PASSED",
    "VALIDATION_FAILED",
    "VALIDATION_WARNING",
    "VALIDATION_BLOCKED",
    "VALIDATION_INCOMPLETE",
}
PARSED_VALIDATION_STATUSES = {
    "FAKE_NOT_EXECUTED",
    "PASS",
    "PASSED",
    "FAIL",
    "FAILED",
    "BLOCKED",
    "WARNING",
    "UNKNOWN",
    "CLI_COMPLETED",
    "CLI_RETURNED_NONZERO",
    "CLI_TIMEOUT",
    "DISPATCH_BLOCKED",
}

FORBIDDEN_CAPTURE_FLAGS = (
    "branch_created",
    "commit_performed",
    "push_performed",
    "merge_performed",
    "app_source_modified",
)
FAKE_FALSE_FLAGS = (
    "real_cli_execution",
    "execution_occurred",
    "model_or_provider_called",
    "terminal_started",
    "branch_created",
    "commit_performed",
    "push_performed",
    "merge_performed",
    "app_source_modified",
)


class ValidateResultError(Exception):
    """Operator-facing validation error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require_id(value: str, label: str) -> str:
    if not value or not ID_RE.fullmatch(value):
        raise ValidateResultError(f"{label} must use letters, numbers, '.', '_' or '-' and cannot be empty")
    return value


def safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._-") or "record"


def windows_mapped_path(path_text: str) -> Path | None:
    win_path = PureWindowsPath(path_text)
    if not win_path.drive:
        return None
    return Path("/mnt") / win_path.drive.rstrip(":").lower() / Path(*win_path.parts[1:])


def readable_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_file():
        return path
    mapped = windows_mapped_path(path_text)
    if mapped is not None and mapped.is_file():
        return mapped
    return path


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidateResultError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidateResultError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidateResultError(f"JSON root must be an object: {path}")
    return data


def try_load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        return load_json(path), None
    except ValidateResultError as exc:
        return None, str(exc)


def write_json(path: Path, data: dict[str, Any]) -> None:
    length_check = check_path_length(path)
    if length_check["status"] == "fail":
        raise ValidateResultError(f"refusing to write overlong path: {length_check['message']} -> {path}")
    if length_check["status"] == "warn":
        print(f"warning: {length_check['message']} -> {path}", file=sys.stderr)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def result_packet_path(root: Path, result_id: str) -> Path:
    return root / "result_packets" / f"{require_id(result_id, 'result_id')}.json"


def validation_path(root: Path, validation_id: str) -> Path:
    return root / "result_validations" / f"{require_id(validation_id, 'validation_id')}.json"


def build_validation_id(result_id: str, result_packet: dict[str, Any]) -> str:
    return require_id(
        make_artifact_id(
            "val",
            [
                result_id,
                str(result_packet.get("capture_id", "")),
                str(result_packet.get("source_capture_manifest", "")),
            ],
            timestamp=utc_now(),
            max_len=64,
        ),
        "validation_id",
    )


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"check": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def list_field(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def validate_result(root: Path, result_id: str) -> Path:
    root = root.resolve()
    result_id = require_id(result_id, "result_id")
    result_path = result_packet_path(root, result_id)
    result_packet = load_json(result_path)

    checks: list[dict[str, Any]] = []
    reasons: list[str] = []
    missing_artifacts: list[str] = []
    warnings: list[str] = []

    checks.append(check("result_packet_exists", True, str(result_path)))
    result_status = str(result_packet.get("result_status", ""))
    status_ok = result_status in ALLOWED_RESULT_STATUSES
    checks.append(check("result_status_supported", status_ok, result_status))
    if not status_ok:
        reasons.append(f"unsupported result_status: {result_status}")

    trusted_ok = result_packet.get("trusted") is False
    checks.append(check("trusted_false_before_validation", trusted_ok, str(result_packet.get("trusted"))))
    if not trusted_ok:
        reasons.append("result packet must remain untrusted before validation")

    capture_manifest_path = readable_path(str(result_packet.get("source_capture_manifest", "")))
    capture_manifest, capture_error = try_load_json(capture_manifest_path)
    capture_exists = capture_manifest is not None
    checks.append(check("capture_manifest_exists", capture_exists, str(capture_manifest_path)))
    if not capture_exists:
        missing_artifacts.append(str(capture_manifest_path))

    manifest = capture_manifest or {}
    output_artifacts = result_packet.get("output_artifacts", {})
    if not isinstance(output_artifacts, dict):
        output_artifacts = {}

    artifact_paths = {
        "parsed_result_path": str(manifest.get("parsed_result_path") or output_artifacts.get("parsed_result", "")),
        "raw_output_path": str(manifest.get("raw_output_path") or output_artifacts.get("raw_output", "")),
        "validation_source_path": str(manifest.get("validation_path") or output_artifacts.get("validation", "")),
        "operator_report_path": str(manifest.get("operator_report_path") or output_artifacts.get("operator_report", "")),
    }
    parsed_path = readable_path(artifact_paths["parsed_result_path"])
    raw_path = readable_path(artifact_paths["raw_output_path"])
    validation_source_path = readable_path(artifact_paths["validation_source_path"])
    operator_report_path = readable_path(artifact_paths["operator_report_path"])

    for name, path in (
        ("parsed_result_json_exists", parsed_path),
        ("raw_output_md_exists", raw_path),
        ("validation_md_exists", validation_source_path),
        ("operator_report_md_exists", operator_report_path),
    ):
        exists = path.is_file()
        checks.append(check(name, exists, str(path)))
        if not exists:
            missing_artifacts.append(str(path))

    parsed_result: dict[str, Any] = {}
    if parsed_path.is_file():
        parsed_loaded, parsed_error = try_load_json(parsed_path)
        if parsed_loaded is None:
            missing_artifacts.append(str(parsed_path))
            checks.append(check("parsed_result_json_valid", False, parsed_error or str(parsed_path)))
        else:
            parsed_result = parsed_loaded
            checks.append(check("parsed_result_json_valid", True, str(parsed_path)))

    fake_execution = bool(manifest.get("fake_execution") or result_packet.get("fake_execution"))
    safety_flags = {
        "fake_execution": fake_execution,
        "real_cli_execution": bool(manifest.get("real_cli_execution") or result_packet.get("real_cli_execution")),
        "execution_occurred": bool(manifest.get("execution_occurred") or result_packet.get("execution_occurred")),
        "model_or_provider_called": bool(manifest.get("model_or_provider_called") or result_packet.get("model_or_provider_called")),
        "terminal_started": bool(manifest.get("terminal_started") or result_packet.get("terminal_started")),
        "branch_created": bool(manifest.get("branch_created") or result_packet.get("branch_created")),
        "commit_performed": bool(manifest.get("commit_performed") or result_packet.get("commit_performed")),
        "push_performed": bool(manifest.get("push_performed") or result_packet.get("push_performed")),
        "merge_performed": bool(manifest.get("merge_performed") or result_packet.get("merge_performed")),
        "app_source_modified": bool(manifest.get("app_source_modified") or result_packet.get("app_source_modified")),
    }

    forbidden_flags = [flag for flag in FORBIDDEN_CAPTURE_FLAGS if safety_flags.get(flag) is True]
    if fake_execution:
        forbidden_flags.extend([flag for flag in FAKE_FALSE_FLAGS if safety_flags.get(flag) is True])
    forbidden_flags = sorted(set(forbidden_flags))
    flags_ok = not forbidden_flags
    checks.append(check("capture_safety_flags_conservative", flags_ok, ", ".join(forbidden_flags) or "all conservative"))
    if forbidden_flags:
        reasons.extend(f"forbidden safety flag true: {flag}" for flag in forbidden_flags)

    commands_run = list_field(parsed_result.get("commands_run"))
    files_created = list_field(parsed_result.get("files_created"))
    files_modified = list_field(parsed_result.get("files_modified"))
    tests_run = list_field(parsed_result.get("tests_run"))
    blockers = list_field(parsed_result.get("blockers") or result_packet.get("blockers"))

    command_ok = not (fake_execution and commands_run)
    file_change_ok = not (fake_execution and (files_created or files_modified))
    blocker_ok = not blockers
    parsed_trusted_ok = parsed_result.get("trusted") in {False, None}
    parsed_review_flag = parsed_result.get("human_review_required")
    parsed_validation_status = str(parsed_result.get("validation_status", "UNKNOWN"))
    parsed_status_ok = parsed_validation_status in PARSED_VALIDATION_STATUSES

    if not command_ok:
        reasons.append("fake dispatch result reported commands_run")
    if not file_change_ok:
        reasons.append("fake dispatch result reported file changes")
    if not blocker_ok:
        reasons.append("result surfaced blockers")
    if not parsed_trusted_ok:
        reasons.append("parsed result must not mark itself trusted")
    if parsed_review_flag is not True:
        warnings.append("parsed_result.human_review_required was not true; validation record keeps escalation explicit")
    if not parsed_status_ok:
        reasons.append(f"unknown parsed_result validation_status: {parsed_validation_status}")

    checks.append(check("no_branch_created", not safety_flags["branch_created"], str(safety_flags["branch_created"])))
    checks.append(check("no_commit_performed", not safety_flags["commit_performed"], str(safety_flags["commit_performed"])))
    checks.append(check("no_push_performed", not safety_flags["push_performed"], str(safety_flags["push_performed"])))
    checks.append(check("no_merge_performed", not safety_flags["merge_performed"], str(safety_flags["merge_performed"])))
    checks.append(check("no_app_source_modified", not safety_flags["app_source_modified"], str(safety_flags["app_source_modified"])))
    checks.append(check("fake_no_model_or_provider_called", not (fake_execution and safety_flags["model_or_provider_called"]), str(safety_flags["model_or_provider_called"])))
    checks.append(check("fake_no_terminal_started", not (fake_execution and safety_flags["terminal_started"]), str(safety_flags["terminal_started"])))
    checks.append(check("parsed_commands_allowed", command_ok, f"commands_run_count={len(commands_run)}"))
    checks.append(check("parsed_file_changes_allowed", file_change_ok, f"created={len(files_created)} modified={len(files_modified)}"))
    checks.append(check("blockers_empty", blocker_ok, f"blocker_count={len(blockers)}"))
    checks.append(check("parsed_validation_status_understood", parsed_status_ok, parsed_validation_status))

    if capture_error:
        reasons.append(capture_error)

    if missing_artifacts:
        validation_status = "VALIDATION_INCOMPLETE"
        recommended = "BLOCKED_VALIDATION_FAILED"
        human_escalation_required = True
    elif forbidden_flags or not command_ok or not file_change_ok or not parsed_trusted_ok:
        validation_status = "VALIDATION_FAILED"
        recommended = "BLOCKED_FORBIDDEN_ACTION"
        human_escalation_required = True
    elif not blocker_ok:
        validation_status = "VALIDATION_BLOCKED"
        recommended = "BLOCKED_NEEDS_OPERATOR"
        human_escalation_required = True
    elif reasons:
        validation_status = "VALIDATION_FAILED"
        recommended = "BLOCKED_VALIDATION_FAILED"
        human_escalation_required = True
    elif warnings:
        validation_status = "VALIDATION_WARNING"
        recommended = "COMPLETED_PENDING_DAILY_REVIEW"
        human_escalation_required = False
    else:
        validation_status = "VALIDATION_PASSED"
        recommended = "COMPLETED_PENDING_DAILY_REVIEW"
        human_escalation_required = False

    validation_id = build_validation_id(result_id, result_packet)
    record = {
        "validation_id": validation_id,
        "result_id": result_id,
        "result_packet_path": str(result_path.resolve()),
        "source_packet_id": str(result_packet.get("source_packet_id", "")),
        "dispatch_plan_id": str(result_packet.get("source_dispatch_plan_id", "")),
        "capture_manifest_path": str(capture_manifest_path),
        "parsed_result_path": str(parsed_path),
        "raw_output_path": str(raw_path),
        "validation_source_path": str(validation_source_path),
        "operator_report_path": str(operator_report_path),
        "created_at": utc_now(),
        "validation_status": validation_status,
        "validation_checks": checks,
        "safety_flags": safety_flags,
        "expected_outputs_check": {
            "status": "PASS" if tests_run is not None else "UNKNOWN",
            "tests_run_count": len(tests_run),
            "note": "MVP validates result metadata only; implementation correctness is not established.",
        },
        "forbidden_actions_check": {
            "status": "PASS" if not forbidden_flags else "FAIL",
            "forbidden_flags": forbidden_flags,
        },
        "file_change_check": {
            "status": "PASS" if file_change_ok else "FAIL",
            "files_created": files_created,
            "files_modified": files_modified,
        },
        "command_check": {
            "status": "PASS" if command_ok else "FAIL",
            "commands_run": commands_run,
        },
        "test_result_check": {
            "status": "INFO",
            "tests_run": tests_run,
            "note": "No tests were executed by fake dispatch.",
        },
        "blocker_check": {
            "status": "PASS" if blocker_ok else "BLOCKED",
            "blockers": blockers,
        },
        "retry_eligibility": {
            "retry_count": 0,
            "retry_budget": 1,
            "eligible": validation_status in {"VALIDATION_FAILED", "VALIDATION_BLOCKED"},
            "note": "MVP retry metadata only; no automatic redispatch in this slice.",
        },
        "human_escalation_required": human_escalation_required,
        "recommended_loop_decision": recommended,
        "reasons": reasons + warnings,
        "generated_by": "exchange_validate_result.py",
    }
    out = validation_path(root, validation_id)
    write_json(out, record)
    return out


def cmd_validate_result(args: argparse.Namespace) -> int:
    out = validate_result(Path(args.root), args.result_id)
    print(f"validation record written: {out}")
    return 0


def cmd_validation_status(args: argparse.Namespace) -> int:
    path = validation_path(Path(args.root), args.validation_id)
    data = load_json(path)
    print(json.dumps(data, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exchange result validation metadata writer.")
    sub = parser.add_subparsers(dest="command")

    help_parser = sub.add_parser("help", help="Show command help.")
    help_parser.set_defaults(func=lambda _args: (print(parser.format_help()), 0)[1])

    validate = sub.add_parser("validate-result", help="Validate an imported result packet.")
    validate.add_argument("--result-id", required=True)
    validate.add_argument("--root", default=str(DEFAULT_ROOT))
    validate.set_defaults(func=cmd_validate_result)

    status = sub.add_parser("validation-status", help="Show one validation record.")
    status.add_argument("--validation-id", required=True)
    status.add_argument("--root", default=str(DEFAULT_ROOT))
    status.set_defaults(func=cmd_validation_status)
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
    except ValidateResultError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
