#!/usr/bin/env python3
"""PURE_READ Product Lane PRD status helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from product_prd import PRD_FILENAME
from product_registry import get_product_status, product_dir, validate_product_id
from product_scope_lock import SCOPE_LOCK_FILENAME, compute_scope_lock_hash


SCOPE_LOCKED_STATE = "SCOPE_LOCKED"
APPROVAL_DIR = "decisions"
APPROVAL_FILENAME = "prd_approval.md"
UI_PRODUCT_TYPES = {"website", "webapp", "dashboard"}


def _safe_child(base: Path, child: Path) -> Path:
    base_resolved = base.resolve()
    child_resolved = child.resolve()
    if child_resolved == base_resolved:
        return child_resolved
    if base_resolved not in child_resolved.parents:
        raise ValueError(f"path escapes expected base: {child_resolved} not under {base_resolved}")
    return child_resolved


def _derived_prd_status(record: dict[str, Any], *, prd_exists: bool) -> str:
    raw_status = str(record.get("prd_status", "")).strip().upper()
    if not prd_exists:
        return "NOT_CREATED"
    if raw_status:
        return raw_status
    return "DRAFTED"


def _next_suggested_command(
    *,
    product_id: str,
    prd_status_display: str,
    product_type: str,
    scope_change_pending: bool,
    active_scope_lock_exists: bool,
    current_prd_stale: bool,
    wireframe_status: str | None = None,
) -> str:
    if scope_change_pending:
        return f"ws product-scope-revision --product {product_id} --dry-run"
    if prd_status_display == "NOT_CREATED":
        return f"ws product-prd --product {product_id} --dry-run"
    if prd_status_display in {"DRAFTED", "REVIEWED", "NEEDS_CHANGES"}:
        return f"ws product-prd-review --product {product_id} --dry-run"
    if prd_status_display in {"NEEDS_REVISION", "STALE"}:
        if active_scope_lock_exists:
            return f"ws product-prd-revision --product {product_id} --dry-run"
        return f"ws product-scope-revision --product {product_id} --dry-run"
    if prd_status_display == "APPROVED":
        if current_prd_stale:
            return f"ws product-prd-revision --product {product_id} --dry-run"
        if product_type in UI_PRODUCT_TYPES:
            if not wireframe_status:
                return f"ws product-wireframe --product {product_id} --dry-run"
            if wireframe_status == "DRAFTED":
                return f"ws product-wireframe-review --product {product_id} --dry-run"
            return f"ws product-tech-plan --product {product_id} --dry-run"
        return f"ws product-tech-plan --product {product_id} --dry-run"
    return f"ws product-status {product_id}"


def get_prd_status(root: str | Path, product_id: str) -> dict[str, Any]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")

    record = get_product_status(root, product_id)
    pdir = product_dir(root, product_id)
    prd_path = _safe_child(pdir, pdir / PRD_FILENAME)
    scope_lock_path = _safe_child(pdir, pdir / SCOPE_LOCK_FILENAME)
    
    active_prd_revision = record.get("active_prd_revision")
    approval_filename = f"prd_approval_v{active_prd_revision}.md" if active_prd_revision and active_prd_revision > 1 else APPROVAL_FILENAME
    approval_path = _safe_child(pdir, pdir / APPROVAL_DIR / approval_filename)

    prd_exists = prd_path.is_file()
    scope_lock_exists = scope_lock_path.is_file()
    approval_exists = approval_path.is_file()
    scope_lock_hash = str(record.get("scope_lock_hash", "")).strip()
    scope_lock_hash_exists = bool(scope_lock_hash)
    active_scope_lock = str(record.get("active_scope_lock", "")).strip()
    active_scope_lock_hash = str(record.get("active_scope_lock_hash", "")).strip()
    stale_artifacts = list(record.get("stale_artifacts", []) or [])
    scope_change_pending = bool(record.get("scope_change_pending", False))
    
    active_scope_lock_exists = False
    active_scope_hash_status = "UNSET"
    if active_scope_lock:
        active_scope_path = _safe_child(pdir, pdir / active_scope_lock)
        active_scope_lock_exists = active_scope_path.is_file()
        if active_scope_lock_exists and active_scope_lock_hash:
            actual_scope_hash = compute_scope_lock_hash(active_scope_path.read_text(encoding="utf-8"))
            active_scope_hash_status = "MATCH" if actual_scope_hash == active_scope_lock_hash else "MISMATCH"

    active_prd = str(record.get("active_prd", "")).strip()
    active_prd_hash = str(record.get("active_prd_hash", "")).strip()
    active_prd_exists = False
    active_prd_hash_status = "UNSET"
    if active_prd:
        active_prd_path = _safe_child(pdir, pdir / active_prd)
        active_prd_exists = active_prd_path.is_file()
        if active_prd_exists and active_prd_hash:
            actual_prd_hash = hashlib.sha256(active_prd_path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
            active_prd_hash_status = "MATCH" if actual_prd_hash == active_prd_hash else "MISMATCH"

    product_type = str(record.get("product_type", "")).strip()
    prd_status_display = _derived_prd_status(record, prd_exists=prd_exists or active_prd_exists)
    
    current_prd_stale = "prd.md" in stale_artifacts or prd_status_display in {"NEEDS_REVISION", "STALE"}
    if active_prd_exists and active_prd_hash_status == "MATCH" and active_scope_hash_status != "MISMATCH":
        current_prd_stale = False

    active_wireframe = str(record.get("active_wireframe", "")).strip()
    active_wireframe_hash = str(record.get("active_wireframe_hash", "")).strip()
    wireframe_status = str(record.get("wireframe_status", "")).strip() or None
    active_wireframe_exists = False
    active_wireframe_hash_status = "UNSET"
    if active_wireframe:
        active_wf_path = _safe_child(pdir, pdir / active_wireframe)
        active_wireframe_exists = active_wf_path.is_file()
        if active_wireframe_exists and active_wireframe_hash:
            actual_wf_hash = hashlib.sha256(active_wf_path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
            active_wireframe_hash_status = "MATCH" if actual_wf_hash == active_wireframe_hash else "MISMATCH"

    return {
        "product_id": str(record.get("product_id", "")).strip(),
        "product_type": product_type,
        "label": str(record.get("label", "")).strip(),
        "product_state": str(record.get("state", "")).strip(),
        "scope_locked_state": str(record.get("state", "")).strip() == SCOPE_LOCKED_STATE,
        "prd_status": str(record.get("prd_status", "")).strip() or None,
        "prd_status_display": prd_status_display,
        "prd_created_at": record.get("prd_created_at"),
        "prd_reviewed_at": record.get("prd_reviewed_at"),
        "prd_approved_at": record.get("prd_approved_at"),
        "prd_review_notes": str(record.get("prd_review_notes", "")).strip(),
        "prd_exists": prd_exists or active_prd_exists,
        "scope_lock_exists": scope_lock_exists,
        "scope_lock_hash_exists": scope_lock_hash_exists,
        "scope_lock_hash": scope_lock_hash or None,
        "active_scope_lock": active_scope_lock or None,
        "active_scope_lock_exists": active_scope_lock_exists,
        "active_scope_lock_hash": active_scope_lock_hash or None,
        "active_scope_hash_status": active_scope_hash_status,
        "active_scope_revision": record.get("active_scope_revision"),
        "scope_change_pending": scope_change_pending,
        "stale_artifacts": stale_artifacts,
        "current_prd_stale": current_prd_stale,
        "original_prd_path": PRD_FILENAME if prd_exists else None,
        "active_prd": (active_prd or PRD_FILENAME) if (prd_exists or active_prd_exists) else None,
        "active_prd_exists": active_prd_exists,
        "active_prd_hash": active_prd_hash or None,
        "active_prd_hash_status": active_prd_hash_status,
        "active_prd_revision": active_prd_revision,
        "prd_approval_exists": approval_exists,
        "prd_approval_path": str(approval_path),
        "active_wireframe": active_wireframe or None,
        "active_wireframe_exists": active_wireframe_exists,
        "active_wireframe_hash_status": active_wireframe_hash_status,
        "wireframe_status": wireframe_status,
        "next_suggested_command": _next_suggested_command(
            product_id=product_id,
            prd_status_display=prd_status_display,
            product_type=product_type,
            scope_change_pending=scope_change_pending,
            active_scope_lock_exists=active_scope_lock_exists,
            current_prd_stale=current_prd_stale,
            wireframe_status=wireframe_status,
        ),
        "pure_read": True,
        "uses_model_provider_agent": False,
    }


def render_prd_status(status_record: dict[str, Any]) -> str:
    lines = [
        "Product PRD Status",
        "==================",
        "",
        "PURE_READ - no files written.",
        "No product state changes.",
        "No model/provider/agent calls.",
        "",
        f"- product_id: {status_record.get('product_id', '')}",
        f"- product_type: {status_record.get('product_type', '')}",
        f"- label: {status_record.get('label', '')}",
        f"- product_state: {status_record.get('product_state', '')}",
        f"- prd_status_display: {status_record.get('prd_status_display', '')}",
        f"- prd_status(raw): {status_record.get('prd_status') or 'UNSET'}",
        f"- prd_created_at: {status_record.get('prd_created_at') or 'UNSET'}",
        f"- prd_reviewed_at: {status_record.get('prd_reviewed_at') or 'UNSET'}",
        f"- prd_approved_at: {status_record.get('prd_approved_at') or 'UNSET'}",
        f"- prd_review_notes: {status_record.get('prd_review_notes') or 'UNSET'}",
        "",
        "Wireframe Status:",
        f"- active_wireframe: {status_record.get('active_wireframe') or 'UNSET'}",
        f"- active_wireframe_exists: {status_record.get('active_wireframe_exists')}",
        f"- active_wireframe_hash_status: {status_record.get('active_wireframe_hash_status')}",
        f"- wireframe_status: {status_record.get('wireframe_status') or 'UNSET'}",
        "",
        "Artifacts:",
        f"- prd.md exists: {status_record.get('prd_exists')}",
        f"- original_prd_path: {status_record.get('original_prd_path') or 'UNSET'}",
        f"- active_prd: {status_record.get('active_prd') or 'UNSET'}",
        f"- active_prd_exists: {status_record.get('active_prd_exists')}",
        f"- active_prd_hash: {status_record.get('active_prd_hash') or 'UNSET'}",
        f"- active_prd_hash_status: {status_record.get('active_prd_hash_status')}",
        f"- active_prd_revision: {status_record.get('active_prd_revision') if status_record.get('active_prd_revision') is not None else 'UNSET'}",
        f"- scope_lock.md exists: {status_record.get('scope_lock_exists')}",
        f"- scope_lock_hash exists: {status_record.get('scope_lock_hash_exists')}",
        f"- active_scope_lock: {status_record.get('active_scope_lock') or 'UNSET'}",
        f"- active_scope_lock exists: {status_record.get('active_scope_lock_exists')}",
        f"- active_scope_lock_hash: {status_record.get('active_scope_lock_hash') or 'UNSET'}",
        f"- active_scope_hash_status: {status_record.get('active_scope_hash_status')}",
        f"- active_scope_revision: {status_record.get('active_scope_revision') if status_record.get('active_scope_revision') is not None else 'UNSET'}",
        f"- scope_change_pending: {status_record.get('scope_change_pending')}",
        f"- stale_artifacts: {status_record.get('stale_artifacts') or []}",
        f"- current_prd_stale: {status_record.get('current_prd_stale')}",
        f"- decisions/{Path(status_record.get('prd_approval_path', '')).name} exists: {status_record.get('prd_approval_exists')}",
        "",
        f"Next suggested command: {status_record.get('next_suggested_command', '')}",
    ]
    return "\n".join(lines)
