#!/usr/bin/env python3
"""Deterministic Product Lane PRD revision helpers."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from product_prd import PRD_FILENAME, SCOPE_LOCKED_STATE, render_prd_preview
from product_registry import ACTION_LOG_FILENAME, get_product_status, product_dir, save_product, validate_product_id
from product_scope_lock import SCOPE_LOCK_FILENAME, compute_scope_lock_hash


PRD_REVISION_DRY_RUN_ACTION = "ws product-prd-revision --dry-run"
PRD_REVISION_CONFIRM_ACTION = "ws product-prd-revision --confirm"
PRD_REVISIONS_DIR = "prds"
PRD_REVISION_FILENAME = "prd_v2.md"


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


def _select_active_scope_path(product_record: dict[str, Any], pdir: Path) -> Path:
    active_scope_lock = str(product_record.get("active_scope_lock", "")).strip()
    if active_scope_lock:
        return _safe_child(pdir, pdir / active_scope_lock)
    return _safe_child(pdir, pdir / SCOPE_LOCK_FILENAME)


def _require_revision_state(product_record: dict[str, Any], *, prd_exists: bool) -> None:
    if not prd_exists:
        return
    raw_status = str(product_record.get("prd_status", "")).strip().upper()
    if raw_status not in {"NEEDS_REVISION", "STALE"}:
        raise ValueError(
            "prd_status must be NEEDS_REVISION or STALE to preview PRD revision when prd.md exists"
        )


def load_prd_revision_inputs(root: str | Path, product_id: str) -> dict[str, Any]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")

    product_record = get_product_status(root, product_id)
    pdir = product_dir(root, product_id)
    prd_path = _safe_child(pdir, pdir / PRD_FILENAME)
    prd_exists = prd_path.is_file()
    _require_revision_state(product_record, prd_exists=prd_exists)

    active_scope_path = _select_active_scope_path(product_record, pdir)
    if not active_scope_path.is_file():
        raise FileNotFoundError(f"active scope lock file not found: {active_scope_path}")
    active_scope_text = active_scope_path.read_text(encoding="utf-8")
    active_scope_hash_actual = compute_scope_lock_hash(active_scope_text)

    active_scope_hash_recorded = str(product_record.get("active_scope_lock_hash", "")).strip()
    if str(product_record.get("active_scope_lock", "")).strip() and active_scope_hash_recorded:
        if active_scope_hash_recorded != active_scope_hash_actual:
            raise ValueError("active_scope_lock hash mismatch with product.yaml")

    current_state = str(product_record.get("state", "")).strip() or "UNKNOWN"
    if current_state != SCOPE_LOCKED_STATE:
        raise ValueError(
            f"product must be in {SCOPE_LOCKED_STATE} for PRD revision preview (found {current_state})"
        )

    stale_artifacts = list(product_record.get("stale_artifacts", []) or [])
    proposed_prd_path = _safe_child(pdir, pdir / PRD_REVISIONS_DIR / PRD_REVISION_FILENAME)
    source_scope_rel = (
        str(product_record.get("active_scope_lock", "")).strip() or SCOPE_LOCK_FILENAME
    )

    return {
        "product_record": product_record,
        "active_scope_path": active_scope_path,
        "active_scope_text": active_scope_text,
        "active_scope_hash": active_scope_hash_recorded or active_scope_hash_actual,
        "source_scope_relpath": source_scope_rel,
        "prd_exists": prd_exists,
        "prd_path": prd_path,
        "proposed_prd_path": proposed_prd_path,
        "stale_artifacts": stale_artifacts,
        "product_dir": pdir,
    }


def render_prd_revision_dry_run(payload: dict[str, Any]) -> str:
    product_record = dict(payload["product_record"])
    product_id = str(product_record.get("product_id", "")).strip()
    label = str(product_record.get("label", "")).strip() or product_id
    active_scope_hash = str(payload["active_scope_hash"]).strip()
    source_scope_relpath = str(payload["source_scope_relpath"]).strip()
    prd_exists = bool(payload["prd_exists"])
    stale_artifacts = list(payload["stale_artifacts"])
    prd_status = str(product_record.get("prd_status", "")).strip() or "UNSET"

    render_record = dict(product_record)
    render_record["scope_lock_hash"] = active_scope_hash
    revised_prd_preview = render_prd_preview(render_record, str(payload["active_scope_text"]))

    lines = [
        f"# PRD Revision Preview: {label}",
        "",
        "DRY RUN - no files written.",
        "No product state changes.",
        "No model/provider/agent calls.",
        "",
        "## Product Metadata",
        "",
        f"- product_id: `{product_id}`",
        f"- product_type: `{product_record.get('product_type', '')}`",
        f"- current_state: `{product_record.get('state', '')}`",
        f"- prd_status: `{prd_status}`",
        "",
        "## Active Scope",
        "",
        f"- active_scope_lock: `{source_scope_relpath}`",
        f"- active_scope_lock_hash: `{active_scope_hash}`",
        "",
        "## PRD Revision Targets",
        "",
        f"- previous_prd_path: `{'prd.md' if prd_exists else 'UNSET'}`",
        f"- proposed_prd_revision_path: `{PRD_REVISIONS_DIR}/{PRD_REVISION_FILENAME}`",
        "",
        "## Stale Artifacts",
        "",
    ]
    if stale_artifacts:
        for artifact in stale_artifacts:
            lines.append(f"- {artifact}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Generated From",
            "",
            "- product.yaml",
            f"- {source_scope_relpath}",
            f"- {'prd.md' if prd_exists else 'previous prd.md not present'}",
            "",
            "## Revised PRD Preview",
            "",
            "```md",
            revised_prd_preview.rstrip(),
            "```",
            "",
            "## Next Step",
            "",
            f"- Future {PRD_REVISION_CONFIRM_ACTION} --product <product_id>",
            f"- Preview command used: `{PRD_REVISION_DRY_RUN_ACTION} --product <product_id>`",
            "",
        ]
    )
    return "\n".join(lines)


def confirm_prd_revision(root: str | Path, product_id: str, *, confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise PermissionError("confirm_prd_revision requires explicit confirm=True")

    payload = load_prd_revision_inputs(root, product_id)
    product_record = payload["product_record"]
    pdir = payload["product_dir"]
    proposed_prd_path: Path = payload["proposed_prd_path"]

    if proposed_prd_path.exists():
        raise FileExistsError(f"Revised PRD already exists: {proposed_prd_path}")

    proposed_prd_path.parent.mkdir(parents=True, exist_ok=True)

    render_record = dict(product_record)
    render_record["scope_lock_hash"] = payload["active_scope_hash"]
    preview_text = render_prd_preview(render_record, str(payload["active_scope_text"]))

    lines: list[str] = []
    for raw_line in preview_text.splitlines():
        line = raw_line
        if line.startswith("# PRD Preview: "):
            line = line.replace("# PRD Preview: ", "# PRD: ", 1)
        elif line == "DRY RUN - no files written.":
            continue
        elif line == "No product state changes.":
            continue
        elif line == "- Use `ws product-prd --confirm` to write `prd.md` when approved.":
            line = f"- PRD revision written by `{PRD_REVISION_CONFIRM_ACTION}` from active locked scope."
        elif line.startswith("- Preview command used: "):
            line = f"- Written by `{PRD_REVISION_CONFIRM_ACTION}` from active locked scope."
        lines.append(line)

    prd_text = "\n".join(lines).rstrip() + "\n"
    proposed_prd_path.write_text(prd_text, encoding="utf-8", newline="\n")

    prd_hash = hashlib.sha256(prd_text.encode("utf-8")).hexdigest()

    timestamp = _utc_now_iso()
    updated_record = dict(product_record)

    prd_path_rel = f"{PRD_REVISIONS_DIR}/{PRD_REVISION_FILENAME}"
    updated_record["active_prd"] = prd_path_rel
    updated_record["active_prd_hash"] = prd_hash
    updated_record["active_prd_revision"] = 2

    previous_prd_hash = ""
    prd_path_absolute = payload["prd_path"]
    if prd_path_absolute.is_file():
        previous_prd_hash = hashlib.sha256(prd_path_absolute.read_text(encoding="utf-8").encode("utf-8")).hexdigest()

    updated_record["previous_prd"] = PRD_FILENAME
    updated_record["previous_prd_hash"] = previous_prd_hash

    current_rev_count = int(product_record.get("prd_revision_count", 0))
    updated_record["prd_revision_count"] = current_rev_count + 1
    updated_record["prd_status"] = "DRAFTED"
    updated_record["prd_revised_at"] = timestamp
    updated_record["prd_reviewed_at"] = None
    updated_record["prd_approved_at"] = None
    updated_record["last_action"] = PRD_REVISION_CONFIRM_ACTION
    updated_record["updated_at"] = timestamp

    stale_artifacts = list(product_record.get("stale_artifacts", []) or [])
    if PRD_FILENAME in stale_artifacts:
        stale_artifacts.remove(PRD_FILENAME)
    if "historical_stale_artifacts" not in updated_record:
        updated_record["historical_stale_artifacts"] = []
    if PRD_FILENAME not in updated_record["historical_stale_artifacts"]:
        updated_record["historical_stale_artifacts"].append(PRD_FILENAME)

    updated_record["stale_artifacts"] = stale_artifacts

    product_file = save_product(updated_record, root, confirm=True, allow_overwrite=True)

    action_log = _safe_child(pdir, pdir / ACTION_LOG_FILENAME)
    if action_log.is_file():
        with action_log.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"- {timestamp} PRD revised via {PRD_REVISION_CONFIRM_ACTION} (state={product_record.get('state', '')})\n")

    files_written = [str(proposed_prd_path), str(product_file)]
    if action_log.is_file():
        files_written.append(str(action_log))

    return {
        "product_id": product_id,
        "state_before": str(product_record.get("state", "")).strip(),
        "state_after": str(updated_record.get("state", "")).strip(),
        "prd_path": str(proposed_prd_path),
        "product_file": str(product_file),
        "active_prd_hash": prd_hash,
        "prd_revised_at": timestamp,
        "files_written": files_written,
        "used_model_provider_agent": False,
    }
