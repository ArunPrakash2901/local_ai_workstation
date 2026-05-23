#!/usr/bin/env python3
"""Deterministic no-write Product Lane wireframe review helpers."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from product_registry import get_product_status, product_dir, validate_product_id
from product_scope_lock import compute_scope_lock_hash


WIREFRAME_REVIEW_ACTION = "ws product-wireframe-review --dry-run"
APPROVED_STATUS = "APPROVED"
TODO_UNKNOWN_TOKEN = "TODO/UNKNOWN"

REQUIRED_SECTIONS: tuple[str, ...] = (
    "Page/Screen Map",
    "ASCII/Text Wireframes",
    "Component Inventory",
    "Navigation Model",
    "Content Hierarchy",
    "Responsive Notes",
    "Accessibility Notes",
    "Generated From",
)

SECTION_HEADER_RE = re.compile(r"^##\s+(.*)$")
# We also check for [Page Name] style headers for wireframes
PAGE_HEADER_RE = re.compile(r"^\[(.*)\]$")
TODO_PATTERN = re.compile(r"\bTODO/UNKNOWN\b", re.IGNORECASE)


def _safe_child(base: Path, child: Path) -> Path:
    base_resolved = base.resolve()
    child_resolved = child.resolve()
    if child_resolved == base_resolved:
        return child_resolved
    if base_resolved not in child_resolved.parents:
        raise ValueError(f"path escapes expected base: {child_resolved} not under {base_resolved}")
    return child_resolved


def _extract_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
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


def detect_missing_sections(text: str) -> list[str]:
    sections = _extract_sections(text)
    missing: list[str] = []
    for section_name in REQUIRED_SECTIONS:
        if section_name not in sections:
            missing.append(section_name)
    return missing


def detect_critical_todos(text: str) -> list[str]:
    sections = _extract_sections(text)
    flagged: list[str] = []
    # All required sections are critical for wireframes
    for section_name in REQUIRED_SECTIONS:
        content = "\n".join(sections.get(section_name, []))
        if TODO_PATTERN.search(content):
            flagged.append(section_name)
    return flagged


def validate_wireframe_review_preconditions(root: str | Path, product_id: str) -> dict[str, Any]:
    product_record = get_product_status(root, product_id)
    pdir = product_dir(root, product_id)

    active_wireframe = str(product_record.get("active_wireframe", "")).strip()
    if not active_wireframe:
        raise ValueError("No active wireframe found in product metadata. Run ws product-wireframe --confirm first.")

    wireframe_path = _safe_child(pdir, pdir / active_wireframe)
    if not wireframe_path.is_file():
        raise FileNotFoundError(f"Active wireframe file missing: {active_wireframe}")

    active_wireframe_hash_expected = str(product_record.get("active_wireframe_hash", "")).strip()
    wireframe_text = wireframe_path.read_text(encoding="utf-8")
    actual_wireframe_hash = hashlib.sha256(wireframe_text.encode("utf-8")).hexdigest()
    
    wireframe_hash_status = "MATCH" if actual_wireframe_hash == active_wireframe_hash_expected else "MISMATCH"
    if not active_wireframe_hash_expected:
        wireframe_hash_status = "UNSET"

    # PRD validation
    prd_status = str(product_record.get("prd_status", "")).strip().upper()
    if prd_status != APPROVED_STATUS:
        raise ValueError(f"Wireframe review requires APPROVED PRD (found {prd_status})")

    active_prd = str(product_record.get("active_prd", "")).strip()
    if not active_prd:
         raise ValueError("No active PRD found in metadata.")
    
    prd_path = _safe_child(pdir, pdir / active_prd)
    active_prd_hash_expected = str(product_record.get("active_prd_hash", "")).strip()
    if not prd_path.is_file():
        raise FileNotFoundError(f"Active PRD file missing: {active_prd}")
    
    actual_prd_hash = hashlib.sha256(prd_path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    prd_hash_status = "MATCH" if actual_prd_hash == active_prd_hash_expected else "MISMATCH"

    # Scope validation
    active_scope_lock = str(product_record.get("active_scope_lock", "")).strip()
    if not active_scope_lock:
        raise ValueError("No active scope lock found in metadata.")
    
    scope_path = _safe_child(pdir, pdir / active_scope_lock)
    active_scope_hash_expected = str(product_record.get("active_scope_lock_hash", "")).strip()
    if not scope_path.is_file():
        raise FileNotFoundError(f"Active scope lock file missing: {active_scope_lock}")
    
    actual_scope_hash = compute_scope_lock_hash(scope_path.read_text(encoding="utf-8"))
    scope_hash_status = "MATCH" if actual_scope_hash == active_scope_hash_expected else "MISMATCH"

    return {
        "product_record": product_record,
        "wireframe_path": wireframe_path,
        "wireframe_text": wireframe_text,
        "wireframe_hash_status": wireframe_hash_status,
        "prd_hash_status": prd_hash_status,
        "scope_hash_status": scope_hash_status,
        "active_prd": active_prd,
        "active_scope_lock": active_scope_lock,
    }


def load_wireframe_review_inputs(root: str | Path, product_id: str) -> dict[str, Any]:
    return validate_wireframe_review_preconditions(root, product_id)


def review_wireframe_text(
    product_record: dict[str, Any],
    wireframe_text: str,
    payload_extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(wireframe_text, str) or not wireframe_text.strip():
        raise ValueError("wireframe text must be a non-empty string")

    payload_extras = payload_extras or {}
    wireframe_hash_status = payload_extras.get("wireframe_hash_status", "UNSET")
    prd_hash_status = payload_extras.get("prd_hash_status", "UNSET")
    scope_hash_status = payload_extras.get("scope_hash_status", "UNSET")
    active_prd = payload_extras.get("active_prd", "UNSET")
    active_scope_lock = payload_extras.get("active_scope_lock", "UNSET")

    product_id = str(product_record.get("product_id", "")).strip()
    
    sections = _extract_sections(wireframe_text)
    missing_sections = detect_missing_sections(wireframe_text)
    critical_todos = detect_critical_todos(wireframe_text)

    fail_reasons: list[str] = []
    warnings: list[str] = []

    if wireframe_hash_status == "MISMATCH":
        fail_reasons.append("active_wireframe hash mismatch")
    if prd_hash_status == "MISMATCH":
        fail_reasons.append("active_prd hash mismatch")
    if scope_hash_status == "MISMATCH":
        fail_reasons.append("active_scope_lock hash mismatch")

    if missing_sections:
        fail_reasons.append("Missing required sections: " + ", ".join(missing_sections))

    if critical_todos:
        fail_reasons.append("Critical sections contain TODO/UNKNOWN: " + ", ".join(critical_todos))

    # Check for references in Generated From
    gen_from = "\n".join(sections.get("Generated From", []))
    if active_prd not in gen_from and Path(active_prd).name not in gen_from:
        fail_reasons.append(f"Wireframe does not reference active PRD ({active_prd}) in Generated From")
    if active_scope_lock not in gen_from and Path(active_scope_lock).name not in gen_from:
        fail_reasons.append(f"Wireframe does not reference active scope ({active_scope_lock}) in Generated From")

    # Check for explicit no model/agent statement
    # The template includes "No model/provider/agent calls." but the confirmation might strip it or replace it.
    # Actually Task A says it should include "no model/provider/agent statement"
    if "no model/provider/agent" not in wireframe_text.lower():
         warnings.append("Explicit 'no model/provider/agent' statement not found in wireframe artifact.")

    if fail_reasons:
        status = "FAIL"
    elif warnings:
        status = "WARN"
    else:
        status = "PASS"

    next_step = "future ws product-tech-plan --dry-run"
    if status == "FAIL":
        next_step = "Fix wireframe findings and rerun review."

    return {
        "status": status,
        "product_id": product_id,
        "wireframe_hash_status": wireframe_hash_status,
        "prd_hash_status": prd_hash_status,
        "scope_hash_status": scope_hash_status,
        "missing_sections": missing_sections,
        "critical_todos": critical_todos,
        "fail_reasons": fail_reasons,
        "warnings": warnings,
        "next_step": next_step,
        "no_write": True,
        "no_model_provider_agent": True,
    }


def render_wireframe_review_report(
    product_record: dict[str, Any],
    review_result: dict[str, Any],
    *,
    wireframe_path: str | Path,
) -> str:
    label = str(product_record.get("label", "")).strip() or str(review_result.get("product_id", "")).strip()
    status = str(review_result.get("status", "FAIL")).strip().upper()
    
    lines = [
        f"# Wireframe Review Report: {label}",
        "",
        "DRY RUN - no files written.",
        "No product state changes.",
        "No model/provider/agent calls.",
        "",
        f"- status: `{status}`",
        f"- product_id: `{review_result.get('product_id', '')}`",
        f"- wireframe_path: `{Path(wireframe_path)}`",
        f"- wireframe_hash_status: `{review_result.get('wireframe_hash_status', 'UNSET')}`",
        f"- active_prd_hash_status: `{review_result.get('prd_hash_status', 'UNSET')}`",
        f"- active_scope_hash_status: `{review_result.get('scope_hash_status', 'UNSET')}`",
        "",
        "## Required Section Checklist",
        "",
    ]

    sections = _extract_sections(review_result.get("wireframe_text", "")) # This is not quite right, text isn't in result
    # I'll just use the missing sections list
    missing = set(review_result.get("missing_sections", []))
    for section_name in REQUIRED_SECTIONS:
        marker = "FAIL" if section_name in missing else "PASS"
        lines.append(f"- [{marker}] {section_name}")

    lines.extend(["", "## Findings", ""])
    if review_result.get("fail_reasons"):
        lines.append("- Fail Reasons:")
        for reason in review_result["fail_reasons"]:
            lines.append(f"  - {reason}")
    else:
        lines.append("- Fail Reasons: none")

    if review_result.get("warnings"):
        lines.append("- Warnings:")
        for warning in review_result["warnings"]:
            lines.append(f"  - {warning}")
    else:
        lines.append("- Warnings: none")

    lines.extend(
        [
            "",
            "## Next Step",
            "",
            f"- {review_result.get('next_step', '').strip()}",
            f"- Review command used: `{WIREFRAME_REVIEW_ACTION} --product <product_id>`",
            "",
        ]
    )
    return "\n".join(lines)
