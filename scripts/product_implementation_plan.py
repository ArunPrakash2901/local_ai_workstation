#!/usr/bin/env python3
"""Deterministic no-write Product Lane implementation plan gate preview helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from product_registry import get_product_status, product_dir, save_product, validate_product_id
from product_scope_lock import compute_scope_lock_hash
from product_tech_plan import APPROVED_STATUS
from product_tech_plan_review import review_tech_plan_text, validate_tech_plan_review_preconditions


IMPLEMENTATION_PLAN_DRY_RUN_ACTION = "ws product-implementation-plan --dry-run"
IMPLEMENTATION_PLAN_CONFIRM_ACTION = "ws product-implementation-plan --confirm"
IMPLEMENTATION_PLANS_DIR = "implementation_plans"
IMPLEMENTATION_PLAN_V1_FILENAME = "implementation_plan_v1.md"

REQUIRED_SECTIONS: tuple[str, ...] = (
    "Implementation Phases",
    "File/Folder Strategy",
    "Component Build Order",
    "Validation Strategy",
    "Test Plan",
    "Deployment Notes",
    "Explicit Non-Goals",
    "Generated From",
)


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


def _sha256_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    canonical = "\n".join(line.rstrip() for line in lines).rstrip("\n") + "\n"
    import hashlib

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _assert_hashed_artifact(
    pdir: Path,
    *,
    relpath: str,
    hash_value: str,
    label: str,
    use_scope_hash: bool = False,
) -> None:
    if not relpath:
        raise ValueError(f"{label} path is missing in product metadata")
    if not hash_value:
        raise ValueError(f"{label} hash is missing in product metadata")
    artifact_path = _safe_child(pdir, pdir / relpath)
    if not artifact_path.is_file():
        raise FileNotFoundError(f"{label} file missing: {relpath}")
    text = artifact_path.read_text(encoding="utf-8")
    actual_hash = compute_scope_lock_hash(text) if use_scope_hash else _sha256_text(text)
    if actual_hash != hash_value:
        raise ValueError(f"{label} hash mismatch")


def load_implementation_plan_inputs(root: str | Path, product_id: str) -> dict[str, Any]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")

    product_record = get_product_status(root, product_id)
    pdir = product_dir(root, product_id)

    prd_status = str(product_record.get("prd_status", "")).strip().upper()
    if prd_status != APPROVED_STATUS:
        raise ValueError(f"implementation plan requires prd_status={APPROVED_STATUS} (found {prd_status or 'UNSET'})")

    _assert_hashed_artifact(
        pdir,
        relpath=str(product_record.get("active_scope_lock", "")).strip(),
        hash_value=str(product_record.get("active_scope_lock_hash", "")).strip(),
        label="active_scope_lock",
        use_scope_hash=True,
    )
    _assert_hashed_artifact(
        pdir,
        relpath=str(product_record.get("active_prd", "")).strip(),
        hash_value=str(product_record.get("active_prd_hash", "")).strip(),
        label="active_prd",
    )
    _assert_hashed_artifact(
        pdir,
        relpath=str(product_record.get("active_wireframe", "")).strip(),
        hash_value=str(product_record.get("active_wireframe_hash", "")).strip(),
        label="active_wireframe",
    )
    _assert_hashed_artifact(
        pdir,
        relpath=str(product_record.get("active_technical_plan", "")).strip(),
        hash_value=str(product_record.get("active_technical_plan_hash", "")).strip(),
        label="active_technical_plan",
    )

    review_payload = validate_tech_plan_review_preconditions(root, product_id)
    review_result = review_tech_plan_text(
        review_payload["product_record"],
        review_payload["tech_plan_text"],
        payload_extras=review_payload,
    )
    if review_result["status"] != "PASS":
        raise ValueError(
            "implementation plan requires technical plan review PASS "
            f"(found {review_result['status']})"
        )

    return {
        "product_record": product_record,
        "product_dir": pdir,
        "review_result": review_result,
        "active_scope_lock": str(product_record.get("active_scope_lock", "")).strip(),
        "active_scope_lock_hash": str(product_record.get("active_scope_lock_hash", "")).strip(),
        "active_prd": str(product_record.get("active_prd", "")).strip(),
        "active_prd_hash": str(product_record.get("active_prd_hash", "")).strip(),
        "active_wireframe": str(product_record.get("active_wireframe", "")).strip(),
        "active_wireframe_hash": str(product_record.get("active_wireframe_hash", "")).strip(),
        "active_technical_plan": str(product_record.get("active_technical_plan", "")).strip(),
        "active_technical_plan_hash": str(product_record.get("active_technical_plan_hash", "")).strip(),
    }


def render_implementation_plan_preview(payload: dict[str, Any]) -> str:
    product_record = payload["product_record"]
    product_id = str(product_record.get("product_id", "")).strip()
    label = str(product_record.get("label", "")).strip() or product_id
    lines = [
        "Implementation Plan Preview",
        "===========================",
        "",
        "DRY RUN - no files written.",
        "No product state changes.",
        "No model/provider/agent calls.",
        "",
        "Product Metadata:",
        f"- product_id: `{product_id}`",
        f"- label: {label}",
        f"- product_type: `{product_record.get('product_type', '')}`",
        f"- prd_status: `{product_record.get('prd_status', '')}`",
        "",
        "Source Artifact Summary:",
        f"- active_scope_lock: `{payload['active_scope_lock']}` ({payload['active_scope_lock_hash']})",
        f"- active_prd: `{payload['active_prd']}` ({payload['active_prd_hash']})",
        f"- active_wireframe: `{payload['active_wireframe']}` ({payload['active_wireframe_hash']})",
        f"- active_technical_plan: `{payload['active_technical_plan']}` ({payload['active_technical_plan_hash']})",
        "",
        "Implementation Readiness Gate:",
        f"- technical_plan_review_status: `{payload['review_result']['status']}`",
        "",
        "Proposed Artifact Path:",
        f"- {IMPLEMENTATION_PLANS_DIR}/{IMPLEMENTATION_PLAN_V1_FILENAME}",
        "",
        "Proposed Sections:",
        *[f"- {section.lower()}" for section in REQUIRED_SECTIONS],
        "",
        "Blockers/Warnings:",
        "- none",
        "",
        "Next Step:",
        f"- future {IMPLEMENTATION_PLAN_CONFIRM_ACTION}",
        f"- Preview command used: `{IMPLEMENTATION_PLAN_DRY_RUN_ACTION} --product <product_id>`",
    ]
    return "\n".join(lines)


def write_implementation_plan(root: str | Path, product_id: str, *, confirm: bool) -> str:
    if not confirm:
        raise PermissionError("write_implementation_plan requires explicit confirm=True")

    payload = load_implementation_plan_inputs(root, product_id)
    product_record = payload["product_record"]
    pdir = payload["product_dir"]
    plan_dir = _safe_child(pdir, pdir / IMPLEMENTATION_PLANS_DIR)
    plan_path = _safe_child(plan_dir, plan_dir / IMPLEMENTATION_PLAN_V1_FILENAME)

    if plan_path.exists():
        raise FileExistsError(f"implementation plan already exists: {plan_path.relative_to(root)}")

    now = _utc_now_iso()
    label = str(product_record.get("label", "")).strip() or product_id
    product_type = str(product_record.get("product_type", "")).strip()

    lines = [
        "# Implementation Plan v1",
        "",
        f"- product_id: `{product_id}`",
        f"- product_type: `{product_type}`",
        f"- title: {label}",
        f"- generated_at: {now}",
        "",
        "## Source Artifacts",
        f"- active_scope_lock: `{payload['active_scope_lock']}` ({payload['active_scope_lock_hash']})",
        f"- active_prd: `{payload['active_prd']}` ({payload['active_prd_hash']})",
        f"- active_wireframe: `{payload['active_wireframe']}` ({payload['active_wireframe_hash']})",
        f"- active_technical_plan: `{payload['active_technical_plan']}` ({payload['active_technical_plan_hash']})",
        "",
        "## Implementation Phases",
        "TODO/UNKNOWN: Define phases based on technical plan.",
        "",
        "## File/Folder Strategy",
        "TODO/UNKNOWN: Define file/folder strategy.",
        "",
        "## Component Build Order",
        "TODO/UNKNOWN: Define component build order.",
        "",
        "## Validation Strategy",
        "TODO/UNKNOWN: Define validation strategy.",
        "",
        "## Test Plan",
        "TODO/UNKNOWN: Define test plan.",
        "",
        "## Deployment Notes",
        "TODO/UNKNOWN: Define deployment notes.",
        "",
        "## Explicit Non-Goals",
        "TODO/UNKNOWN: Define explicit non-goals.",
        "",
        "## Generated From",
        "- product.yaml",
        f"- {payload['active_scope_lock']}",
        f"- {payload['active_prd']}",
        f"- {payload['active_wireframe']}",
        f"- {payload['active_technical_plan']}",
        "",
        "---",
        "This is a deterministic workstation planning artifact.",
        "The hash of this file is recorded in product.yaml.",
    ]
    content = "\n".join(lines) + "\n"
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(content, encoding="utf-8")

    plan_hash = _sha256_text(content)
    product_record["active_implementation_plan"] = f"{IMPLEMENTATION_PLANS_DIR}/{IMPLEMENTATION_PLAN_V1_FILENAME}"
    product_record["active_implementation_plan_hash"] = plan_hash
    product_record["active_implementation_plan_revision"] = 1
    product_record["implementation_plan_status"] = "DRAFTED"
    product_record["implementation_plan_created_at"] = now
    product_record["implementation_plan_reviewed_at"] = None
    product_record["implementation_plan_approved_at"] = None
    product_record["last_action"] = IMPLEMENTATION_PLAN_CONFIRM_ACTION
    product_record["updated_at"] = now

    save_product(product_record, root, confirm=True, allow_overwrite=True)

    log_path = pdir / "action_log.md"
    if log_path.is_file():
        log_content = log_path.read_text(encoding="utf-8")
        log_path.write_text(
            log_content.rstrip() + f"\n- {now} {IMPLEMENTATION_PLAN_CONFIRM_ACTION}\n",
            encoding="utf-8",
        )

    return f"CREATED: {plan_path.relative_to(root)}\nUPDATED: product.yaml"
