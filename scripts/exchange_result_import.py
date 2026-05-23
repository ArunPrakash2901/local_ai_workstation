#!/usr/bin/env python3
"""Deterministic Exchange Lane result import and operator-report skeleton helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from exchange_registry import EXCHANGE_PACKET_FILENAME, _safe_child, exchange_dir, validate_exchange_packet

REQUIRED_SECTIONS = ("Task ID", "Result", "Blocked Reason", "Needs Human Decision")
RECOMMENDED_SECTIONS = ("Inputs Read", "Commands Run", "Files Changed", "Tests Run")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def _load_exchange_yaml(path: Path) -> dict[str, Any]:
    data = _load_json_or_yaml(path)
    if not isinstance(data, dict):
        raise ValueError(f"exchange packet must be a mapping: {path}")
    return validate_exchange_packet(data)


def load_exchange_for_result_import(root: str | Path, exchange_id: str) -> tuple[dict[str, Any], Path]:
    target_dir = exchange_dir(root, exchange_id)
    packet_path = _safe_child(target_dir, target_dir / EXCHANGE_PACKET_FILENAME)
    if not packet_path.is_file():
        raise FileNotFoundError(f"exchange packet not found: {packet_path}")
    return _load_exchange_yaml(packet_path), target_dir


def validate_result_import_preconditions(root: str | Path, exchange_id: str, result_file: str | Path) -> dict[str, Any]:
    packet, target_dir = load_exchange_for_result_import(root, exchange_id)
    result_path = Path(result_file).expanduser().resolve()
    if not result_path.is_file():
        raise FileNotFoundError(f"result file not found: {result_path}")

    raw_output_path = _safe_child(target_dir, target_dir / "raw_output.md")
    if raw_output_path.exists():
        raise FileExistsError(f"duplicate import refused; raw_output.md already exists: {raw_output_path}")

    return {
        "packet": packet,
        "exchange_dir": target_dir,
        "packet_path": _safe_child(target_dir, target_dir / EXCHANGE_PACKET_FILENAME),
        "result_path": result_path,
        "raw_output_path": raw_output_path,
        "parsed_result_path": _safe_child(target_dir, target_dir / "parsed_result.json"),
        "validation_path": _safe_child(target_dir, target_dir / "validation.md"),
        "operator_report_path": _safe_child(target_dir, target_dir / "operator_report.md"),
        "run_log_path": _safe_child(target_dir, target_dir / "run_log.md"),
    }


def parse_basic_result_sections(result_text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    buffer: list[str] = []

    for line in result_text.splitlines():
        if line.strip().startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buffer).strip()
            current = line.strip()[3:].strip()
            buffer = []
        else:
            if current is not None:
                buffer.append(line)
    if current is not None:
        sections[current] = "\n".join(buffer).strip()
    return sections


def _validate_parsed_sections(parsed: dict[str, str]) -> dict[str, Any]:
    missing_required = [name for name in REQUIRED_SECTIONS if not parsed.get(name, "").strip()]
    empty_recommended = [name for name in RECOMMENDED_SECTIONS if not parsed.get(name, "").strip()]

    status = "PASS"
    warnings: list[str] = []
    blockers: list[str] = []

    if missing_required:
        status = "FAIL"
        blockers.append("missing required sections: " + ", ".join(missing_required))
    elif empty_recommended:
        status = "WARN"
        warnings.append("empty recommended sections: " + ", ".join(empty_recommended))

    return {
        "status": status,
        "warnings": warnings,
        "blockers": blockers,
        "missing_required": missing_required,
        "empty_recommended": empty_recommended,
    }


def _normalize_none_text(value: str) -> str:
    return value.strip()


def _decide_exchange_status(validation_status: str, parsed: dict[str, str]) -> str:
    if validation_status == "FAIL":
        return "FAILED"
    blocked_reason = _normalize_none_text(parsed.get("Blocked Reason", ""))
    if blocked_reason and blocked_reason.lower() not in {"none", "n/a", "na", "null"}:
        return "BLOCKED"
    return "COMPLETED"


def render_operator_report(packet: dict[str, Any], result_text: str, parsed_summary: dict[str, Any]) -> str:
    parsed = parsed_summary.get("parsed_sections", {})
    validation = parsed_summary.get("validation", {})
    next_status = parsed_summary.get("next_exchange_status", "FAILED")

    lines = [
        "# Operator Report",
        "",
        "Imported result text treated as untrusted input.",
        "No command execution was performed from imported content.",
        "",
        "## Exchange",
        "",
        f"- exchange_id: `{packet.get('exchange_id', '')}`",
        f"- target: `{packet.get('target', '')}`",
        f"- task_type: `{packet.get('task_type', '')}`",
        f"- safety_mode: `{packet.get('safety_mode', '')}`",
        f"- previous_status: `{packet.get('status', '')}`",
        f"- new_status: `{next_status}`",
        "",
        "## Validation",
        "",
        f"- import_validation: `{validation.get('status', 'FAIL')}`",
    ]

    for item in validation.get("blockers", []):
        lines.append(f"- blocker: {item}")
    for item in validation.get("warnings", []):
        lines.append(f"- warning: {item}")

    lines.extend([
        "",
        "## Parsed Summary",
        "",
        f"- Task ID: {parsed.get('Task ID', 'MISSING')}",
        f"- Result: {parsed.get('Result', 'MISSING')}",
        f"- Blocked Reason: {parsed.get('Blocked Reason', 'MISSING')}",
        f"- Needs Human Decision: {parsed.get('Needs Human Decision', 'MISSING')}",
        "",
        "## Next Action",
        "",
        "- Review imported result and decide follow-up workflow.",
        "- Adapter dispatch remains future work; no execution has occurred in this slice.",
        "",
        "## Raw Result Snapshot",
        "",
        "```markdown",
        result_text.strip(),
        "```",
    ])

    return "\n".join(lines) + "\n"


def _render_validation_md(parsed_summary: dict[str, Any]) -> str:
    validation = parsed_summary["validation"]
    lines = [
        "# Result Import Validation",
        "",
        f"validation_status: {validation['status']}",
        "",
        "## Blockers",
    ]
    if validation["blockers"]:
        lines.extend([f"- {x}" for x in validation["blockers"]])
    else:
        lines.append("- none")

    lines.extend(["", "## Warnings"])
    if validation["warnings"]:
        lines.extend([f"- {x}" for x in validation["warnings"]])
    else:
        lines.append("- none")

    lines.extend(["", "## Policy", "", "- Imported text is untrusted and never executed."])
    return "\n".join(lines) + "\n"


def _append_run_log(run_log_path: Path, message: str) -> None:
    timestamp = _utc_now_iso()
    if run_log_path.exists():
        existing = run_log_path.read_text(encoding="utf-8")
        suffix = "" if existing.endswith("\n") else "\n"
        run_log_path.write_text(existing + suffix + f"- {timestamp} {message}\n", encoding="utf-8", newline="\n")
    else:
        run_log_path.write_text("# Run Log\n\n" + f"- {timestamp} {message}\n", encoding="utf-8", newline="\n")


def _render_import_preview(packet: dict[str, Any], result_file: Path, parsed_summary: dict[str, Any], planned_paths: dict[str, Path]) -> str:
    validation = parsed_summary["validation"]
    lines = [
        "# Exchange Result Import Preview",
        "",
        "DRY RUN - no files written.",
        "Imported text is treated as untrusted; no content execution.",
        "",
        "## Exchange",
        "",
        f"- exchange_id: `{packet.get('exchange_id', '')}`",
        f"- target: `{packet.get('target', '')}`",
        f"- task_type: `{packet.get('task_type', '')}`",
        f"- status_before: `{packet.get('status', '')}`",
        f"- status_after: `{parsed_summary['next_exchange_status']}`",
        "",
        "## Validation",
        "",
        f"- validation_status: `{validation['status']}`",
        f"- missing_required_count: {len(validation['missing_required'])}",
        f"- empty_recommended_count: {len(validation['empty_recommended'])}",
        "",
        "## Planned Writes",
        "",
        f"- {planned_paths['raw_output_path']}",
        f"- {planned_paths['parsed_result_path']}",
        f"- {planned_paths['validation_path']}",
        f"- {planned_paths['operator_report_path']}",
        f"- update {planned_paths['packet_path']}",
        f"- append {planned_paths['run_log_path']}",
        "",
        "## Result File",
        "",
        f"- source: `{result_file}`",
    ]
    return "\n".join(lines) + "\n"


def import_exchange_result(root: str | Path, exchange_id: str, result_file: str | Path, confirm: bool = False) -> dict[str, Any]:
    pre = validate_result_import_preconditions(root, exchange_id, result_file)
    packet = pre["packet"]
    result_text = pre["result_path"].read_text(encoding="utf-8")
    parsed = parse_basic_result_sections(result_text)
    validation = _validate_parsed_sections(parsed)
    next_status = _decide_exchange_status(validation["status"], parsed)

    parsed_summary = {
        "parsed_sections": parsed,
        "validation": validation,
        "next_exchange_status": next_status,
    }

    if not confirm:
        return {
            "dry_run": True,
            "preview": _render_import_preview(packet, pre["result_path"], parsed_summary, pre),
            "parsed_summary": parsed_summary,
        }

    raw_output_text = "# Exchange Result\n\n" + result_text if not result_text.lstrip().startswith("#") else result_text
    pre["raw_output_path"].write_text(raw_output_text, encoding="utf-8", newline="\n")

    parsed_payload = {
        "exchange_id": packet.get("exchange_id", ""),
        "validation_status": validation["status"],
        "next_exchange_status": next_status,
        "parsed_sections": parsed,
        "warnings": validation["warnings"],
        "blockers": validation["blockers"],
    }
    pre["parsed_result_path"].write_text(json.dumps(parsed_payload, indent=2) + "\n", encoding="utf-8", newline="\n")
    pre["validation_path"].write_text(_render_validation_md(parsed_summary), encoding="utf-8", newline="\n")
    pre["operator_report_path"].write_text(
        render_operator_report(packet, result_text, parsed_summary),
        encoding="utf-8",
        newline="\n",
    )

    updated_packet = dict(packet)
    updated_packet["status"] = next_status
    updated_packet["result_paths"] = {
        "raw_output": str(pre["raw_output_path"].relative_to(pre["exchange_dir"])).replace("\\", "/"),
        "parsed_result": str(pre["parsed_result_path"].relative_to(pre["exchange_dir"])).replace("\\", "/"),
        "validation": str(pre["validation_path"].relative_to(pre["exchange_dir"])).replace("\\", "/"),
        "operator_report": str(pre["operator_report_path"].relative_to(pre["exchange_dir"])).replace("\\", "/"),
    }
    updated_packet["updated_at"] = _utc_now_iso()
    updated_packet["last_action"] = "ws exchange-import-result --confirm"

    pre["packet_path"].write_text(json.dumps(updated_packet, indent=2) + "\n", encoding="utf-8", newline="\n")

    _append_run_log(pre["run_log_path"], f"Imported result file {pre['result_path'].name}; status={next_status}; validation={validation['status']}")

    return {
        "dry_run": False,
        "parsed_summary": parsed_summary,
        "packet": updated_packet,
        "files_written": [
            str(pre["raw_output_path"]),
            str(pre["parsed_result_path"]),
            str(pre["validation_path"]),
            str(pre["operator_report_path"]),
            str(pre["packet_path"]),
            str(pre["run_log_path"]),
        ],
    }
