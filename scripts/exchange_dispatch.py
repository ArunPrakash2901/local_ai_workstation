#!/usr/bin/env python3
"""Deterministic no-execution Exchange Lane dispatch preview helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from exchange_registry import (
    ALLOWED_SAFETY_MODES,
    ALLOWED_TARGETS,
    EXCHANGE_PACKET_FILENAME,
    _safe_child,
    exchange_dir,
    validate_exchange_packet,
)


ALLOWED_DISPATCH_STATUSES = {"READY", "DRAFT"}


def _load_json_or_yaml(path: Path) -> Any:
    raw = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore[import-not-found]
        except Exception as exc:
            raise ValueError(f"file is not JSON and PyYAML is unavailable: {path}: {exc}") from exc
        return yaml.safe_load(raw)


def _load_command_manifest(root: str | Path) -> dict[str, Any]:
    manifest_path = Path(root).resolve() / "registry" / "ws_command_safety.yaml"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"command safety manifest not found: {manifest_path}")
    data = _load_json_or_yaml(manifest_path)
    if not isinstance(data, dict):
        raise ValueError("command safety manifest must be a mapping")
    commands = data.get("commands")
    if not isinstance(commands, dict):
        raise ValueError("command safety manifest missing commands mapping")
    return data


def load_exchange_for_dispatch(root: str | Path, exchange_id: str) -> dict[str, Any]:
    target_dir = exchange_dir(root, exchange_id)
    packet_path = _safe_child(target_dir, target_dir / EXCHANGE_PACKET_FILENAME)
    if not packet_path.is_file():
        raise FileNotFoundError(f"exchange packet not found: {packet_path}")
    data = _load_json_or_yaml(packet_path)
    if not isinstance(data, dict):
        raise ValueError(f"exchange packet must be a mapping: {packet_path}")
    return validate_exchange_packet(data)


def validate_target_supported(packet: dict[str, Any]) -> list[str]:
    target = str(packet.get("target", ""))
    if target not in ALLOWED_TARGETS:
        return [f"unsupported target: {target}"]
    return []


def validate_allowed_commands_known(packet: dict[str, Any], command_manifest: dict[str, Any]) -> tuple[list[str], list[str]]:
    commands = command_manifest.get("commands", {})
    allowed = packet.get("allowed_commands", [])
    blockers: list[str] = []
    warnings: list[str] = []

    if not isinstance(allowed, list):
        return ["allowed_commands must be a list"], warnings

    unknown = [cmd for cmd in allowed if cmd not in commands]
    if unknown:
        blockers.append("unknown allowed_commands: " + ", ".join(sorted(set(unknown))))

    if not allowed and str(packet.get("safety_mode", "")) == "REVIEW_ONLY":
        warnings.append("allowed_commands is empty; REVIEW_ONLY can proceed without command execution")

    return blockers, warnings


def validate_forbidden_actions_present(packet: dict[str, Any]) -> list[str]:
    items = packet.get("forbidden_actions")
    if not isinstance(items, list) or not [x for x in items if str(x).strip()]:
        return ["forbidden_actions must be a non-empty list"]
    return []


def validate_expected_outputs_present(packet: dict[str, Any]) -> list[str]:
    items = packet.get("expected_outputs")
    if not isinstance(items, list) or not [x for x in items if str(x).strip()]:
        return ["expected_outputs must be a non-empty list"]
    return []


def validate_exchange_dispatch_ready(packet: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []

    status = str(packet.get("status", ""))
    if status not in ALLOWED_DISPATCH_STATUSES:
        blockers.append(f"status must be one of {sorted(ALLOWED_DISPATCH_STATUSES)}, got: {status}")

    safety_mode = str(packet.get("safety_mode", ""))
    if safety_mode not in ALLOWED_SAFETY_MODES:
        blockers.append(f"unsupported safety_mode: {safety_mode}")

    blockers.extend(validate_target_supported(packet))

    if not isinstance(packet.get("approval_required"), bool):
        blockers.append("approval_required must be boolean")

    ac_blockers, ac_warnings = validate_allowed_commands_known(packet, manifest)
    blockers.extend(ac_blockers)
    warnings.extend(ac_warnings)

    blockers.extend(validate_forbidden_actions_present(packet))
    blockers.extend(validate_expected_outputs_present(packet))

    source_artifacts = packet.get("source_artifacts")
    if not isinstance(source_artifacts, list):
        blockers.append("source_artifacts must be a list")
    elif not source_artifacts:
        warnings.append("source_artifacts is empty")

    output_schema = packet.get("output_schema")
    if output_schema in (None, ""):
        warnings.append("output_schema is empty")

    stop_conditions = packet.get("stop_conditions")
    if not isinstance(stop_conditions, list) or not [x for x in stop_conditions if str(x).strip()]:
        blockers.append("stop_conditions must be a non-empty list")

    result = "PASS"
    if blockers:
        result = "FAIL"
    elif warnings:
        result = "WARN"

    return {
        "result": result,
        "blockers": blockers,
        "warnings": warnings,
    }


def render_dispatch_preview(packet: dict[str, Any], validation_result: dict[str, Any]) -> str:
    blockers = validation_result.get("blockers", [])
    warnings = validation_result.get("warnings", [])
    result = validation_result.get("result", "FAIL")
    allowed_commands = packet.get("allowed_commands", [])
    forbidden_actions = packet.get("forbidden_actions", [])
    expected_outputs = packet.get("expected_outputs", [])
    source_artifacts = packet.get("source_artifacts", [])

    lines = [
        "# Exchange Dispatch Preview",
        "",
        "DRY RUN - no execution and no files written.",
        "No adapter/model/provider/agent/browser/MCP calls.",
        "No shell command execution from packet content.",
        "",
        f"dispatch_readiness: {result}",
        "",
        "## Packet",
        "",
        f"- exchange_id: `{packet.get('exchange_id', '')}`",
        f"- target: `{packet.get('target', '')}`",
        f"- task_type: `{packet.get('task_type', '')}`",
        f"- task_summary: {packet.get('task_summary', '')}",
        f"- safety_mode: `{packet.get('safety_mode', '')}`",
        f"- approval_required: `{packet.get('approval_required', '')}`",
        f"- status: `{packet.get('status', '')}`",
        "",
        "## Validation",
        "",
        f"- allowed_commands_count: {len(allowed_commands) if isinstance(allowed_commands, list) else 0}",
        f"- forbidden_actions_count: {len(forbidden_actions) if isinstance(forbidden_actions, list) else 0}",
        f"- expected_outputs_count: {len(expected_outputs) if isinstance(expected_outputs, list) else 0}",
        f"- source_artifacts_count: {len(source_artifacts) if isinstance(source_artifacts, list) else 0}",
        "",
        "### Allowed Commands",
    ]

    if isinstance(allowed_commands, list) and allowed_commands:
        lines.extend([f"- {cmd}" for cmd in allowed_commands])
    else:
        lines.append("- none")

    lines.extend(["", "### Forbidden Actions"])
    if isinstance(forbidden_actions, list) and forbidden_actions:
        lines.extend([f"- {item}" for item in forbidden_actions])
    else:
        lines.append("- none")

    lines.extend(["", "### Expected Outputs"])
    if isinstance(expected_outputs, list) and expected_outputs:
        lines.extend([f"- {item}" for item in expected_outputs])
    else:
        lines.append("- none")

    lines.extend(["", "### Source Artifacts"])
    if isinstance(source_artifacts, list) and source_artifacts:
        lines.extend([f"- {item}" for item in source_artifacts])
    else:
        lines.append("- none")

    lines.extend(["", "### Blockers"])
    if blockers:
        lines.extend([f"- {item}" for item in blockers])
    else:
        lines.append("- none")

    lines.extend(["", "### Warnings"])
    if warnings:
        lines.extend([f"- {item}" for item in warnings])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Next Step",
            "",
            "- Future `ws exchange-dispatch --confirm` (not implemented in this slice).",
        ]
    )

    return "\n".join(lines) + "\n"
