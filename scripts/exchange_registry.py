#!/usr/bin/env python3
"""Deterministic file-backed Exchange Lane Phase 0 helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXCHANGE_ROOT_DIRNAME = "exchange"
EXCHANGE_PACKET_FILENAME = "exchange.yaml"
PHASE0_FILES = (
    EXCHANGE_PACKET_FILENAME,
    "prompt.md",
    "source_artifacts.md",
    "allowed_commands.md",
    "forbidden_actions.md",
    "expected_outputs.md",
    "run_log.md",
)
ALLOWED_TARGETS = {
    "codex_cli",
    "gemini_cli",
    "local_ollama",
    "browser_chatgpt",
    "browser_gemini",
    "future_mcp",
}
ALLOWED_STATUSES = {"DRAFT", "READY", "ACTIVE", "COMPLETED", "FAILED", "BLOCKED"}
ALLOWED_SAFETY_MODES = {
    "DRY_RUN_ONLY",
    "REVIEW_ONLY",
    "GUARDED_EXECUTION",
    "BROWSER_TRANSPORT",
    "LOCAL_MODEL_WORKER",
}
REQUIRED_PACKET_FIELDS = (
    "exchange_id",
    "created_at",
    "source",
    "target",
    "product_id",
    "task_type",
    "task_summary",
    "source_artifacts",
    "allowed_commands",
    "forbidden_actions",
    "expected_outputs",
    "output_schema",
    "stop_conditions",
    "safety_mode",
    "approval_required",
    "status",
    "result_paths",
)
EXCHANGE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,80}$")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_child(base: Path, child: Path) -> Path:
    base_resolved = base.resolve()
    child_resolved = child.resolve()
    if child_resolved == base_resolved:
        return child_resolved
    if base_resolved not in child_resolved.parents:
        raise ValueError(f"path escapes expected base: {child_resolved} not under {base_resolved}")
    return child_resolved


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip())


def _as_list_of_str(name: str, value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{name} must be a list of strings")
    return [str(item).strip() for item in value if str(item).strip()]


def slugify_exchange_id(text: str) -> str:
    candidate = re.sub(r"[^a-z0-9]+", "-", str(text).strip().lower()).strip("-")
    candidate = re.sub(r"-{2,}", "-", candidate)
    return candidate


def validate_exchange_id(exchange_id: str) -> bool:
    if not isinstance(exchange_id, str):
        return False
    candidate = exchange_id.strip()
    if candidate != exchange_id:
        return False
    if not EXCHANGE_ID_RE.fullmatch(candidate):
        return False
    if any(token in candidate for token in ("/", "\\", "..", " ")):
        return False
    return True


def exchange_root(root: str | Path) -> Path:
    return Path(root).expanduser().resolve() / EXCHANGE_ROOT_DIRNAME


def exchange_dir(root: str | Path, exchange_id: str) -> Path:
    if not validate_exchange_id(exchange_id):
        raise ValueError(f"invalid exchange_id: {exchange_id!r}")
    base = exchange_root(root)
    return _safe_child(base, base / exchange_id)


def validate_exchange_packet(packet: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, dict):
        raise ValueError("exchange packet must be a mapping")

    missing = [name for name in REQUIRED_PACKET_FIELDS if name not in packet]
    if missing:
        raise ValueError("missing required packet fields: " + ", ".join(missing))

    exchange_id = str(packet.get("exchange_id", "")).strip()
    if not validate_exchange_id(exchange_id):
        raise ValueError(f"invalid exchange_id: {exchange_id!r}")

    target = str(packet.get("target", "")).strip()
    if target not in ALLOWED_TARGETS:
        raise ValueError("unsupported target: " + target)

    safety_mode = str(packet.get("safety_mode", "")).strip()
    if safety_mode not in ALLOWED_SAFETY_MODES:
        raise ValueError("unsupported safety_mode: " + safety_mode)

    status = str(packet.get("status", "")).strip()
    if status not in ALLOWED_STATUSES:
        raise ValueError("unsupported status: " + status)

    created_at = str(packet.get("created_at", "")).strip()
    if not created_at:
        raise ValueError("created_at is required")

    source = _normalize_text(str(packet.get("source", "")))
    task_type = _normalize_text(str(packet.get("task_type", "")))
    task_summary = _normalize_text(str(packet.get("task_summary", "")))
    if not source:
        raise ValueError("source must be a non-empty string")
    if not task_type:
        raise ValueError("task_type must be a non-empty string")
    if not task_summary:
        raise ValueError("task_summary must be a non-empty string")

    product_id = _normalize_text(str(packet.get("product_id", "")))
    source_artifacts = _as_list_of_str("source_artifacts", packet.get("source_artifacts"))
    allowed_commands = _as_list_of_str("allowed_commands", packet.get("allowed_commands"))
    forbidden_actions = _as_list_of_str("forbidden_actions", packet.get("forbidden_actions"))
    expected_outputs = _as_list_of_str("expected_outputs", packet.get("expected_outputs"))
    stop_conditions = _as_list_of_str("stop_conditions", packet.get("stop_conditions"))

    output_schema = packet.get("output_schema")
    result_paths = packet.get("result_paths")
    if not isinstance(output_schema, dict):
        raise ValueError("output_schema must be a mapping")
    if not isinstance(result_paths, dict):
        raise ValueError("result_paths must be a mapping")
    if not isinstance(packet.get("approval_required"), bool):
        raise ValueError("approval_required must be boolean")

    normalized = dict(packet)
    normalized["exchange_id"] = exchange_id
    normalized["created_at"] = created_at
    normalized["source"] = source
    normalized["target"] = target
    normalized["product_id"] = product_id
    normalized["task_type"] = task_type
    normalized["task_summary"] = task_summary
    normalized["source_artifacts"] = source_artifacts
    normalized["allowed_commands"] = allowed_commands
    normalized["forbidden_actions"] = forbidden_actions
    normalized["expected_outputs"] = expected_outputs
    normalized["output_schema"] = output_schema
    normalized["stop_conditions"] = stop_conditions
    normalized["safety_mode"] = safety_mode
    normalized["approval_required"] = bool(packet.get("approval_required"))
    normalized["status"] = status
    normalized["result_paths"] = result_paths
    return normalized


def create_exchange_packet(
    *,
    target: str,
    task_type: str,
    summary: str,
    product_id: str = "",
    source: str = "operator",
    safety_mode: str = "REVIEW_ONLY",
    exchange_id: str | None = None,
) -> dict[str, Any]:
    candidate_id = exchange_id or f"{target}-{task_type}-{summary[:48]}"
    normalized_id = slugify_exchange_id(candidate_id)
    if not validate_exchange_id(normalized_id):
        raise ValueError(f"could not derive a valid exchange_id from: {candidate_id!r}")

    packet = {
        "exchange_id": normalized_id,
        "created_at": _utc_now_iso(),
        "source": source,
        "target": target,
        "product_id": _normalize_text(product_id),
        "task_type": task_type,
        "task_summary": summary,
        "source_artifacts": [],
        "allowed_commands": [],
        "forbidden_actions": [
            "No model/provider/agent/browser/MCP dispatch in Phase 0.",
            "No shell command execution from packet content.",
        ],
        "expected_outputs": [
            "Deterministic worker result summary (future phase).",
            "blocked_reason when task cannot proceed.",
        ],
        "output_schema": {
            "task_id": "string",
            "inputs_read": "list[string]",
            "commands_run": "list[string]",
            "files_changed": "list[string]",
            "tests_run": "list[string]",
            "result": "string",
            "blocked_reason": "string",
            "needs_human_decision": "boolean",
        },
        "stop_conditions": [
            "Stop on unknown command requirement.",
            "Stop on forbidden action requirement.",
        ],
        "safety_mode": safety_mode,
        "approval_required": True,
        "status": "READY",
        "result_paths": {},
    }
    return validate_exchange_packet(packet)


def render_exchange_preview(packet: dict[str, Any]) -> str:
    safe = validate_exchange_packet(packet)
    lines = [
        f"# Exchange Packet Preview: {safe['exchange_id']}",
        "",
        "DRY RUN - no files written.",
        "No dispatch is performed in Phase 0.",
        "No model/provider/agent/browser/MCP calls.",
        "",
        "## Metadata",
        "",
        f"- exchange_id: `{safe['exchange_id']}`",
        f"- created_at: `{safe['created_at']}`",
        f"- source: `{safe['source']}`",
        f"- target: `{safe['target']}`",
        f"- product_id: `{safe['product_id'] or 'NONE'}`",
        f"- task_type: `{safe['task_type']}`",
        f"- task_summary: {safe['task_summary']}",
        f"- safety_mode: `{safe['safety_mode']}`",
        f"- approval_required: `{safe['approval_required']}`",
        f"- status: `{safe['status']}`",
        "",
        "## Planned Files",
        "",
    ]
    for name in PHASE0_FILES:
        lines.append(f"- exchange/{safe['exchange_id']}/{name}")
    lines.extend(
        [
            "",
            "## Next Step",
            "",
            "- Confirm packet creation with `ws exchange-new --confirm`.",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_file_contents(packet: dict[str, Any]) -> dict[str, str]:
    safe = validate_exchange_packet(packet)
    exchange_yaml = json.dumps(safe, indent=2) + "\n"
    prompt_md = (
        f"# Exchange Prompt: {safe['exchange_id']}\n\n"
        f"Target: `{safe['target']}`\n"
        f"Task Type: `{safe['task_type']}`\n"
        f"Summary: {safe['task_summary']}\n\n"
        "Phase 0 note: packet creation only; dispatch is not implemented.\n"
    )
    source_artifacts_md = "# Source Artifacts\n\n"
    if safe["source_artifacts"]:
        source_artifacts_md += "".join(f"- {item}\n" for item in safe["source_artifacts"])
    else:
        source_artifacts_md += "- none recorded in Phase 0\n"

    allowed_commands_md = "# Allowed Commands\n\n"
    if safe["allowed_commands"]:
        allowed_commands_md += "".join(f"- {item}\n" for item in safe["allowed_commands"])
    else:
        allowed_commands_md += "- none recorded in Phase 0\n"

    forbidden_actions_md = "# Forbidden Actions\n\n" + "".join(f"- {item}\n" for item in safe["forbidden_actions"])
    expected_outputs_md = "# Expected Outputs\n\n" + "".join(f"- {item}\n" for item in safe["expected_outputs"])
    run_log_md = (
        "# Run Log\n\n"
        "- Phase 0 packet created.\n"
        "- No execution or dispatch performed.\n"
    )
    return {
        EXCHANGE_PACKET_FILENAME: exchange_yaml,
        "prompt.md": prompt_md,
        "source_artifacts.md": source_artifacts_md,
        "allowed_commands.md": allowed_commands_md,
        "forbidden_actions.md": forbidden_actions_md,
        "expected_outputs.md": expected_outputs_md,
        "run_log.md": run_log_md,
    }


def save_exchange(packet: dict[str, Any], root: str | Path, confirm: bool = False) -> dict[str, Any]:
    safe = validate_exchange_packet(packet)
    if not confirm:
        return {"packet": safe, "files_written": []}

    base = exchange_root(root)
    base.mkdir(parents=True, exist_ok=True)
    target_dir = exchange_dir(root, safe["exchange_id"])
    if target_dir.exists():
        raise FileExistsError(f"exchange already exists: {target_dir}")
    target_dir.mkdir(parents=True, exist_ok=False)

    files_written: list[str] = []
    file_contents = _render_file_contents(safe)
    for rel_name, content in file_contents.items():
        out_path = _safe_child(target_dir, target_dir / rel_name)
        out_path.write_text(content, encoding="utf-8", newline="\n")
        files_written.append(str(out_path))
    return {"packet": safe, "files_written": files_written}


def _load_exchange_packet(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore[import-not-found]
        except Exception as exc:
            raise ValueError(f"exchange packet is not JSON and PyYAML is unavailable: {exc}") from exc
        data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError(f"exchange packet must be a mapping: {path}")
    return validate_exchange_packet(data)


def list_exchanges(root: str | Path) -> list[dict[str, Any]]:
    base = exchange_root(root)
    if not base.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for child in sorted((p for p in base.iterdir() if p.is_dir()), key=lambda p: p.name):
        packet_path = _safe_child(child, child / EXCHANGE_PACKET_FILENAME)
        if not packet_path.is_file():
            rows.append(
                {
                    "exchange_id": child.name,
                    "status": "BLOCKED",
                    "target": "UNKNOWN",
                    "created_at": "",
                    "path": str(child),
                    "error": "missing exchange.yaml",
                }
            )
            continue
        try:
            packet = _load_exchange_packet(packet_path)
            rows.append(
                {
                    "exchange_id": packet["exchange_id"],
                    "status": packet["status"],
                    "target": packet["target"],
                    "created_at": packet["created_at"],
                    "path": str(child),
                    "error": "",
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "exchange_id": child.name,
                    "status": "BLOCKED",
                    "target": "UNKNOWN",
                    "created_at": "",
                    "path": str(child),
                    "error": str(exc),
                }
            )
    return rows


def get_exchange_status(root: str | Path, exchange_id: str) -> dict[str, Any]:
    target_dir = exchange_dir(root, exchange_id)
    packet_path = _safe_child(target_dir, target_dir / EXCHANGE_PACKET_FILENAME)
    if not packet_path.is_file():
        raise FileNotFoundError(f"exchange packet not found: {packet_path}")
    packet = _load_exchange_packet(packet_path)
    packet["exchange_path"] = str(target_dir)
    return packet

