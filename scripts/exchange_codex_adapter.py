#!/usr/bin/env python3
"""Guarded REVIEW_ONLY Codex CLI adapter dispatch for Exchange Lane."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from exchange_dispatch import _load_command_manifest, validate_exchange_dispatch_ready
from exchange_registry import EXCHANGE_PACKET_FILENAME, _safe_child

Executor = Callable[[str], tuple[int, str, str]]


REVIEW_ONLY_INSTRUCTION = """You are running inside Local AI Workstation Exchange Lane.
This is a REVIEW_ONLY adapter dispatch.
Non-negotiable rules:
- Do not modify files.
- Do not run shell commands.
- Do not apply patches.
- Do not execute allowed_commands.
- Do not call tools if avoidable.
- Return markdown text only.

Return output in this exact Exchange Result structure:
# Exchange Result

## Task ID
<exchange_id>

## Inputs Read
- ...

## Commands Run
- None

## Files Changed
- None

## Tests Run
- None

## Result
<review summary>

## Blocked Reason
None

## Needs Human Decision
None
"""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_executor(prompt_text: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["codex"],
        input=prompt_text,
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )
    return completed.returncode, completed.stdout or "", completed.stderr or ""


def build_codex_review_prompt(packet: dict[str, Any], exchange_dir: Path) -> str:
    prompt_path = _safe_child(exchange_dir, exchange_dir / "prompt.md")
    prompt_body = ""
    if prompt_path.is_file():
        prompt_body = prompt_path.read_text(encoding="utf-8")

    lines = [
        "# Exchange Codex REVIEW_ONLY Dispatch",
        "",
        f"exchange_id: {packet.get('exchange_id', '')}",
        f"target: {packet.get('target', '')}",
        f"task_type: {packet.get('task_type', '')}",
        f"task_summary: {packet.get('task_summary', '')}",
        f"safety_mode: {packet.get('safety_mode', '')}",
        "",
        "## Safety Instruction",
        "",
        REVIEW_ONLY_INSTRUCTION.strip(),
        "",
        "## Exchange Prompt",
        "",
        prompt_body.strip() if prompt_body.strip() else "(empty prompt.md)",
    ]
    return "\n".join(lines) + "\n"


def _has_existing_adapter_output(exchange_dir: Path) -> bool:
    base = _safe_child(exchange_dir, exchange_dir / "adapter_runs" / "codex_cli")
    if not base.exists():
        return False
    for run_dir in base.iterdir():
        if run_dir.is_dir() and (run_dir / "stdout.md").exists():
            return True
    return False


def validate_codex_dispatch_preconditions(
    packet: dict[str, Any],
    exchange_dir: Path,
    requested_target: str,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []

    packet_target = str(packet.get("target", "")).strip()
    if packet_target != "codex_cli":
        blockers.append(f"packet target must be codex_cli, got: {packet_target}")

    if requested_target != "codex_cli":
        blockers.append(f"requested target must be codex_cli, got: {requested_target}")

    safety_mode = str(packet.get("safety_mode", "")).strip()
    if safety_mode != "REVIEW_ONLY":
        blockers.append(f"packet safety_mode must be REVIEW_ONLY, got: {safety_mode}")

    status = str(packet.get("status", "")).strip()
    if status != "READY":
        blockers.append(f"packet status must be READY, got: {status}")

    allowed = packet.get("allowed_commands", [])
    if not isinstance(allowed, list):
        blockers.append("allowed_commands must be a list")
    elif allowed:
        blockers.append("allowed_commands must be empty for REVIEW_ONLY codex dispatch")

    if str(packet.get("status", "")).strip() == "COMPLETED":
        blockers.append("exchange status COMPLETED is blocked for dispatch confirm")

    root_raw_output = _safe_child(exchange_dir, exchange_dir / "raw_output.md")
    if root_raw_output.exists():
        blockers.append("exchange already has imported raw_output.md; dispatch confirm is blocked")

    if _has_existing_adapter_output(exchange_dir):
        blockers.append("existing codex adapter stdout artifact found; duplicate dispatch blocked")

    dispatch_validation = validate_exchange_dispatch_ready(packet, manifest)
    if dispatch_validation.get("result") == "FAIL":
        blockers.append("dispatch dry-run validation has FAIL blockers")
        blockers.extend(dispatch_validation.get("blockers", []))
    else:
        warnings.extend(dispatch_validation.get("warnings", []))

    return {
        "ok": not blockers,
        "blockers": blockers,
        "warnings": warnings,
    }


def codex_adapter_run_dir(exchange_dir: Path, run_id: str) -> Path:
    run_dir = _safe_child(exchange_dir, exchange_dir / "adapter_runs" / "codex_cli" / run_id)
    return run_dir


def _load_packet(exchange_dir: Path) -> tuple[Path, dict[str, Any]]:
    packet_path = _safe_child(exchange_dir, exchange_dir / EXCHANGE_PACKET_FILENAME)
    if not packet_path.is_file():
        raise FileNotFoundError(f"exchange packet not found: {packet_path}")
    raw = packet_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("exchange packet must be a mapping")
    return packet_path, data


def run_codex_adapter(
    root: str | Path,
    exchange_id: str,
    requested_target: str,
    executor: Executor | None = None,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    exchange_dir = _safe_child(root_path / "exchange", (root_path / "exchange" / exchange_id))
    packet_path, packet = _load_packet(exchange_dir)
    manifest = _load_command_manifest(root_path)

    pre = validate_codex_dispatch_preconditions(packet, exchange_dir, requested_target, manifest)
    if not pre["ok"]:
        return {
            "ok": False,
            "blockers": pre["blockers"],
            "warnings": pre["warnings"],
            "exchange_id": exchange_id,
        }

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-codex-review"
    run_dir = codex_adapter_run_dir(exchange_dir, run_id)
    run_dir.mkdir(parents=True, exist_ok=False)

    prompt_text = build_codex_review_prompt(packet, exchange_dir)
    prompt_path = _safe_child(run_dir, run_dir / "adapter_prompt.md")
    stdout_path = _safe_child(run_dir, run_dir / "stdout.md")
    stderr_path = _safe_child(run_dir, run_dir / "stderr.md")
    run_yaml_path = _safe_child(run_dir, run_dir / "adapter_run.yaml")

    prompt_path.write_text(prompt_text, encoding="utf-8", newline="\n")

    exec_fn = executor or _default_executor
    return_code, stdout_text, stderr_text = exec_fn(prompt_text)

    stdout_path.write_text(stdout_text, encoding="utf-8", newline="\n")
    stderr_path.write_text(stderr_text, encoding="utf-8", newline="\n")

    run_status = "SUCCESS" if return_code == 0 else "FAILED"
    run_payload = {
        "run_id": run_id,
        "target": "codex_cli",
        "dispatch_mode": "REVIEW_ONLY",
        "started_at": _utc_now_iso(),
        "return_code": return_code,
        "run_status": run_status,
        "stdout_path": str(stdout_path.relative_to(exchange_dir)).replace("\\", "/"),
        "stderr_path": str(stderr_path.relative_to(exchange_dir)).replace("\\", "/"),
        "prompt_path": str(prompt_path.relative_to(exchange_dir)).replace("\\", "/"),
        "notes": "No command execution from model output. No automatic import.",
    }
    run_yaml_path.write_text(json.dumps(run_payload, indent=2) + "\n", encoding="utf-8", newline="\n")

    updated_packet = dict(packet)
    runs = updated_packet.get("adapter_runs")
    if not isinstance(runs, list):
        runs = []
    run_entry = {
        "run_id": run_id,
        "target": "codex_cli",
        "path": str(run_dir.relative_to(exchange_dir)).replace("\\", "/"),
        "return_code": return_code,
        "status": run_status,
        "created_at": _utc_now_iso(),
    }
    runs.append(run_entry)
    updated_packet["adapter_runs"] = runs
    updated_packet["last_adapter_run"] = run_entry
    updated_packet["status"] = "ACTIVE" if return_code == 0 else "BLOCKED"
    updated_packet["updated_at"] = _utc_now_iso()
    updated_packet["last_action"] = "ws exchange-dispatch --confirm codex_cli"

    packet_path.write_text(json.dumps(updated_packet, indent=2) + "\n", encoding="utf-8", newline="\n")

    return {
        "ok": True,
        "exchange_id": exchange_id,
        "run_id": run_id,
        "return_code": return_code,
        "run_status": run_status,
        "exchange_status": updated_packet["status"],
        "warnings": pre["warnings"],
        "files_written": [
            str(prompt_path),
            str(stdout_path),
            str(stderr_path),
            str(run_yaml_path),
            str(packet_path),
        ],
    }


def render_codex_dispatch_result(result: dict[str, Any]) -> str:
    if not result.get("ok"):
        lines = [
            "CODEx DISPATCH BLOCKED",
            "====================",
            "",
            "Blockers:",
        ]
        for item in result.get("blockers", []):
            lines.append(f"- {item}")
        warnings = result.get("warnings", [])
        if warnings:
            lines.extend(["", "Warnings:"])
            lines.extend([f"- {item}" for item in warnings])
        lines.append("")
        lines.append("No files were written.")
        return "\n".join(lines)

    lines = [
        "CODEX DISPATCH EXECUTED",
        "=======================",
        "",
        f"exchange_id: {result.get('exchange_id', '')}",
        f"run_id: {result.get('run_id', '')}",
        f"return_code: {result.get('return_code', '')}",
        f"run_status: {result.get('run_status', '')}",
        f"exchange_status: {result.get('exchange_status', '')}",
        "",
        "Files written:",
    ]
    for path in result.get("files_written", []):
        lines.append(f"- {path}")

    warnings = result.get("warnings", [])
    if warnings:
        lines.extend(["", "Warnings:"])
        lines.extend([f"- {item}" for item in warnings])

    lines.extend([
        "",
        "Safety:",
        "- REVIEW_ONLY codex dispatch.",
        "- No automatic result import.",
        "- No command execution from adapter output.",
        "- No product artifact writes.",
    ])
    return "\n".join(lines)
