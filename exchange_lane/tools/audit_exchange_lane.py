#!/usr/bin/env python3
"""Audit Exchange Lane metadata without execution."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

import exchange_packet  # noqa: E402


RESULT_STATUSES = {
    "DRAFT",
    "IMPORTED_PENDING_REVIEW",
    "ACCEPTED_BY_HUMAN",
    "REJECTED_BY_HUMAN",
    "BLOCKED",
    "ARCHIVED",
}

KNOWN_ADAPTERS = {
    "codex_cli",
    "gemini_cli",
    "ollama_local",
    "powershell_manual",
    "wsl_manual",
    "manual",
    "unknown",
}

REQUIRED_FOLDERS = (
    "contracts",
    "packets",
    "result_packets",
    "routing",
    "manifests",
    "reports",
    "tools",
    "examples",
)

REQUIRED_CONTRACTS = (
    "exchange_packet_contract.md",
    "result_packet_contract.md",
    "routing_policy.md",
    "adapter_routing_contract.md",
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


def audit_exchange_lane(root: Path) -> AuditResult:
    result = AuditResult()
    for folder in REQUIRED_FOLDERS:
        if not (root / folder).is_dir():
            result.error(f"missing folder: {root / folder}")
    for contract in REQUIRED_CONTRACTS:
        if not (root / "contracts" / contract).is_file():
            result.error(f"missing contract: {contract}")

    for path in sorted((root / "packets").glob("*.json")):
        data = load_json(path, result)
        if data is None:
            continue
        status = data.get("packet_status")
        if status not in exchange_packet.PACKET_STATUSES:
            result.error(f"{path}: invalid packet_status {status!r}")
        source_path = str(data.get("source_artifact_path", ""))
        if status in {"DRAFT", "READY_FOR_REVIEW", "APPROVED_FOR_DISPATCH_PLANNING", "DISPATCH_PLANNED", "BLOCKED"}:
            if not source_path:
                result.error(f"{path}: missing source_artifact_path")
            elif not Path(source_path).exists():
                result.error(f"{path}: source_artifact_path missing: {source_path}")
        if source_path and Path(source_path).is_file():
            checksum = str(data.get("source_artifact_checksum", ""))
            if len(checksum) != 64:
                result.error(f"{path}: missing/invalid source_artifact_checksum for file artifact")
        target_adapter = str(data.get("target_adapter", ""))
        if target_adapter not in KNOWN_ADAPTERS and not (Path(__file__).resolve().parents[2] / "runtime_lane" / "adapters" / f"{target_adapter}_profile.json").exists():
            result.warn(f"{path}: unknown target_adapter {target_adapter!r}")
        for field in ("execution_allowed", "commit_allowed", "push_allowed", "merge_allowed"):
            if data.get(field) not in {False, None}:
                result.error(f"{path}: unsafe field {field}={data.get(field)!r}")
        for field in ("execution_occurred", "branch_created", "commit_performed", "push_performed", "merge_performed"):
            if data.get(field) not in {False, None}:
                result.error(f"{path}: packet claims forbidden action {field}={data.get(field)!r}")
        if status == "DISPATCH_PLANNED":
            if not data.get("dispatch_plan"):
                result.error(f"{path}: DISPATCH_PLANNED requires dispatch_plan in future schema")

    for path in sorted((root / "result_packets").glob("*.json")):
        data = load_json(path, result)
        if data is None:
            continue
        status = data.get("result_status")
        if status not in RESULT_STATUSES:
            result.error(f"{path}: invalid result_status {status!r}")
        for field in ("execution_occurred", "branch_created", "commit_performed", "push_performed", "merge_performed"):
            value = data.get(field)
            if value not in {False, True, None}:
                result.error(f"{path}: invalid boolean field {field}={value!r}")
    return result


def render_audit(result: AuditResult, root: Path) -> str:
    lines = [
        "Exchange Lane Audit",
        "===================",
        f"root: {root}",
        "scope: metadata inspection only; no dispatch/execution/model/terminal actions.",
        "",
        f"Warnings: {len(result.warnings)}",
    ]
    lines.extend(f"- WARNING {w}" for w in result.warnings)
    lines.append(f"Errors: {len(result.errors)}")
    lines.extend(f"- ERROR {e}" for e in result.errors)
    lines.append("")
    lines.append("Result: PASS" if result.ok else "Result: FAIL")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit Exchange Lane metadata.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    result = audit_exchange_lane(root)
    print(render_audit(result, root))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
