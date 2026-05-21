#!/usr/bin/env python3
"""Deterministic Product Lane scope change helpers."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from product_prd import PRD_FILENAME
from product_registry import (
    ACTION_LOG_FILENAME,
    PRODUCT_FILENAME,
    get_product_status,
    product_dir,
    save_product,
    validate_product_id,
)
from product_scope_lock import SCOPE_LOCK_FILENAME


SCOPE_CHANGE_DRY_RUN_ACTION = "ws product-scope-change --dry-run"
SCOPE_CHANGE_CONFIRM_ACTION = "ws product-scope-change --confirm"
SCOPE_LOCKED_STATE = "SCOPE_LOCKED"
APPROVED_STATUS = "APPROVED"
NEEDS_REVISION_STATUS = "NEEDS_REVISION"
DECISIONS_DIR = "decisions"
PRD_APPROVAL_FILENAME = "prd_approval.md"
SUPPORTED_CHANGE_FIELDS = {
    "out_of_scope",
    "non_goals",
    "constraints",
    "assumptions",
    "dependencies",
    "success_criteria",
}
REQUIRED_CHANGE_KEYS = ("change_id", "reason", "field", "proposed_value")
OPTIONAL_CHANGE_KEYS = ("operator_note",)
ALLOWED_CHANGE_KEYS = set(REQUIRED_CHANGE_KEYS) | set(OPTIONAL_CHANGE_KEYS)
KEY_RE = re.compile(r"^([a-z_]+):(?:\s*(.*))?$")


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


def _normalize_scalar(value: str) -> str:
    parts = [part.strip() for part in str(value).replace("\r\n", "\n").replace("\r", "\n").splitlines()]
    collapsed = " ".join(part for part in parts if part)
    return re.sub(r"\s+", " ", collapsed).strip()


def _canonicalize_multiline(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    return "\n".join(line.rstrip() for line in lines).rstrip("\n") + "\n"


def _slugify_change_id(change_id: str) -> str:
    candidate = re.sub(r"[^a-z0-9]+", "-", str(change_id).strip().lower()).strip("-")
    candidate = re.sub(r"-{2,}", "-", candidate)
    if not candidate:
        raise ValueError("change_id must contain at least one lowercase letter or digit")
    return candidate


def _append_action_log(path: Path, *, timestamp: str, message: str) -> None:
    if not path.is_file():
        return
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"- {timestamp} {message}\n")


def parse_scope_change_text(text: str) -> dict[str, str]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("change file must contain non-empty text")

    parsed: dict[str, str] = {}
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    index = 0

    while index < len(lines):
        raw_line = lines[index]
        stripped = raw_line.strip()
        index += 1

        if not stripped or stripped.startswith("#"):
            continue

        match = KEY_RE.match(stripped)
        if not match:
            raise ValueError(f"malformed change file line: {raw_line}")

        key = match.group(1).strip()
        if key in parsed:
            raise ValueError(f"duplicate key in change file: {key}")

        value = (match.group(2) or "").strip()
        if value == ">":
            block_lines: list[str] = []
            while index < len(lines):
                candidate = lines[index]
                if candidate.startswith(" ") or candidate.startswith("\t"):
                    block_lines.append(candidate.strip())
                    index += 1
                    continue
                if not candidate.strip():
                    block_lines.append("")
                    index += 1
                    continue
                break
            parsed[key] = _normalize_scalar("\n".join(block_lines))
            continue

        parsed[key] = _normalize_scalar(value)

    return parsed


def validate_scope_change_request(change: dict[str, Any]) -> dict[str, str]:
    if not isinstance(change, dict):
        raise ValueError("change request must be a mapping")

    unknown_keys = sorted(set(change) - ALLOWED_CHANGE_KEYS)
    if unknown_keys:
        raise ValueError("unsupported change file keys: " + ", ".join(unknown_keys))

    normalized: dict[str, str] = {}
    for key in REQUIRED_CHANGE_KEYS:
        value = _normalize_scalar(str(change.get(key, "")))
        if not value:
            raise ValueError(f"missing required change file key: {key}")
        normalized[key] = value

    for key in OPTIONAL_CHANGE_KEYS:
        value = _normalize_scalar(str(change.get(key, "")))
        if value:
            normalized[key] = value

    field = normalized["field"]
    if field not in SUPPORTED_CHANGE_FIELDS:
        raise ValueError(
            "unsupported field for this slice: "
            f"{field}. Supported fields: {', '.join(sorted(SUPPORTED_CHANGE_FIELDS))}"
        )

    if not normalized["proposed_value"]:
        raise ValueError("proposed_value must not be blank")

    return normalized


def load_scope_change_inputs(root: str | Path, product_id: str) -> dict[str, Any]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")

    product_record = get_product_status(root, product_id)
    pdir = product_dir(root, product_id)
    paths = {
        "product_dir": pdir,
        "product_file": _safe_child(pdir, pdir / PRODUCT_FILENAME),
        "scope_lock_md": _safe_child(pdir, pdir / SCOPE_LOCK_FILENAME),
        "prd_md": _safe_child(pdir, pdir / PRD_FILENAME),
        "prd_approval_md": _safe_child(pdir, pdir / DECISIONS_DIR / PRD_APPROVAL_FILENAME),
        "decisions_dir": _safe_child(pdir, pdir / DECISIONS_DIR),
        "wireframes_md": _safe_child(pdir, pdir / "wireframes.md"),
        "technical_plan_md": _safe_child(pdir, pdir / "technical_plan.md"),
        "answers_md": _safe_child(pdir, pdir / "answers.md"),
        "action_log": _safe_child(pdir, pdir / ACTION_LOG_FILENAME),
    }
    return {
        "product_record": product_record,
        "paths": paths,
    }


def compute_scope_change_impact(product_record: dict[str, Any], change: dict[str, str], paths: dict[str, Path]) -> dict[str, Any]:
    del change

    state = str(product_record.get("state", "")).strip() or "UNKNOWN"
    prd_status = str(product_record.get("prd_status", "")).strip().upper()
    scope_lock_hash = str(product_record.get("scope_lock_hash", "")).strip()

    artifact_flags = {
        "scope_lock.md": paths["scope_lock_md"].is_file(),
        "prd.md": paths["prd_md"].is_file(),
        "decisions/prd_approval.md": paths["prd_approval_md"].is_file(),
        "wireframes.md": paths["wireframes_md"].is_file(),
        "technical_plan.md": paths["technical_plan_md"].is_file(),
    }

    impacts: list[str] = []
    if state == SCOPE_LOCKED_STATE and artifact_flags["prd.md"]:
        impacts.append("PRD_WOULD_BECOME_STALE")
    if state == SCOPE_LOCKED_STATE and prd_status == APPROVED_STATUS:
        impacts.append("APPROVAL_WOULD_BECOME_STALE")
    if artifact_flags["wireframes.md"]:
        impacts.append("WIREFRAMES_WOULD_BECOME_STALE")
    if artifact_flags["technical_plan.md"]:
        impacts.append("TECHNICAL_PLAN_WOULD_BECOME_STALE")
    if not impacts:
        impacts.append("SCOPE_ONLY_CHANGE")

    would_stale = [name for name in impacts if name != "SCOPE_ONLY_CHANGE"]
    stale_artifacts: list[str] = []
    if "PRD_WOULD_BECOME_STALE" in impacts and artifact_flags["prd.md"]:
        stale_artifacts.append("prd.md")
    if "APPROVAL_WOULD_BECOME_STALE" in impacts and artifact_flags["decisions/prd_approval.md"]:
        stale_artifacts.append("decisions/prd_approval.md")
    if "WIREFRAMES_WOULD_BECOME_STALE" in impacts and artifact_flags["wireframes.md"]:
        stale_artifacts.append("wireframes.md")
    if "TECHNICAL_PLAN_WOULD_BECOME_STALE" in impacts and artifact_flags["technical_plan.md"]:
        stale_artifacts.append("technical_plan.md")

    return {
        "current_state": state,
        "scope_locked": state == SCOPE_LOCKED_STATE,
        "scope_lock_hash": scope_lock_hash or "UNSET",
        "prd_status": prd_status or "UNSET",
        "affected_artifacts": artifact_flags,
        "impacts": impacts,
        "would_become_stale": would_stale,
        "stale_artifacts": stale_artifacts,
    }


def render_scope_change_dry_run(
    product_record: dict[str, Any],
    change: dict[str, str],
    impact: dict[str, Any],
) -> str:
    product_id = str(product_record.get("product_id", "")).strip()
    label = str(product_record.get("label", "")).strip() or product_id
    product_type = str(product_record.get("product_type", "")).strip()

    lines = [
        f"# Scope Change Impact Preview: {label}",
        "",
        "DRY RUN - no files written.",
        "No product state changes.",
        "No model/provider/agent calls.",
        "",
        f"- product_id: `{product_id}`",
        f"- product_type: `{product_type}`",
        f"- current_state: `{impact.get('current_state', 'UNKNOWN')}`",
        f"- scope_locked: `{impact.get('scope_locked', False)}`",
        f"- current_scope_lock_hash: `{impact.get('scope_lock_hash', 'UNSET')}`",
        f"- current_prd_status: `{impact.get('prd_status', 'UNSET')}`",
        "",
        "## Proposed Change",
        "",
        f"- change_id: `{change.get('change_id', '')}`",
        f"- reason: {change.get('reason', '')}",
        f"- target_field: `{change.get('field', '')}`",
        f"- proposed_value: {change.get('proposed_value', '')}",
    ]

    operator_note = str(change.get("operator_note", "")).strip()
    if operator_note:
        lines.append(f"- operator_note: {operator_note}")

    lines.extend(
        [
            "",
            "## Affected Artifacts",
            "",
        ]
    )
    for artifact_name, exists in impact.get("affected_artifacts", {}).items():
        lines.append(f"- {artifact_name}: {'present' if exists else 'missing'}")

    lines.extend(
        [
            "",
            "## Impact Classification",
            "",
        ]
    )
    for item in impact.get("impacts", []):
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Revision Flow Implications",
            "",
            f"- product already scope locked: {impact.get('scope_locked', False)}",
        ]
    )
    would_become_stale = list(impact.get("would_become_stale", []))
    if would_become_stale:
        lines.append("- downstream artifacts would become stale in confirm/revision flow:")
        for item in would_become_stale:
            lines.append(f"  - {item}")
    else:
        lines.append("- downstream artifacts would become stale in confirm/revision flow: none detected")

    lines.extend(
        [
            "",
            "## Generated From",
            "",
            "- product.yaml",
            "- scope_lock.md",
            "- operator-provided change file",
            "",
            "## Next Step",
            "",
            f"- Confirm decision record with `{SCOPE_CHANGE_CONFIRM_ACTION} --product <product_id> --file <change_file>`.",
            "- Future ws product-scope-revision --dry-run will generate revised scope artifacts.",
            f"- Preview command used: `{SCOPE_CHANGE_DRY_RUN_ACTION} --product <product_id> --file <change_file>`",
            "",
        ]
    )
    return "\n".join(lines)


def scope_change_decision_path(root: str | Path, product_id: str, change_id_or_timestamp: str) -> Path:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")
    pdir = product_dir(root, product_id)
    slug = _slugify_change_id(change_id_or_timestamp)
    return _safe_child(pdir, pdir / DECISIONS_DIR / f"scope_change_{slug}.md")


def render_scope_change_decision(
    product_record: dict[str, Any],
    change: dict[str, str],
    impact: dict[str, Any],
    *,
    decision_path: Path,
    decided_at: str,
) -> str:
    product_id = str(product_record.get("product_id", "")).strip()
    product_type = str(product_record.get("product_type", "")).strip()
    current_state = str(product_record.get("state", "")).strip() or "UNKNOWN"
    scope_lock_hash = str(product_record.get("scope_lock_hash", "")).strip() or "UNSET"
    stale_artifacts = list(impact.get("stale_artifacts", []))

    lines = [
        "# Scope Change Decision",
        "",
        f"- decided_at: `{decided_at}`",
        f"- product_id: `{product_id}`",
        f"- product_type: `{product_type}`",
        f"- current_state: `{current_state}`",
        f"- current_scope_lock_hash: `{scope_lock_hash}`",
        f"- decision_path: `{decision_path}`",
        f"- change_id: `{change.get('change_id', '')}`",
        f"- reason: {change.get('reason', '')}",
        f"- field: `{change.get('field', '')}`",
        f"- proposed_value: {change.get('proposed_value', '')}",
    ]

    operator_note = str(change.get("operator_note", "")).strip()
    if operator_note:
        lines.append(f"- operator_note: {operator_note}")

    lines.extend(
        [
            "",
            "## Affected Artifacts",
            "",
        ]
    )
    for artifact_name, exists in impact.get("affected_artifacts", {}).items():
        lines.append(f"- {artifact_name}: {'present' if exists else 'missing'}")

    lines.extend(
        [
            "",
            "## Impact Classification",
            "",
        ]
    )
    for item in impact.get("impacts", []):
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Staleness Implications",
            "",
        ]
    )
    if stale_artifacts:
        for artifact_name in stale_artifacts:
            lines.append(f"- {artifact_name} would be stale until a future scope revision/PRD refresh flow runs")
    else:
        lines.append("- No downstream stale artifacts detected at decision-record time")

    lines.extend(
        [
            "",
            "## Safety Notes",
            "",
            "- This decision record does not directly edit scope_lock.md.",
            "- This decision record does not directly edit prd.md.",
            "- This decision record does not directly edit answers.md.",
            "- No model/provider/agent calls were used.",
            "",
            "## Generated From",
            "",
            "- product.yaml",
            "- scope_lock.md",
            "- operator-provided change file",
            "",
            "## Next Step",
            "",
            "- Future ws product-scope-revision --dry-run",
            "",
        ]
    )
    return _canonicalize_multiline("\n".join(lines))


def confirm_scope_change(root: str | Path, product_id: str, change_file: str | Path, *, confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise PermissionError("confirm_scope_change requires explicit confirm=True")
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")

    payload = load_scope_change_inputs(root, product_id)
    product_record = payload["product_record"]
    paths = payload["paths"]
    product_dir_path = Path(paths["product_dir"]).resolve()

    change_path = Path(change_file).expanduser()
    if not change_path.is_absolute():
        change_path = (_safe_child(Path(root).expanduser().resolve(), Path(root).expanduser().resolve() / change_path))
    else:
        change_path = change_path.resolve()
    if not change_path.is_file():
        raise FileNotFoundError(f"change file not found: {change_path}")

    change = validate_scope_change_request(parse_scope_change_text(change_path.read_text(encoding="utf-8")))
    impact = compute_scope_change_impact(product_record, change, paths)

    decision_path = scope_change_decision_path(root, product_id, change["change_id"])
    if decision_path.exists():
        raise FileExistsError(f"scope change decision already exists for change_id={change['change_id']}: {decision_path}")

    decisions_dir = _safe_child(product_dir_path, decision_path.parent)
    decisions_dir.mkdir(parents=True, exist_ok=True)

    timestamp = _utc_now_iso()
    decision_text = render_scope_change_decision(
        product_record,
        change,
        impact,
        decision_path=decision_path,
        decided_at=timestamp,
    )
    decision_path.write_text(decision_text, encoding="utf-8", newline="\n")

    updated_record = dict(product_record)
    updated_record["scope_change_pending"] = True
    updated_record["last_scope_change_at"] = timestamp
    updated_record["last_action"] = SCOPE_CHANGE_CONFIRM_ACTION
    updated_record["updated_at"] = timestamp
    updated_record["stale_artifacts"] = list(impact.get("stale_artifacts", []))
    if paths["prd_md"].is_file():
        updated_record["prd_status"] = NEEDS_REVISION_STATUS

    product_file = save_product(updated_record, root, confirm=True, allow_overwrite=True)
    _append_action_log(
        paths["action_log"],
        timestamp=timestamp,
        message=(
            f"scope change recorded via {SCOPE_CHANGE_CONFIRM_ACTION} "
            f"(change_id={change['change_id']}, field={change['field']})"
        ),
    )

    files_written = [str(decision_path), str(product_file)]
    if paths["action_log"].is_file():
        files_written.append(str(paths["action_log"]))

    return {
        "product_id": product_id,
        "decision_path": str(decision_path),
        "product_file": str(product_file),
        "action_log_path": str(paths["action_log"]),
        "change_id": change["change_id"],
        "field": change["field"],
        "scope_change_pending": True,
        "prd_status": updated_record.get("prd_status"),
        "stale_artifacts": list(updated_record.get("stale_artifacts", [])),
        "state_before": str(product_record.get("state", "")).strip(),
        "state_after": str(updated_record.get("state", "")).strip(),
        "last_scope_change_at": timestamp,
        "files_written": files_written,
        "used_model_provider_agent": False,
    }
