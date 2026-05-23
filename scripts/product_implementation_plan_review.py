#!/usr/bin/env python3
"""Deterministic no-write Product Lane implementation plan review helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from product_registry import get_product_status, product_dir, validate_product_id
from product_scope_lock import compute_scope_lock_hash
from product_tech_plan import APPROVED_STATUS


IMPLEMENTATION_PLAN_REVIEW_ACTION = "ws product-implementation-plan-review --dry-run"
IMPLEMENTATION_PLAN_DRY_RUN_ACTION = "ws product-implementation-plan --dry-run"
TODO_PATTERN = re.compile(r"\bTODO/UNKNOWN\b", re.IGNORECASE)
SECTION_HEADER_RE = re.compile(r"^##\s+(.*)$")
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


def _safe_child(base: Path, child: Path) -> Path:
    base_resolved = base.resolve()
    child_resolved = child.resolve()
    if child_resolved == base_resolved:
        return child_resolved
    if base_resolved not in child_resolved.parents:
        raise ValueError(f"path escapes expected base: {child_resolved} not under {base_resolved}")
    return child_resolved


def _extract_sections(md_text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in md_text.splitlines():
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


def _sha256_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    canonical = "\n".join(line.rstrip() for line in lines).rstrip("\n") + "\n"
    import hashlib

    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_hashed_artifact(
    pdir: Path,
    *,
    relpath: str,
    hash_value: str,
    label: str,
    use_scope_hash: bool = False,
) -> tuple[Path, str]:
    if not relpath:
        raise ValueError(f"{label} path is missing in product metadata")
    artifact_path = _safe_child(pdir, pdir / relpath)
    if not artifact_path.is_file():
        raise FileNotFoundError(f"{label} file missing: {relpath}")
    if not hash_value:
        raise ValueError(f"{label} hash is missing in product metadata")
    content = artifact_path.read_text(encoding="utf-8")
    actual_hash = compute_scope_lock_hash(content) if use_scope_hash else _sha256_text(content)
    if actual_hash != hash_value:
        raise ValueError(f"{label} hash mismatch")
    return artifact_path, content


def validate_implementation_plan_review_preconditions(root: str | Path, product_id: str) -> dict[str, Any]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")

    product_record = get_product_status(root, product_id)
    pdir = product_dir(root, product_id)

    prd_status = str(product_record.get("prd_status", "")).strip().upper()
    if prd_status != APPROVED_STATUS:
        raise ValueError(f"implementation plan review requires prd_status={APPROVED_STATUS} (found {prd_status or 'UNSET'})")

    active_impl = str(product_record.get("active_implementation_plan", "")).strip()
    active_impl_hash = str(product_record.get("active_implementation_plan_hash", "")).strip()
    impl_path, impl_text = _load_hashed_artifact(
        pdir,
        relpath=active_impl,
        hash_value=active_impl_hash,
        label="active_implementation_plan",
    )

    active_scope_lock = str(product_record.get("active_scope_lock", "")).strip()
    active_scope_lock_hash = str(product_record.get("active_scope_lock_hash", "")).strip()
    _scope_path, _scope_text = _load_hashed_artifact(
        pdir,
        relpath=active_scope_lock,
        hash_value=active_scope_lock_hash,
        label="active_scope_lock",
        use_scope_hash=True,
    )

    active_prd = str(product_record.get("active_prd", "")).strip()
    active_prd_hash = str(product_record.get("active_prd_hash", "")).strip()
    _prd_path, _prd_text = _load_hashed_artifact(
        pdir,
        relpath=active_prd,
        hash_value=active_prd_hash,
        label="active_prd",
    )

    active_wireframe = str(product_record.get("active_wireframe", "")).strip()
    active_wireframe_hash = str(product_record.get("active_wireframe_hash", "")).strip()
    _wire_path, _wire_text = _load_hashed_artifact(
        pdir,
        relpath=active_wireframe,
        hash_value=active_wireframe_hash,
        label="active_wireframe",
    )

    active_tech_plan = str(product_record.get("active_technical_plan", "")).strip()
    active_tech_plan_hash = str(product_record.get("active_technical_plan_hash", "")).strip()
    _tech_path, _tech_text = _load_hashed_artifact(
        pdir,
        relpath=active_tech_plan,
        hash_value=active_tech_plan_hash,
        label="active_technical_plan",
    )

    return {
        "product_record": product_record,
        "impl_plan_path": impl_path,
        "impl_plan_text": impl_text,
        "active_scope_lock": active_scope_lock,
        "active_prd": active_prd,
        "active_wireframe": active_wireframe,
        "active_technical_plan": active_tech_plan,
        "hash_statuses": {
            "active_implementation_plan": "MATCH",
            "active_scope_lock": "MATCH",
            "active_prd": "MATCH",
            "active_wireframe": "MATCH",
            "active_technical_plan": "MATCH",
        },
    }


def review_implementation_plan_text(
    product_record: dict[str, Any],
    impl_plan_text: str,
    *,
    payload_extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(impl_plan_text, str) or not impl_plan_text.strip():
        raise ValueError("implementation plan text must be non-empty")
    payload_extras = payload_extras or {}
    sections = _extract_sections(impl_plan_text)

    missing_sections = [section for section in REQUIRED_SECTIONS if section not in sections]
    critical_todos: list[str] = []
    for section in REQUIRED_SECTIONS:
        if section in sections and TODO_PATTERN.search("\n".join(sections[section])):
            critical_todos.append(section)

    fail_reasons: list[str] = []
    warnings: list[str] = []
    if missing_sections:
        fail_reasons.append("Missing required sections: " + ", ".join(missing_sections))
    if critical_todos:
        fail_reasons.append("Critical sections contain TODO/UNKNOWN: " + ", ".join(critical_todos))

    generated_from = "\n".join(sections.get("Generated From", []))
    active_scope_lock = str(payload_extras.get("active_scope_lock", "")).strip()
    active_prd = str(payload_extras.get("active_prd", "")).strip()
    active_wireframe = str(payload_extras.get("active_wireframe", "")).strip()
    active_tech_plan = str(payload_extras.get("active_technical_plan", "")).strip()

    if "product.yaml" not in generated_from:
        fail_reasons.append("Generated From missing product.yaml reference")
    for label, relpath in (
        ("active scope", active_scope_lock),
        ("active PRD", active_prd),
        ("active wireframe", active_wireframe),
        ("active technical plan", active_tech_plan),
    ):
        if relpath and relpath not in generated_from and Path(relpath).name not in generated_from:
            fail_reasons.append(f"Generated From missing {label} reference ({relpath})")

    deterministic_statement = "deterministic workstation planning artifact"
    if deterministic_statement not in impl_plan_text.lower():
        fail_reasons.append("deterministic workstation statement is missing")

    if fail_reasons:
        status = "FAIL"
    elif warnings:
        status = "WARN"
    else:
        status = "PASS"

    if status == "PASS":
        next_step = "Implementation plan is ready for exchange preview."
    elif status == "WARN":
        next_step = f"Resolve warnings and rerun {IMPLEMENTATION_PLAN_REVIEW_ACTION}"
    else:
        next_step = f"Fix implementation plan findings and rerun {IMPLEMENTATION_PLAN_REVIEW_ACTION}"

    return {
        "status": status,
        "product_id": str(product_record.get("product_id", "")).strip(),
        "missing_sections": missing_sections,
        "critical_todos": critical_todos,
        "warnings": warnings,
        "fail_reasons": fail_reasons,
        "required_sections_present": [s for s in REQUIRED_SECTIONS if s in sections],
        "hash_statuses": payload_extras.get("hash_statuses", {}),
        "next_step": next_step,
        "no_write": True,
    }


def render_implementation_plan_review_report(
    product_record: dict[str, Any],
    review_result: dict[str, Any],
    *,
    impl_plan_path: str | Path,
) -> str:
    label = str(product_record.get("label", "")).strip() or str(review_result.get("product_id", "")).strip()
    present = set(review_result.get("required_sections_present", []))
    lines: list[str] = [
        f"# Implementation Plan Review Report: {label}",
        "",
        "DRY RUN - no files written.",
        "No product state changes.",
        "No model/provider/agent calls.",
        "",
        f"- status: `{review_result.get('status', 'FAIL')}`",
        f"- product_id: `{review_result.get('product_id', '')}`",
        f"- implementation_plan_path: `{Path(impl_plan_path)}`",
        "",
        "## Required Section Checklist",
        "",
    ]
    for section in REQUIRED_SECTIONS:
        marker = "PASS" if section in present else "FAIL"
        lines.append(f"- [{marker}] {section}")

    lines.extend(["", "## Critical TODO/UNKNOWN", ""])
    critical_todos = list(review_result.get("critical_todos", []))
    if critical_todos:
        for item in critical_todos:
            lines.append(f"- {item}")
    else:
        lines.append("- None")

    lines.extend(["", "## Warnings", ""])
    warnings = list(review_result.get("warnings", []))
    if warnings:
        for item in warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- None")

    lines.extend(["", "## Fail Reasons", ""])
    fail_reasons = list(review_result.get("fail_reasons", []))
    if fail_reasons:
        for item in fail_reasons:
            lines.append(f"- {item}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Next Step",
            "",
            f"- {review_result.get('next_step', '')}",
            f"- Review command used: `{IMPLEMENTATION_PLAN_REVIEW_ACTION} --product <product_id>`",
            "",
        ]
    )
    return "\n".join(lines)
