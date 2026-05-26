#!/usr/bin/env python3
"""Audit Execution Lane MVP Slice 1 artifacts without execution."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from pathlib import PureWindowsPath
from typing import Any


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_ROOT = SCRIPT_PATH.parents[1]

REQUIRED_FOLDERS = (
    "contracts",
    "runs",
    "run_reports",
    "worker_task_packets",
    "handoff_previews",
    "manifests",
    "tools",
)

REQUIRED_CONTRACTS = (
    "execution_run_contract.md",
    "worker_task_packet_contract.md",
    "execution_handoff_preview_contract.md",
    "execution_queue_contract.md",
)

ALLOWED_RUN_STATUS = {
    "PLANNED_DRY_RUN",
    "PREPARED_NOT_EXECUTED",
    "BLOCKED_QUEUE_NOT_READY",
    "BLOCKED_INVALID_QUEUE",
    "BLOCKED_MISSING_ARTIFACTS",
    "BLOCKED_PRODUCT_DEV_VALIDATION",
    "CLOSED",
}

FORBIDDEN_TEXT = (
    "executed prompt",
    "dispatched",
    "started terminal",
    "ran codex",
    "ran gemini",
    "ran ollama",
    "created branch",
    "committed",
    "pushed",
    "merged",
    "browser automation",
)


class AuditResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def load_json(path: Path, result: AuditResult) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        result.error(f"invalid JSON: {path}: {exc}")
        return None
    if not isinstance(data, dict):
        result.error(f"JSON root must be object: {path}")
        return None
    return data


def strings_from(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(strings_from(item))
        return out
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(strings_from(item))
        return out
    return []


def validate_false_flags(data: dict[str, Any], path: Path, result: AuditResult) -> None:
    for key in (
        "execution_allowed",
        "branch_creation_allowed",
        "commit_allowed",
        "push_allowed",
        "merge_allowed",
    ):
        if data.get(key) is not False:
            result.error(f"{path}: {key} must be false")
    for key in (
        "execution_occurred",
        "branch_created",
        "commit_performed",
        "push_performed",
        "merge_performed",
        "model_invoked",
        "provider_called",
    ):
        if key in data and data.get(key) not in {False, None}:
            result.error(f"{path}: forbidden action flag {key} must be false")


def existing_path(raw_path: str) -> Path | None:
    path = Path(raw_path)
    if path.is_file():
        return path
    win_path = PureWindowsPath(raw_path)
    if win_path.drive:
        drive = win_path.drive.rstrip(":").lower()
        mapped = Path("/mnt") / drive / Path(*win_path.parts[1:])
        if mapped.is_file():
            return mapped
    return None


def audit_execution_lane(root: Path) -> AuditResult:
    result = AuditResult()
    for folder in REQUIRED_FOLDERS:
        if not (root / folder).is_dir():
            result.error(f"missing folder: {root / folder}")
    for contract in REQUIRED_CONTRACTS:
        if not (root / "contracts" / contract).is_file():
            result.error(f"missing contract: {root / 'contracts' / contract}")

    for path in sorted((root / "runs").glob("*.json")):
        run = load_json(path, result)
        if run is None:
            continue
        status = str(run.get("run_status", ""))
        if status not in ALLOWED_RUN_STATUS:
            result.error(f"{path}: invalid run_status {status}")
        validate_false_flags(run, path, result)
        if not str(run.get("source_queue_manifest", "")):
            result.error(f"{path}: missing source_queue_manifest")
        else:
            source_queue = str(run.get("source_queue_manifest", ""))
            if existing_path(source_queue) is None:
                result.error(f"{path}: source_queue_manifest missing on disk: {source_queue}")
        packet_list = run.get("worker_task_packets", [])
        if not isinstance(packet_list, list):
            result.error(f"{path}: worker_task_packets must be list")
        else:
            for packet_path in packet_list:
                packet = str(packet_path)
                if existing_path(packet) is None:
                    result.error(f"{path}: referenced worker task packet missing: {packet}")

        linked_manifest = str(run.get("linked_product_development_manifest", ""))
        if linked_manifest:
            if existing_path(linked_manifest) is None:
                result.error(f"{path}: linked product development manifest missing: {linked_manifest}")

        text_blob = " | ".join(s.casefold() for s in strings_from(run))
        for forbidden in FORBIDDEN_TEXT:
            if forbidden in text_blob:
                result.error(f"{path}: forbidden execution claim detected: {forbidden}")

    for path in sorted((root / "worker_task_packets").glob("*.json")):
        packet = load_json(path, result)
        if packet is None:
            continue
        for field in (
            "task_packet_id",
            "run_id",
            "phase_id",
            "source_worker_prompt",
            "source_handoff_bundle",
            "source_branch_plan",
        ):
            if not str(packet.get(field, "")):
                result.error(f"{path}: missing field {field}")
        for key in ("execution_allowed", "commit_allowed", "push_allowed", "merge_allowed"):
            if packet.get(key) is not False:
                result.error(f"{path}: {key} must be false")
        if packet.get("human_approval_required") is not True:
            result.error(f"{path}: human_approval_required must be true")
        forbidden_actions = packet.get("forbidden_actions", [])
        if not isinstance(forbidden_actions, list) or not forbidden_actions:
            result.error(f"{path}: forbidden_actions must be a non-empty list")
        text_blob = " | ".join(s.casefold() for s in strings_from(packet))
        for forbidden in FORBIDDEN_TEXT:
            if forbidden in text_blob:
                result.error(f"{path}: forbidden execution claim detected: {forbidden}")

    for path in sorted((root / "handoff_previews").glob("*.json")):
        preview = load_json(path, result)
        if preview is None:
            continue
        if preview.get("execution_allowed") is not False:
            result.error(f"{path}: execution_allowed must be false")
        if preview.get("dispatch_allowed") is not False:
            result.error(f"{path}: dispatch_allowed must be false")
        note = str(preview.get("note", "")).casefold()
        if "preview only" not in note:
            result.error(f"{path}: note must include 'preview only'")
        text_blob = " | ".join(s.casefold() for s in strings_from(preview))
        for forbidden in FORBIDDEN_TEXT:
            if forbidden in text_blob:
                result.error(f"{path}: forbidden execution claim detected: {forbidden}")
    return result


def render_report(result: AuditResult, root: Path) -> str:
    lines = [
        "Execution Lane Audit",
        "====================",
        f"root: {root}",
        "scope: metadata inspection only; no execution/model/provider/dispatch actions.",
        "",
        f"Warnings: {len(result.warnings)}",
    ]
    lines.extend(f"- WARNING {item}" for item in result.warnings)
    lines.append(f"Errors: {len(result.errors)}")
    lines.extend(f"- ERROR {item}" for item in result.errors)
    lines.append("")
    lines.append("Result: PASS" if result.ok else "Result: FAIL")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit execution lane artifacts.")
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    result = audit_execution_lane(root)
    print(render_report(result, root))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
