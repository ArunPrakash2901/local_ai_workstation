#!/usr/bin/env python3
"""Deterministic Product Lane scope revision preview helpers."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from product_registry import (
    ACTION_LOG_FILENAME,
    PRODUCT_FILENAME,
    get_product_status,
    product_dir,
    save_product,
    validate_product_id,
)
from product_scope_change import DECISIONS_DIR, SUPPORTED_CHANGE_FIELDS
from product_scope_lock import SCOPE_LOCK_FILENAME


SCOPE_REVISION_DRY_RUN_ACTION = "ws product-scope-revision --dry-run"
SCOPE_REVISION_CONFIRM_ACTION = "ws product-scope-revision --confirm"
SCOPE_CHANGE_PENDING_FIELD = "scope_change_pending"
SCOPE_CHANGE_PREFIX = "scope_change_"
SCOPE_LOCKS_DIR = "scope_locks"
SECTION_TITLES = {
    "out_of_scope": "Out of Scope",
    "non_goals": "Explicit Non-Goals",
    "constraints": "Constraints",
    "assumptions": "Assumptions",
    "dependencies": "Dependencies",
    "success_criteria": "Success Criteria",
}
KEY_LINE_PREFIXES = {
    "change_id": "- change_id:",
    "reason": "- reason:",
    "field": "- field:",
    "proposed_value": "- proposed_value:",
    "operator_note": "- operator_note:",
    "current_scope_lock_hash": "- current_scope_lock_hash:",
}


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


def _canonicalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    normalized = "\n".join(line.rstrip() for line in lines)
    return normalized.rstrip("\n") + "\n"


def _strip_ticks(value: str) -> str:
    cleaned = str(value).strip()
    if cleaned.startswith("`") and cleaned.endswith("`") and len(cleaned) >= 2:
        return cleaned[1:-1].strip()
    return cleaned


def _append_action_log(path: Path, *, timestamp: str, message: str) -> None:
    if not path.is_file():
        return
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"- {timestamp} {message}\n")


def parse_scope_change_decision(text: str) -> dict[str, str]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("scope change decision text must be non-empty")

    parsed: dict[str, str] = {}
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        line = raw_line.strip()
        for key, prefix in KEY_LINE_PREFIXES.items():
            if line.startswith(prefix):
                parsed[key] = _strip_ticks(line.split(":", 1)[1].strip())
                break

    required = ("change_id", "reason", "field", "proposed_value")
    missing = [key for key in required if not parsed.get(key)]
    if missing:
        raise ValueError("scope change decision missing required fields: " + ", ".join(missing))

    field = parsed["field"]
    if field not in SUPPORTED_CHANGE_FIELDS:
        raise ValueError(
            "unsupported scope change decision field for this slice: "
            f"{field}. Supported fields: {', '.join(sorted(SUPPORTED_CHANGE_FIELDS))}"
        )
    return parsed


def find_confirmed_scope_changes(root: str | Path, product_id: str) -> list[dict[str, Any]]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")

    pdir = product_dir(root, product_id)
    decisions_dir = _safe_child(pdir, pdir / DECISIONS_DIR)
    if not decisions_dir.is_dir():
        raise FileNotFoundError(f"scope change decisions directory not found: {decisions_dir}")

    decision_paths = sorted(
        path for path in decisions_dir.glob(f"{SCOPE_CHANGE_PREFIX}*.md") if path.is_file()
    )
    if not decision_paths:
        raise FileNotFoundError(f"no confirmed scope change decisions found in {decisions_dir}")

    changes: list[dict[str, Any]] = []
    seen_fields: set[str] = set()
    for path in decision_paths:
        parsed = parse_scope_change_decision(path.read_text(encoding="utf-8"))
        field = parsed["field"]
        if field in seen_fields:
            raise ValueError(
                "multiple pending scope changes target the same field in this slice: "
                f"{field}. Resolve or combine them before preview."
            )
        seen_fields.add(field)
        parsed["decision_path"] = str(path)
        changes.append(parsed)
    return changes


def load_scope_revision_inputs(root: str | Path, product_id: str) -> dict[str, Any]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")

    product_record = get_product_status(root, product_id)
    pdir = product_dir(root, product_id)
    scope_lock_path = _safe_child(pdir, pdir / SCOPE_LOCK_FILENAME)
    if not scope_lock_path.is_file():
        raise FileNotFoundError(f"scope lock not found: {scope_lock_path}")

    if product_record.get(SCOPE_CHANGE_PENDING_FIELD) is not True:
        raise ValueError("scope_change_pending must be true before previewing a scope revision")

    scope_lock_text = scope_lock_path.read_text(encoding="utf-8")
    changes = find_confirmed_scope_changes(root, product_id)

    return {
        "product_record": product_record,
        "scope_lock_text": scope_lock_text,
        "changes": changes,
        "paths": {
            "product_dir": pdir,
            "scope_lock_md": scope_lock_path,
            "product_file": _safe_child(pdir, pdir / "product.yaml"),
            "prd_md": _safe_child(pdir, pdir / "prd.md"),
            "answers_md": _safe_child(pdir, pdir / "answers.md"),
            "scope_locks_dir": _safe_child(pdir, pdir / SCOPE_LOCKS_DIR),
            "action_log": _safe_child(pdir, pdir / ACTION_LOG_FILENAME),
        },
    }


def apply_scope_change_to_scope_text(scope_lock_text: str, change: dict[str, Any]) -> dict[str, str]:
    field = str(change.get("field", "")).strip()
    section_title = SECTION_TITLES.get(field)
    if not section_title:
        raise ValueError(f"unsupported scope change field for revision preview: {field}")

    pattern = re.compile(
        rf"(?ms)^## {re.escape(section_title)}\n\n(?P<body>.*?)(?=^## |\Z)"
    )
    match = pattern.search(scope_lock_text)
    if not match:
        raise ValueError(
            f"target section not found in scope_lock.md for field={field}: {section_title}"
        )

    before_body = match.group("body").rstrip("\n")
    proposed_value = str(change.get("proposed_value", "")).strip()
    if not proposed_value:
        raise ValueError(f"scope change decision has blank proposed_value for field={field}")

    after_body = f"- {proposed_value}"
    replacement = f"## {section_title}\n\n{after_body}\n\n"
    revised_text = pattern.sub(replacement, scope_lock_text, count=1)

    return {
        "field": field,
        "section_title": section_title,
        "before_section": before_body or "- TODO/UNKNOWN",
        "after_section": after_body,
        "proposed_value": proposed_value,
        "change_id": str(change.get("change_id", "")).strip(),
        "decision_path": str(change.get("decision_path", "")).strip(),
        "revised_scope_text": _canonicalize_text(revised_text),
    }


def render_revised_scope_preview(
    product_record: dict[str, Any],
    scope_lock_text: str,
    changes: list[dict[str, Any]],
) -> dict[str, Any]:
    revised_text = _canonicalize_text(scope_lock_text)
    revised_sections: list[dict[str, str]] = []
    decision_paths: list[str] = []
    pending_change_ids: list[str] = []
    fields_affected: list[str] = []

    for change in changes:
        applied = apply_scope_change_to_scope_text(revised_text, change)
        revised_text = applied["revised_scope_text"]
        revised_sections.append(applied)
        pending_change_ids.append(applied["change_id"])
        fields_affected.append(applied["field"])
        decision_paths.append(applied["decision_path"])

    return {
        "product_id": str(product_record.get("product_id", "")).strip(),
        "product_type": str(product_record.get("product_type", "")).strip(),
        "current_state": str(product_record.get("state", "")).strip() or "UNKNOWN",
        "current_scope_lock_hash": str(product_record.get("scope_lock_hash", "")).strip() or "UNSET",
        "scope_change_pending": bool(product_record.get("scope_change_pending", False)),
        "stale_artifacts": list(product_record.get("stale_artifacts", []) or []),
        "pending_change_ids": pending_change_ids,
        "fields_affected": fields_affected,
        "decision_paths": decision_paths,
        "revised_sections": revised_sections,
        "revised_scope_text": revised_text,
    }


def render_scope_revision_dry_run(product_record: dict[str, Any], preview: dict[str, Any]) -> str:
    product_id = str(product_record.get("product_id", "")).strip()
    label = str(product_record.get("label", "")).strip() or product_id

    lines = [
        f"# Scope Revision Preview: {label}",
        "",
        "DRY RUN - no files written.",
        "No product state changes.",
        "No model/provider/agent calls.",
        "",
        "## Product Metadata",
        "",
        f"- product_id: `{preview.get('product_id', '')}`",
        f"- product_type: `{preview.get('product_type', '')}`",
        f"- current_state: `{preview.get('current_state', 'UNKNOWN')}`",
        f"- current_scope_lock_hash: `{preview.get('current_scope_lock_hash', 'UNSET')}`",
        f"- scope_change_pending: `{preview.get('scope_change_pending', False)}`",
        "",
        "## Affected Stale Artifacts",
        "",
    ]

    stale_artifacts = list(preview.get("stale_artifacts", []))
    if stale_artifacts:
        for artifact_name in stale_artifacts:
            lines.append(f"- {artifact_name}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Confirmed Change Summary",
            "",
        ]
    )
    pending_change_ids = list(preview.get("pending_change_ids", []))
    fields_affected = list(preview.get("fields_affected", []))
    decision_paths = list(preview.get("decision_paths", []))
    for index, change_id in enumerate(pending_change_ids):
        field = fields_affected[index] if index < len(fields_affected) else "UNKNOWN"
        path = decision_paths[index] if index < len(decision_paths) else ""
        lines.append(f"- change_id: `{change_id}`")
        lines.append(f"- field: `{field}`")
        lines.append(f"- decision_record: `{Path(path).name}`")

    lines.extend(
        [
            "",
            "## Revised Sections",
            "",
        ]
    )
    for section in preview.get("revised_sections", []):
        lines.append(f"### {section.get('section_title', '')}")
        lines.append("")
        lines.append(f"- change_id: `{section.get('change_id', '')}`")
        lines.append(f"- field: `{section.get('field', '')}`")
        lines.append("- before:")
        before_lines = str(section.get("before_section", "")).splitlines() or ["- TODO/UNKNOWN"]
        for item in before_lines:
            lines.append(f"  {item}")
        lines.append(f"- proposed_value: {section.get('proposed_value', '')}")
        lines.append("- revised_section:")
        for item in str(section.get("after_section", "")).splitlines():
            lines.append(f"  {item}")
        lines.append("")

    lines.extend(
        [
            "## Revised Scope Preview",
            "",
            "```md",
            preview.get("revised_scope_text", "").rstrip(),
            "```",
            "",
            "## Generated From",
            "",
            "- product.yaml",
            "- scope_lock.md",
        ]
    )
    for path in decision_paths:
        lines.append(f"- decisions/{Path(path).name}")
    lines.extend(
        [
            "",
            "## Next Step",
            "",
            "- Future ws product-scope-revision --confirm",
            f"- Preview command used: `{SCOPE_REVISION_DRY_RUN_ACTION} --product <product_id>`",
            "",
        ]
    )
    return "\n".join(lines)


def next_scope_revision_number(root: str | Path, product_id: str) -> int:
    product_record = get_product_status(root, product_id)
    active_revision = product_record.get("active_scope_revision")
    if isinstance(active_revision, int) and active_revision > 0:
        return active_revision + 1
    if isinstance(active_revision, str) and active_revision.isdigit() and int(active_revision) > 0:
        return int(active_revision) + 1
    return 2


def revised_scope_lock_path(root: str | Path, product_id: str, revision_number: int) -> Path:
    if revision_number < 2:
        raise ValueError(f"revision_number must be >= 2, found {revision_number}")
    pdir = product_dir(root, product_id)
    return _safe_child(pdir, pdir / SCOPE_LOCKS_DIR / f"scope_lock_v{revision_number}.md")


def compute_revised_scope_hash(scope_text: str) -> str:
    if not isinstance(scope_text, str) or not scope_text.strip():
        raise ValueError("revised scope text must be a non-empty string")
    canonical = _canonicalize_text(scope_text)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _extract_scope_body(scope_text: str) -> str:
    canonical = _canonicalize_text(scope_text)
    lines = canonical.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[2:] if len(lines) > 1 and lines[1] == "" else lines[1:]
    return _canonicalize_text("\n".join(lines))


def render_scope_revision_record(
    product_record: dict[str, Any],
    revision_path: Path,
    revision_hash: str,
    changes: list[dict[str, str]],
    *,
    revision_number: int,
    revised_at: str,
    previous_scope_lock: str,
    previous_scope_lock_hash: str,
    revised_scope_text: str,
) -> str:
    product_id = str(product_record.get("product_id", "")).strip()
    product_type = str(product_record.get("product_type", "")).strip()
    label = str(product_record.get("label", "")).strip() or product_id
    scope_body = _extract_scope_body(revised_scope_text).rstrip()

    lines = [
        f"# Scope Lock Revision v{revision_number}: {label}",
        "",
        f"- product_id: `{product_id}`",
        f"- product_type: `{product_type}`",
        f"- label: {label}",
        f"- revised_at: `{revised_at}`",
        f"- revision_number: `{revision_number}`",
        f"- previous_scope_lock: `{previous_scope_lock}`",
        f"- previous_scope_lock_hash: `{previous_scope_lock_hash}`",
        f"- revision_artifact: `{revision_path}`",
        "- revised_scope_lock_hash: Hash recorded in product.yaml",
        "- models/providers/agents: none",
        "",
        "## Applied Change Decision Records",
        "",
    ]
    for change in changes:
        lines.append(f"- decisions/{Path(str(change.get('decision_path', ''))).name}")

    lines.extend(
        [
            "",
            "## Changed Sections Summary",
            "",
        ]
    )
    for change in changes:
        lines.append(f"### {change.get('section_title', '')}")
        lines.append("")
        lines.append(f"- change_id: `{change.get('change_id', '')}`")
        lines.append(f"- field: `{change.get('field', '')}`")
        lines.append("- previous_section:")
        before_lines = str(change.get("before_section", "")).splitlines() or ["- TODO/UNKNOWN"]
        for item in before_lines:
            lines.append(f"  {item}")
        lines.append("- revised_section:")
        after_lines = str(change.get("after_section", "")).splitlines() or ["- TODO/UNKNOWN"]
        for item in after_lines:
            lines.append(f"  {item}")
        lines.append("")

    lines.extend(
        [
            "## Revised Scope Content",
            "",
            scope_body,
            "",
            "## Generated From",
            "",
            "- product.yaml",
            "- scope_lock.md",
        ]
    )
    for change in changes:
        lines.append(f"- decisions/{Path(str(change.get('decision_path', ''))).name}")
    lines.extend(
        [
            "",
            "## Operator Confirmation",
            "",
            "I confirm this revised scope supersedes the previous active scope for downstream planning. Historical scope locks remain immutable.",
            "",
            "This scope revision does not run agents, models, providers, browser automation, or cloud handoffs.",
            "",
        ]
    )
    record = _canonicalize_text("\n".join(lines))
    if revision_hash and compute_revised_scope_hash(record) != revision_hash:
        raise ValueError("revised scope hash mismatch while rendering revision artifact")
    return record


def confirm_scope_revision(root: str | Path, product_id: str, *, confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise PermissionError("confirm_scope_revision requires explicit confirm=True")
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")

    payload = load_scope_revision_inputs(root, product_id)
    product_record = payload["product_record"]
    scope_lock_text = payload["scope_lock_text"]
    changes = payload["changes"]
    paths = payload["paths"]
    product_dir_path = Path(paths["product_dir"]).resolve()

    preview = render_revised_scope_preview(product_record, scope_lock_text, changes)
    revision_number = next_scope_revision_number(root, product_id)
    revision_path = revised_scope_lock_path(root, product_id, revision_number)
    if revision_path.exists():
        raise FileExistsError(f"revised scope lock already exists: {revision_path}")

    previous_scope_lock = str(product_record.get("active_scope_lock", "")).strip() or SCOPE_LOCK_FILENAME
    previous_scope_lock_hash = (
        str(product_record.get("active_scope_lock_hash", "")).strip()
        or str(product_record.get("scope_lock_hash", "")).strip()
        or "UNSET"
    )
    revised_at = _utc_now_iso()

    provisional_text = render_scope_revision_record(
        product_record,
        revision_path,
        "",
        preview["revised_sections"],
        revision_number=revision_number,
        revised_at=revised_at,
        previous_scope_lock=previous_scope_lock,
        previous_scope_lock_hash=previous_scope_lock_hash,
        revised_scope_text=str(preview.get("revised_scope_text", "")),
    )
    revision_hash = compute_revised_scope_hash(provisional_text)
    revision_text = render_scope_revision_record(
        product_record,
        revision_path,
        revision_hash,
        preview["revised_sections"],
        revision_number=revision_number,
        revised_at=revised_at,
        previous_scope_lock=previous_scope_lock,
        previous_scope_lock_hash=previous_scope_lock_hash,
        revised_scope_text=str(preview.get("revised_scope_text", "")),
    )

    scope_locks_dir = _safe_child(product_dir_path, revision_path.parent)
    scope_locks_dir.mkdir(parents=True, exist_ok=True)
    revision_path.write_text(revision_text, encoding="utf-8", newline="\n")

    updated_record = dict(product_record)
    updated_record["active_scope_lock"] = str(Path(SCOPE_LOCKS_DIR) / revision_path.name).replace("\\", "/")
    updated_record["active_scope_lock_hash"] = revision_hash
    updated_record["active_scope_revision"] = revision_number
    updated_record["previous_scope_lock"] = previous_scope_lock
    updated_record["previous_scope_lock_hash"] = previous_scope_lock_hash
    updated_record["scope_revision_count"] = max(revision_number - 1, 1)
    updated_record["scope_change_pending"] = False
    updated_record["last_scope_revision_at"] = revised_at
    updated_record["last_action"] = SCOPE_REVISION_CONFIRM_ACTION
    updated_record["updated_at"] = revised_at

    stale_artifacts = list(updated_record.get("stale_artifacts", []) or [])
    if Path(paths["prd_md"]).is_file() and "prd.md" not in stale_artifacts:
        stale_artifacts.append("prd.md")
    updated_record["stale_artifacts"] = stale_artifacts
    if Path(paths["prd_md"]).is_file():
        updated_record["prd_status"] = "NEEDS_REVISION"

    product_file = save_product(updated_record, root, confirm=True, allow_overwrite=True)
    _append_action_log(
        Path(paths["action_log"]),
        timestamp=revised_at,
        message=(
            f"scope revision recorded via {SCOPE_REVISION_CONFIRM_ACTION} "
            f"(active_scope_lock={updated_record['active_scope_lock']}, revision={revision_number})"
        ),
    )

    files_written = [str(revision_path), str(product_file)]
    action_log_path = Path(paths["action_log"])
    if action_log_path.is_file():
        files_written.append(str(action_log_path))

    return {
        "product_id": product_id,
        "revision_path": str(revision_path),
        "product_file": str(product_file),
        "action_log_path": str(action_log_path),
        "files_written": files_written,
        "active_scope_lock": updated_record["active_scope_lock"],
        "active_scope_lock_hash": revision_hash,
        "active_scope_revision": revision_number,
        "previous_scope_lock": previous_scope_lock,
        "previous_scope_lock_hash": previous_scope_lock_hash,
        "scope_change_pending": False,
        "prd_status": updated_record.get("prd_status"),
        "stale_artifacts": stale_artifacts,
        "state_before": str(product_record.get("state", "")).strip(),
        "state_after": str(updated_record.get("state", "")).strip(),
        "last_scope_revision_at": revised_at,
        "used_model_provider_agent": False,
    }
