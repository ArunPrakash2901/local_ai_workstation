#!/usr/bin/env python3
"""Deterministic no-write Product Lane PRD review helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from product_prd import (
    PRD_FILENAME,
    SUPPORTED_PRODUCT_TYPES,
    load_prd_inputs,
)
from product_registry import validate_product_id
from product_scope_lock import SCOPE_LOCK_FILENAME


PRD_REVIEW_ACTION = "ws product-prd-review --dry-run"
PRD_APPROVE_ACTION_FUTURE = "ws product-prd-approve --confirm"
SCOPE_LOCKED_STATE = "SCOPE_LOCKED"
TODO_UNKNOWN_TOKEN = "TODO/UNKNOWN"

REQUIRED_SECTIONS: tuple[str, ...] = (
    "Executive Summary",
    "Problem Statement",
    "Target Users / Audience",
    "Goals",
    "Non-Goals",
    "In Scope",
    "Out of Scope",
    "Requirements",
    "Constraints",
    "Dependencies",
    "Success Criteria",
    "Risks and Mitigations",
    "Acceptance Criteria",
    "Generated From",
    "Next Step",
)

CRITICAL_SECTIONS: tuple[str, ...] = (
    "Executive Summary",
    "Problem Statement",
    "Target Users / Audience",
    "Goals",
    "In Scope",
    "Out of Scope",
    "Requirements",
    "Success Criteria",
    "Acceptance Criteria",
)

SECTION_HEADER_RE = re.compile(r"^##\s+(.*)$")
TODO_PATTERN = re.compile(r"\bTODO/UNKNOWN\b", re.IGNORECASE)


def prd_review_required_sections() -> tuple[str, ...]:
    return REQUIRED_SECTIONS


def _safe_child(base: Path, child: Path) -> Path:
    base_resolved = base.resolve()
    child_resolved = child.resolve()
    if child_resolved == base_resolved:
        return child_resolved
    if base_resolved not in child_resolved.parents:
        raise ValueError(f"path escapes expected base: {child_resolved} not under {base_resolved}")
    return child_resolved


def _extract_sections(prd_text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in prd_text.splitlines():
        stripped = raw_line.strip()
        header = SECTION_HEADER_RE.match(stripped)
        if header:
            current = header.group(1).strip()
            sections.setdefault(current, [])
            continue
        if current is None:
            continue
        sections[current].append(raw_line)
    return sections


def detect_missing_prd_sections(prd_text: str) -> list[str]:
    sections = _extract_sections(prd_text)
    missing: list[str] = []
    for section_name in REQUIRED_SECTIONS:
        if section_name not in sections:
            missing.append(section_name)
    return missing


def detect_critical_todos(prd_text: str) -> list[str]:
    sections = _extract_sections(prd_text)
    flagged: list[str] = []
    for section_name in CRITICAL_SECTIONS:
        content = "\n".join(sections.get(section_name, []))
        if TODO_PATTERN.search(content):
            flagged.append(section_name)
    return flagged


def validate_prd_review_preconditions(root: str | Path, product_id: str) -> dict[str, Any]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")

    payload = load_prd_inputs(root, product_id)
    product_record = payload["product_record"]
    state = str(product_record.get("state", "")).strip()
    if state != SCOPE_LOCKED_STATE:
        raise ValueError(f"product must be in {SCOPE_LOCKED_STATE} for PRD review (found {state or 'UNKNOWN'})")

    product_type = str(product_record.get("product_type", "")).strip()
    if product_type not in SUPPORTED_PRODUCT_TYPES:
        raise ValueError(f"unsupported product_type for PRD review: {product_type or 'UNKNOWN'}")

    paths = payload["paths"]
    product_dir = Path(paths["product_dir"]).resolve()
    prd_path = _safe_child(product_dir, Path(paths["prd_md"]))
    if not prd_path.is_file():
        raise FileNotFoundError(
            "prd.md is missing; run ws product-prd --product <product_id> --confirm first"
        )

    payload["prd_path"] = prd_path
    payload["prd_text"] = prd_path.read_text(encoding="utf-8")
    return payload


def load_prd_review_inputs(root: str | Path, product_id: str) -> dict[str, Any]:
    return validate_prd_review_preconditions(root, product_id)


def review_prd_text(
    product_record: dict[str, Any],
    scope_lock_text: str,
    prd_text: str,
) -> dict[str, Any]:
    del scope_lock_text  # preconditions already verify lock/hash integrity via load_prd_inputs.
    if not isinstance(prd_text, str) or not prd_text.strip():
        raise ValueError("prd text must be a non-empty string")

    product_id = str(product_record.get("product_id", "")).strip()
    product_type = str(product_record.get("product_type", "")).strip()
    current_state = str(product_record.get("state", "")).strip() or "UNKNOWN"
    prd_status = str(product_record.get("prd_status", "")).strip()
    if not prd_status:
        prd_status = "DRAFTED" if str(product_record.get("prd_created_at", "")).strip() else "UNKNOWN"
    scope_lock_hash = str(product_record.get("scope_lock_hash", "")).strip()

    sections = _extract_sections(prd_text)
    required_sections_present = [name for name in REQUIRED_SECTIONS if name in sections]
    missing_sections = detect_missing_prd_sections(prd_text)
    critical_todos = detect_critical_todos(prd_text)

    warnings: list[str] = []
    fail_reasons: list[str] = []

    has_generated_from = "Generated From" in sections
    if not has_generated_from:
        fail_reasons.append("Generated From section is missing.")

    lower_prd = prd_text.lower()
    has_scope_reference = ("scope_lock.md" in lower_prd) or (
        bool(scope_lock_hash) and scope_lock_hash in prd_text
    )
    if not has_scope_reference:
        fail_reasons.append("PRD does not reference scope_lock.md or scope_lock_hash.")

    if missing_sections:
        fail_reasons.append("Missing required sections: " + ", ".join(missing_sections))

    if critical_todos:
        warnings.append(
            "Critical sections contain TODO/UNKNOWN: " + ", ".join(critical_todos)
        )

    if fail_reasons:
        status = "FAIL"
    elif critical_todos:
        status = "WARN"
    else:
        status = "PASS"

    if status == "PASS":
        next_step = f"Future guarded approval: `{PRD_APPROVE_ACTION_FUTURE}`."
    elif status == "WARN":
        next_step = (
            "Resolve critical TODO/UNKNOWN findings, then rerun "
            f"`{PRD_REVIEW_ACTION}` before future approval."
        )
    else:
        next_step = (
            "Fix missing/invalid PRD structure and rerun "
            f"`{PRD_REVIEW_ACTION}` before future approval."
        )

    return {
        "status": status,
        "product_id": product_id,
        "product_type": product_type,
        "current_state": current_state,
        "prd_status": prd_status,
        "scope_lock_hash": scope_lock_hash,
        "required_sections_total": len(REQUIRED_SECTIONS),
        "required_sections_present": required_sections_present,
        "missing_sections": missing_sections,
        "critical_todos": critical_todos,
        "warnings": warnings,
        "fail_reasons": fail_reasons,
        "has_generated_from": has_generated_from,
        "has_scope_reference": has_scope_reference,
        "next_step": next_step,
        "no_write": True,
        "no_model_provider_agent": True,
    }


def render_prd_review_report(
    product_record: dict[str, Any],
    review_result: dict[str, Any],
    *,
    prd_path: str | Path,
) -> str:
    label = str(product_record.get("label", "")).strip() or str(review_result.get("product_id", "")).strip()
    status = str(review_result.get("status", "FAIL")).strip().upper() or "FAIL"
    required_present = set(review_result.get("required_sections_present", []))
    missing_sections = list(review_result.get("missing_sections", []))
    critical_todos = list(review_result.get("critical_todos", []))
    warnings = list(review_result.get("warnings", []))
    fail_reasons = list(review_result.get("fail_reasons", []))

    lines: list[str] = [
        f"# PRD Review Report: {label}",
        "",
        "DRY RUN - no files written.",
        "No product state changes.",
        "No model/provider/agent calls.",
        "",
        f"- status: `{status}`",
        f"- product_id: `{review_result.get('product_id', '')}`",
        f"- product_type: `{review_result.get('product_type', '')}`",
        f"- current_state: `{review_result.get('current_state', '')}`",
        f"- prd_status: `{review_result.get('prd_status', '')}`",
        f"- prd_path: `{Path(prd_path)}`",
        f"- scope_lock_hash: `{review_result.get('scope_lock_hash', '')}`",
        "",
        "## Required Section Checklist",
        "",
    ]

    for section_name in REQUIRED_SECTIONS:
        marker = "PASS" if section_name in required_present else "FAIL"
        lines.append(f"- [{marker}] {section_name}")

    lines.extend(["", "## Structural Findings", ""])
    if missing_sections:
        lines.append("- Missing required sections:")
        for section_name in missing_sections:
            lines.append(f"  - {section_name}")
    else:
        lines.append("- Missing required sections: none")

    lines.append(
        "- Scope reference check: "
        + ("PASS" if bool(review_result.get("has_scope_reference")) else "FAIL")
    )
    lines.append(
        "- Generated From section check: "
        + ("PASS" if bool(review_result.get("has_generated_from")) else "FAIL")
    )

    lines.extend(["", "## Critical TODO/UNKNOWN", ""])
    if critical_todos:
        for section_name in critical_todos:
            lines.append(f"- {section_name}")
    else:
        lines.append("- None")

    lines.extend(["", "## Warnings", ""])
    if warnings:
        for warning in warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- None")

    lines.extend(["", "## Fail Reasons", ""])
    if fail_reasons:
        for reason in fail_reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Next Step",
            "",
            f"- {review_result.get('next_step', '').strip()}",
            f"- Review command used: `{PRD_REVIEW_ACTION} --product <product_id>`",
            "- Approval is not implemented in this slice.",
            "",
        ]
    )
    return "\n".join(lines)

