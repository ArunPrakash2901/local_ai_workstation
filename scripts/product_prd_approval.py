#!/usr/bin/env python3
"""Product Lane Phase 2 Slice 3B PRD approval helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from product_prd import PRD_FILENAME
from product_prd_review import PRD_REVIEW_ACTION, load_prd_review_inputs, review_prd_text
from product_registry import ACTION_LOG_FILENAME, get_product_status, product_dir, save_product, validate_product_id
from product_scope_lock import SCOPE_LOCK_FILENAME


PRD_APPROVE_ACTION = "ws product-prd-approve --confirm"
PRD_APPROVAL_DIR = "decisions"
PRD_APPROVAL_FILENAME = "prd_approval.md"
APPROVED_STATUS = "APPROVED"
SCOPE_LOCKED_STATE = "SCOPE_LOCKED"


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


def _append_action_log(path: Path, *, timestamp: str, message: str) -> None:
    if not path.is_file():
        return
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"- {timestamp} {message}\n")


def prd_approval_path(root: str | Path, product_id: str, revision: int | None = None) -> Path:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")
    pdir = product_dir(root, product_id)
    filename = PRD_APPROVAL_FILENAME
    if revision and revision > 1:
        filename = f"prd_approval_v{revision}.md"
    return _safe_child(pdir, pdir / PRD_APPROVAL_DIR / filename)


def render_prd_approval_record(
    product_record: dict[str, Any],
    review_result: dict[str, Any],
    *,
    approved_at: str,
    prd_path: Path,
) -> str:
    product_id = str(product_record.get("product_id", "")).strip()
    product_type = str(product_record.get("product_type", "")).strip()
    
    active_scope_lock = str(product_record.get("active_scope_lock", "")).strip() or "scope_lock.md"
    active_scope_lock_hash = str(product_record.get("active_scope_lock_hash", "")).strip() or str(product_record.get("scope_lock_hash", "")).strip()
    active_prd = str(product_record.get("active_prd", "")).strip() or "prd.md"
    active_prd_hash = str(product_record.get("active_prd_hash", "")).strip()
    
    required_total = int(review_result.get("required_sections_total", 0))
    required_present = len(list(review_result.get("required_sections_present", [])))
    missing_sections = list(review_result.get("missing_sections", []))
    warnings = list(review_result.get("warnings", []))
    fail_reasons = list(review_result.get("fail_reasons", []))

    lines: list[str] = [
        "# PRD Approval",
        "",
        f"- product_id: `{product_id}`",
        f"- product_type: `{product_type}`",
        f"- prd_path: `{active_prd}`",
        f"- prd_hash: `{active_prd_hash or 'UNSET'}`",
        f"- scope_path: `{active_scope_lock}`",
        f"- scope_hash: `{active_scope_lock_hash}`",
        f"- approved_at: `{approved_at}`",
        f"- approval_status: `{APPROVED_STATUS}`",
        f"- review_status: `{review_result.get('status', '')}`",
        "",
        "## Required Sections Result",
        "",
        f"- required_sections_present: {required_present}/{required_total}",
    ]

    if missing_sections:
        lines.append("- missing_sections:")
        for section_name in missing_sections:
            lines.append(f"  - {section_name}")
    else:
        lines.append("- missing_sections: none")

    if warnings:
        lines.append("- review_warnings:")
        for warning in warnings:
            lines.append(f"  - {warning}")
    else:
        lines.append("- review_warnings: none")

    if fail_reasons:
        lines.append("- review_fail_reasons:")
        for reason in fail_reasons:
            lines.append(f"  - {reason}")
    else:
        lines.append("- review_fail_reasons: none")

    lines.extend(
        [
            "",
            "## Operator Confirmation",
            "",
            "I approve this PRD as the basis for downstream UX, wireframe, technical planning, and build planning.",
            "",
            "## Safety Notes",
            "",
            "- No model/provider/agent calls were used for this approval.",
            "- This approval does not modify prd.md or active PRD files.",
            "- This approval does not modify scope_lock.md or active scope files.",
            "",
            "## Generated From",
            "",
            "- product.yaml",
            f"- {active_scope_lock}",
            f"- {active_prd}",
            "- deterministic product-prd-review",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def validate_prd_approval_preconditions(root: str | Path, product_id: str) -> dict[str, Any]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")

    product_record = get_product_status(root, product_id)
    state = str(product_record.get("state", "")).strip()
    if state != SCOPE_LOCKED_STATE:
        raise ValueError(
            f"product must be in {SCOPE_LOCKED_STATE} for PRD approval (found {state or 'UNKNOWN'})"
        )

    current_prd_status = str(product_record.get("prd_status", "")).strip().upper()
    if current_prd_status in {"NEEDS_REVISION", "STALE"}:
        raise ValueError("PRD status is NEEDS_REVISION or STALE. Please revise PRD before approving.")

    payload = load_prd_review_inputs(root, product_id)
    
    if payload.get("prd_hash_status") == "MISMATCH":
        raise ValueError("active_prd hash mismatch")
    if payload.get("active_scope_hash_status") == "MISMATCH":
        raise ValueError("active_scope_lock hash mismatch")
        
    review_result = review_prd_text(
        payload["product_record"],
        payload["scope_lock_text"],
        payload["prd_text"],
        payload_extras=payload,
    )

    review_status = str(review_result.get("status", "")).strip().upper()
    if review_status != "PASS":
        raise ValueError(f"PRD approval requires deterministic review PASS (found {review_status or 'UNKNOWN'})")

    pdir = Path(payload["paths"]["product_dir"]).resolve() if "paths" in payload else product_dir(root, product_id)
    prd_file = payload["prd_path"]
    scope_lock_file = _safe_child(pdir, pdir / payload.get("active_scope_lock", SCOPE_LOCK_FILENAME))
    
    active_prd_revision = product_record.get("active_prd_revision")
    approval_file = prd_approval_path(root, product_id, active_prd_revision)
    
    action_log = _safe_child(pdir, pdir / ACTION_LOG_FILENAME)

    if not prd_file.is_file():
        raise FileNotFoundError(f"PRD file is required before approval: {prd_file.name}")
    if not scope_lock_file.is_file():
        raise FileNotFoundError(f"scope lock file is required before approval: {scope_lock_file.name}")
    if approval_file.exists():
        raise FileExistsError(f"approval artifact already exists: {approval_file}")

    return {
        "product_record": product_record,
        "product_dir": pdir,
        "prd_file": prd_file,
        "scope_lock_file": scope_lock_file,
        "approval_file": approval_file,
        "action_log": action_log,
        "review_result": review_result,
    }


def approve_prd(root: str | Path, product_id: str, *, confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise PermissionError("approve_prd requires explicit confirm=True")

    payload = validate_prd_approval_preconditions(root, product_id)
    product_record = payload["product_record"]
    approval_file: Path = payload["approval_file"]
    action_log: Path = payload["action_log"]
    review_result = payload["review_result"]

    approval_dir = _safe_child(payload["product_dir"], approval_file.parent)
    approval_dir.mkdir(parents=True, exist_ok=True)

    timestamp = _utc_now_iso()
    approval_text = render_prd_approval_record(
        product_record,
        review_result,
        approved_at=timestamp,
        prd_path=payload["prd_file"],
    )
    approval_file.write_text(approval_text, encoding="utf-8", newline="\n")

    updated_record = dict(product_record)
    updated_record["prd_status"] = APPROVED_STATUS
    updated_record["prd_reviewed_at"] = timestamp
    updated_record["prd_approved_at"] = timestamp
    updated_record["prd_review_notes"] = (
        "Deterministic review PASS via "
        f"{PRD_REVIEW_ACTION}; required_sections={len(review_result.get('required_sections_present', []))}/"
        f"{review_result.get('required_sections_total', 0)}."
    )
    updated_record["updated_at"] = timestamp
    updated_record["last_action"] = PRD_APPROVE_ACTION
    product_file = save_product(updated_record, root, confirm=True, allow_overwrite=True)

    _append_action_log(
        action_log,
        timestamp=timestamp,
        message=(
            f"PRD approved via {PRD_APPROVE_ACTION} "
            f"(state={updated_record.get('state', SCOPE_LOCKED_STATE)}, prd_status={APPROVED_STATUS})"
        ),
    )

    files_written = [str(approval_file), str(product_file)]
    if action_log.is_file():
        files_written.append(str(action_log))

    return {
        "product_id": str(product_record.get("product_id", "")).strip(),
        "state_before": str(product_record.get("state", "")).strip(),
        "state_after": str(updated_record.get("state", "")).strip(),
        "prd_status": APPROVED_STATUS,
        "prd_reviewed_at": timestamp,
        "prd_approved_at": timestamp,
        "approval_path": str(approval_file),
        "product_file": str(product_file),
        "action_log_updated": action_log.is_file(),
        "action_log_path": str(action_log),
        "files_written": files_written,
        "used_model_provider_agent": False,
    }
