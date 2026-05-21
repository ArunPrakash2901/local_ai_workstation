#!/usr/bin/env python3
"""PURE_READ Product Lane PRD status helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from product_prd import PRD_FILENAME
from product_registry import get_product_status, product_dir, validate_product_id
from product_scope_lock import SCOPE_LOCK_FILENAME


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


def _next_suggested_command(*, product_id: str, prd_status_display: str, product_type: str) -> str:
    if prd_status_display == "NOT_CREATED":
        return f"ws product-prd --product {product_id} --dry-run"
    if prd_status_display in {"DRAFTED", "REVIEWED", "NEEDS_CHANGES"}:
        return f"ws product-prd-review --product {product_id} --dry-run"
    if prd_status_display in {"NEEDS_REVISION", "STALE"}:
        return f"future ws product-scope-revision --product {product_id} --dry-run"
    if prd_status_display == "APPROVED":
        if product_type in UI_PRODUCT_TYPES:
            return f"ws product-wireframe --product {product_id} --dry-run"
        return "future ws product-tech-plan --dry-run"
    return f"ws product-status {product_id}"


def get_prd_status(root: str | Path, product_id: str) -> dict[str, Any]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")

    record = get_product_status(root, product_id)
    pdir = product_dir(root, product_id)
    prd_path = _safe_child(pdir, pdir / PRD_FILENAME)
    scope_lock_path = _safe_child(pdir, pdir / SCOPE_LOCK_FILENAME)
    approval_path = _safe_child(pdir, pdir / APPROVAL_DIR / APPROVAL_FILENAME)

    prd_exists = prd_path.is_file()
    scope_lock_exists = scope_lock_path.is_file()
    approval_exists = approval_path.is_file()
    scope_lock_hash = str(record.get("scope_lock_hash", "")).strip()
    scope_lock_hash_exists = bool(scope_lock_hash)

    product_type = str(record.get("product_type", "")).strip()
    prd_status_display = _derived_prd_status(record, prd_exists=prd_exists)

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
        "prd_exists": prd_exists,
        "scope_lock_exists": scope_lock_exists,
        "scope_lock_hash_exists": scope_lock_hash_exists,
        "scope_lock_hash": scope_lock_hash or None,
        "prd_approval_exists": approval_exists,
        "prd_approval_path": str(approval_path),
        "next_suggested_command": _next_suggested_command(
            product_id=product_id,
            prd_status_display=prd_status_display,
            product_type=product_type,
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
        "Artifacts:",
        f"- prd.md exists: {status_record.get('prd_exists')}",
        f"- scope_lock.md exists: {status_record.get('scope_lock_exists')}",
        f"- scope_lock_hash exists: {status_record.get('scope_lock_hash_exists')}",
        f"- decisions/prd_approval.md exists: {status_record.get('prd_approval_exists')}",
        "",
        f"Next suggested command: {status_record.get('next_suggested_command', '')}",
    ]
    return "\n".join(lines)
