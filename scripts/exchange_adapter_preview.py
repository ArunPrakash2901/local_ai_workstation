#!/usr/bin/env python3
"""Deterministic no-execution Exchange Lane adapter preview helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from exchange_dispatch import (
    _load_command_manifest,
    load_exchange_for_dispatch,
    validate_allowed_commands_known,
)
from session_registry import load_session_manifest

SUPPORTED_PREVIEW_TARGETS = {"codex_cli"}
SUPPORTED_PREVIEW_SAFETY_MODES = {"REVIEW_ONLY", "DRY_RUN_ONLY"}


def load_exchange_adapter_context(root: str | Path, exchange_id: str) -> dict[str, Any]:
    packet = load_exchange_for_dispatch(root, exchange_id)
    exchange_dir = Path(root).resolve() / "exchange" / packet["exchange_id"]
    return {
        "packet": packet,
        "exchange_dir": exchange_dir,
        "prompt_path": exchange_dir / "prompt.md",
        "allowed_commands_path": exchange_dir / "allowed_commands.md",
        "forbidden_actions_path": exchange_dir / "forbidden_actions.md",
        "expected_outputs_path": exchange_dir / "expected_outputs.md",
        "raw_output_path": exchange_dir / "raw_output.md",
    }


def validate_adapter_preview_preconditions(packet: dict[str, Any], target: str, manifest: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []

    packet_target = str(packet.get("target", "")).strip()
    if target not in SUPPORTED_PREVIEW_TARGETS:
        blockers.append(f"unsupported adapter preview target in this slice: {target}")

    if packet_target != target:
        blockers.append(f"packet target mismatch: packet target is {packet_target}, requested target is {target}")

    safety_mode = str(packet.get("safety_mode", "")).strip()
    if safety_mode not in SUPPORTED_PREVIEW_SAFETY_MODES:
        blockers.append(
            "safety_mode not yet supported for adapter preview in this slice: " + safety_mode
        )

    allowed = packet.get("allowed_commands", [])
    ac_blockers, ac_warnings = validate_allowed_commands_known(packet, manifest)
    blockers.extend(ac_blockers)
    warnings.extend(ac_warnings)

    if not isinstance(allowed, list):
        blockers.append("allowed_commands must be a list")

    forbidden_actions = packet.get("forbidden_actions", [])
    if not isinstance(forbidden_actions, list) or not [x for x in forbidden_actions if str(x).strip()]:
        blockers.append("forbidden_actions must be a non-empty list")

    expected_outputs = packet.get("expected_outputs", [])
    if not isinstance(expected_outputs, list) or not [x for x in expected_outputs if str(x).strip()]:
        blockers.append("expected_outputs must be a non-empty list")

    stop_conditions = packet.get("stop_conditions", [])
    if not isinstance(stop_conditions, list) or not [x for x in stop_conditions if str(x).strip()]:
        blockers.append("stop_conditions must be a non-empty list")

    status = str(packet.get("status", "")).strip()
    if status == "COMPLETED":
        warnings.append(
            "exchange status is COMPLETED and may already have imported results; preview remains read-only"
        )

    preview_status = "PASS"
    if blockers:
        preview_status = "FAIL"
    elif warnings:
        preview_status = "WARN"

    return {
        "preview_status": preview_status,
        "blockers": blockers,
        "warnings": warnings,
    }


def render_codex_cli_preview(packet: dict[str, Any], exchange_dir: Path, validation_result: dict[str, Any]) -> str:
    allowed_commands = packet.get("allowed_commands", [])
    forbidden_actions = packet.get("forbidden_actions", [])
    stop_conditions = packet.get("stop_conditions", [])
    expected_outputs = packet.get("expected_outputs", [])

    lines = [
        "# Exchange Adapter Preview",
        "",
        "DRY RUN - no adapter execution and no files written.",
        "Codex CLI was not executed.",
        "",
        f"adapter_preview_status: {validation_result.get('preview_status', 'FAIL')}",
        "",
        "## Exchange",
        "",
        f"- exchange_id: `{packet.get('exchange_id', '')}`",
        f"- target: `{packet.get('target', '')}`",
        f"- task_type: `{packet.get('task_type', '')}`",
        f"- task_summary: {packet.get('task_summary', '')}",
        f"- safety_mode: `{packet.get('safety_mode', '')}`",
        f"- status: `{packet.get('status', '')}`",
        "",
        "## Session Integration Preview",
    ]

    session_suggestion = validation_result.get("session_suggestion", {})
    if session_suggestion.get("found"):
        lines.extend(
            [
                f"- suggested_session_id: `{session_suggestion.get('session_id', '')}`",
                f"- session_status: `{session_suggestion.get('status', '')}`",
                f"- runtime_type: `{session_suggestion.get('runtime_type', '')}`",
                f"- adapter: `{session_suggestion.get('adapter', '')}`",
                "- no process started",
            ]
        )
    else:
        lines.append("- warning: no matching planned runtime session found")

    lines.extend(
        [
            "",
        "## Planned Adapter Invocation",
        "",
        "- adapter: `codex_cli`",
        "- execution_mode: `preview_only`",
        f"- prompt_path: `{(exchange_dir / 'prompt.md').as_posix()}`",
        f"- planned_output_capture_path: `{(exchange_dir / 'raw_output.md').as_posix()}`",
        "",
        "## Future Import Step",
        "",
        f"- `ws exchange-import-result --exchange {packet.get('exchange_id', '')} --file <result_file> --confirm`",
        "",
        "## Allowed Commands",
        ]
    )

    if isinstance(allowed_commands, list) and allowed_commands:
        lines.extend([f"- {cmd}" for cmd in allowed_commands])
    else:
        lines.append("- none")

    lines.extend(["", "## Forbidden Actions"])
    if isinstance(forbidden_actions, list) and forbidden_actions:
        lines.extend([f"- {item}" for item in forbidden_actions])
    else:
        lines.append("- none")

    lines.extend(["", "## Stop Conditions"])
    if isinstance(stop_conditions, list) and stop_conditions:
        lines.extend([f"- {item}" for item in stop_conditions])
    else:
        lines.append("- none")

    lines.extend(["", "## Expected Outputs"])
    if isinstance(expected_outputs, list) and expected_outputs:
        lines.extend([f"- {item}" for item in expected_outputs])
    else:
        lines.append("- none")

    lines.extend(["", "## Blockers"])
    blockers = validation_result.get("blockers", [])
    if blockers:
        lines.extend([f"- {item}" for item in blockers])
    else:
        lines.append("- none")

    lines.extend(["", "## Warnings"])
    warnings = validation_result.get("warnings", [])
    if warnings:
        lines.extend([f"- {item}" for item in warnings])
    else:
        lines.append("- none")

    lines.extend(["", "## Next Step", "", "- Future adapter execution path (not implemented in this slice)."])

    return "\n".join(lines) + "\n"


def render_adapter_preview(packet: dict[str, Any], target: str, exchange_dir: Path, validation_result: dict[str, Any]) -> str:
    if target == "codex_cli":
        return render_codex_cli_preview(packet, exchange_dir, validation_result)
    raise ValueError(f"unsupported adapter preview target: {target}")


def preview_exchange_adapter(root: str | Path, exchange_id: str, target: str) -> dict[str, Any]:
    context = load_exchange_adapter_context(root, exchange_id)
    packet = context["packet"]
    manifest = _load_command_manifest(root)
    validation_result = validate_adapter_preview_preconditions(packet, target, manifest)
    validation_result["session_suggestion"] = suggest_runtime_session(root, packet, target)
    preview = render_adapter_preview(packet, target, context["exchange_dir"], validation_result)
    return {
        "preview": preview,
        "validation_result": validation_result,
        "packet": packet,
        "exchange_dir": str(context["exchange_dir"]),
    }


def suggest_runtime_session(root: str | Path, packet: dict[str, Any], target: str) -> dict[str, Any]:
    if target == "codex_cli":
        candidate_id = "codex-exchange-lane"
    elif target == "gemini_cli":
        candidate_id = "gemini-product-lane"
    elif target == "local_ollama":
        return {"found": False, "note": "local_ollama runtime session suggestion not implemented yet"}
    elif target in {"browser_chatgpt", "browser_gemini"}:
        return {"found": False, "note": "browser runtime integration not implemented yet"}
    else:
        return {"found": False, "note": "no session suggestion available for this target"}

    try:
        manifest = load_session_manifest(root, candidate_id)
    except Exception:
        return {"found": False, "session_id": candidate_id, "note": "no matching planned runtime session found"}

    return {
        "found": True,
        "session_id": manifest.get("session_id", candidate_id),
        "status": manifest.get("status", ""),
        "runtime_type": manifest.get("runtime_type", ""),
        "adapter": manifest.get("adapter", ""),
    }
