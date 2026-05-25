#!/usr/bin/env python3
"""Audit Runtime Session Lane metadata without executing runtimes."""

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

import runtime_session  # noqa: E402


REQUIRED_FOLDERS = ("contracts", "adapters", "sessions", "blockers", "reports", "tools", "examples")
REQUIRED_CONTRACTS = (
    "runtime_session_contract.md",
    "adapter_profile_contract.md",
    "blocker_contract.md",
)
REQUIRED_PROFILES = (
    "codex_cli_profile.json",
    "gemini_cli_profile.json",
    "ollama_local_profile.json",
    "powershell_manual_profile.json",
    "wsl_manual_profile.json",
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


def audit_runtime_lane(root: Path) -> AuditResult:
    result = AuditResult()
    for folder in REQUIRED_FOLDERS:
        if not (root / folder).is_dir():
            result.error(f"missing folder: {root / folder}")
    for contract in REQUIRED_CONTRACTS:
        if not (root / "contracts" / contract).is_file():
            result.error(f"missing contract: {contract}")
    for profile_name in REQUIRED_PROFILES:
        path = root / "adapters" / profile_name
        data = load_json(path, result) if path.exists() else None
        if data is None:
            if not path.exists():
                result.error(f"missing adapter profile: {profile_name}")
            continue
        if data.get("launch_mode") != "manual_terminal":
            result.error(f"{profile_name}: launch_mode must be manual_terminal")
        if data.get("adapter_id") in {"codex_cli", "gemini_cli"}:
            text = json.dumps(data).lower()
            if "api integration" in text or "api worker" in text:
                result.error(f"{profile_name}: must not claim API ownership")
            if "not_an_api_worker" not in text:
                result.error(f"{profile_name}: must explicitly forbid API-worker assumption")

    for path in sorted((root / "sessions").glob("*.json")):
        data = load_json(path, result)
        if data is None:
            continue
        status = data.get("status")
        if status not in runtime_session.SESSION_STATUSES:
            result.error(f"{path}: invalid session status {status!r}")
        if data.get("automated_terminal_control") is True:
            result.error(f"{path}: claims automated terminal control")
        for field in ("commit_allowed", "push_allowed", "merge_allowed", "runtime_lane_git_actions_performed"):
            if data.get(field) not in {False, None}:
                result.error(f"{path}: unsafe runtime lane field {field}={data.get(field)!r}")

    for path in sorted((root / "blockers").glob("*.json")):
        data = load_json(path, result)
        if data is None:
            continue
        blocker_type = data.get("blocker_type")
        if blocker_type not in runtime_session.BLOCKER_TYPES:
            result.error(f"{path}: invalid blocker type {blocker_type!r}")
        if not data.get("operator_action_required") and not data.get("suggested_safe_response"):
            result.error(f"{path}: blocker needs operator_action_required or suggested_safe_response")

    return result


def render_audit(result: AuditResult, root: Path) -> str:
    lines = [
        "Runtime Session Lane Audit",
        "==========================",
        f"root: {root}",
        "scope: metadata inspection only; no terminals, CLIs, models, branches, or git actions are executed.",
        "",
        f"Warnings: {len(result.warnings)}",
    ]
    lines.extend(f"- WARNING {warning}" for warning in result.warnings)
    lines.append(f"Errors: {len(result.errors)}")
    lines.extend(f"- ERROR {error}" for error in result.errors)
    lines.append("")
    lines.append("Result: PASS" if result.ok else "Result: FAIL")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit Runtime Session Lane metadata.")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    result = audit_runtime_lane(root)
    print(render_audit(result, root))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

