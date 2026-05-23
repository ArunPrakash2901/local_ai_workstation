#!/usr/bin/env python3
"""Deterministic Product Lane technical plan preview and confirm helpers."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from product_registry import (
    ACTION_LOG_FILENAME,
    get_product_status,
    product_dir,
    save_product,
    validate_product_id,
)
from product_scope_lock import compute_scope_lock_hash
from product_wireframe_review import review_wireframe_text


TECH_PLAN_DRY_RUN_ACTION = "ws product-tech-plan --dry-run"
TECH_PLAN_CONFIRM_ACTION = "ws product-tech-plan --confirm"
APPROVED_STATUS = "APPROVED"
PASS_STATUS = "PASS"
TECH_PLAN_DIR = "technical_plans"
TECH_PLAN_V1_FILENAME = "technical_plan_v1.md"
SECTION_HEADER_RE = re.compile(r"^##\s+(.*)$")
TODO_PATTERN = re.compile(r"\bTODO/UNKNOWN\b", re.IGNORECASE)


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


def _sha256_text(text: str) -> str:
    canonical = _canonicalize_text(text)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_hashed_artifact(
    pdir: Path,
    *,
    relpath: str,
    hash_value: str,
    label: str,
    use_scope_hash: bool = False,
) -> tuple[Path, str, str]:
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
    return artifact_path, content, actual_hash


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


def _section_values(sections: dict[str, list[str]], name: str) -> list[str]:
    values: list[str] = []
    for line in sections.get(name, []):
        item = line.strip()
        if not item:
            continue
        if item.startswith("- "):
            item = item[2:].strip()
        if item:
            values.append(item)
    return values


def _first_non_todo(values: list[str]) -> str:
    for value in values:
        if not TODO_PATTERN.search(value):
            return value
    return "TODO/UNKNOWN"


def validate_tech_plan_preconditions(
    root: str | Path,
    product_id: str,
    *,
    require_wireframe_review_pass: bool,
) -> dict[str, Any]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")

    product_record = get_product_status(root, product_id)
    pdir = product_dir(root, product_id)

    prd_status = str(product_record.get("prd_status", "")).strip().upper()
    if prd_status != APPROVED_STATUS:
        raise ValueError(f"Technical plan requires APPROVED PRD (found {prd_status or 'UNSET'})")

    active_prd = str(product_record.get("active_prd", "")).strip()
    active_prd_hash = str(product_record.get("active_prd_hash", "")).strip()
    prd_path, prd_text, _ = _load_hashed_artifact(
        pdir,
        relpath=active_prd,
        hash_value=active_prd_hash,
        label="active_prd",
    )

    active_scope_lock = str(product_record.get("active_scope_lock", "")).strip()
    active_scope_lock_hash = str(product_record.get("active_scope_lock_hash", "")).strip()
    scope_path, scope_text, _ = _load_hashed_artifact(
        pdir,
        relpath=active_scope_lock,
        hash_value=active_scope_lock_hash,
        label="active_scope_lock",
        use_scope_hash=True,
    )

    active_wireframe = str(product_record.get("active_wireframe", "")).strip()
    active_wireframe_hash = str(product_record.get("active_wireframe_hash", "")).strip()
    wireframe_path, wireframe_text, _ = _load_hashed_artifact(
        pdir,
        relpath=active_wireframe,
        hash_value=active_wireframe_hash,
        label="active_wireframe",
    )

    review_payload = {
        "wireframe_hash_status": "MATCH",
        "prd_hash_status": "MATCH",
        "scope_hash_status": "MATCH",
        "active_prd": active_prd,
        "active_scope_lock": active_scope_lock,
    }
    wireframe_review = review_wireframe_text(product_record, wireframe_text, payload_extras=review_payload)
    if wireframe_review["status"] == "FAIL":
        raise ValueError(
            "Technical plan gated by failing wireframe review. "
            + ", ".join(wireframe_review.get("fail_reasons", []) or ["unknown failure"])
        )
    if require_wireframe_review_pass and wireframe_review["status"] != PASS_STATUS:
        raise ValueError(
            f"Technical plan confirm requires wireframe review PASS (found {wireframe_review['status']})"
        )

    return {
        "product_record": product_record,
        "product_dir": pdir,
        "active_prd": active_prd,
        "active_prd_hash": active_prd_hash,
        "active_prd_path": prd_path,
        "active_prd_text": prd_text,
        "active_scope_lock": active_scope_lock,
        "active_scope_lock_hash": active_scope_lock_hash,
        "active_scope_path": scope_path,
        "active_scope_text": scope_text,
        "active_wireframe": active_wireframe,
        "active_wireframe_hash": active_wireframe_hash,
        "active_wireframe_path": wireframe_path,
        "active_wireframe_text": wireframe_text,
        "wireframe_review": wireframe_review,
    }


def _build_tech_plan_text(payload: dict[str, Any], *, generated_at: str) -> str:
    product_record = payload["product_record"]
    product_id = str(product_record.get("product_id", "")).strip()
    label = str(product_record.get("label", "")).strip() or product_id
    product_type = str(product_record.get("product_type", "")).strip() or "UNKNOWN"

    prd_sections = _extract_sections(str(payload["active_prd_text"]))
    goals = _section_values(prd_sections, "Goals")
    in_scope = _section_values(prd_sections, "In Scope")
    out_of_scope = _section_values(prd_sections, "Out of Scope")
    constraints = _section_values(prd_sections, "Constraints")
    success_criteria = _section_values(prd_sections, "Success Criteria")

    goal_summary = _first_non_todo(goals)
    scope_summary = _first_non_todo(in_scope)
    constraint_summary = _first_non_todo(constraints)
    success_summary = _first_non_todo(success_criteria)

    lines: list[str] = [
        f"# Technical Plan v1: {label}",
        "",
        f"- product_id: `{product_id}`",
        f"- product_type: `{product_type}`",
        f"- label: {label}",
        f"- generated_at: `{generated_at}`",
        f"- active_scope_lock: `{payload['active_scope_lock']}`",
        f"- active_scope_lock_hash: `{payload['active_scope_lock_hash']}`",
        f"- active_prd: `{payload['active_prd']}`",
        f"- active_prd_hash: `{payload['active_prd_hash']}`",
        f"- active_wireframe: `{payload['active_wireframe']}`",
        f"- active_wireframe_hash: `{payload['active_wireframe_hash']}`",
        "- technical_plan_hash: Hash recorded in product.yaml",
        "- models/providers/agents: none",
        "",
        "## Architecture Overview",
        "",
        f"- Primary goal anchor: {goal_summary}",
        f"- Scope anchor: {scope_summary}",
        "- Build a deterministic, content-first UI architecture aligned to the approved PRD and active wireframe.",
        "- Keep implementation boundaries explicit to prevent scope expansion before implementation planning approval.",
        "",
        "## Frontend Structure",
        "",
        "- Organize by route-level screens and shared components.",
        "- Separate layout shells, feature sections, and reusable primitives.",
        "- Keep styling tokens and interaction patterns centrally defined.",
        "",
        "## Data/Content Model",
        "",
        "- Treat PRD and scope artifacts as source-of-truth inputs for static and semi-structured content.",
        f"- Constraint anchor: {constraint_summary}",
        "- Define content contracts per screen to reduce implementation ambiguity.",
        "",
        "## Routing/Navigation",
        "",
        "- Route map must mirror the active wireframe page/screen map.",
        "- Define deterministic transitions between overview/list/detail/contact surfaces.",
        "- Ensure fallback routes and not-found handling are explicit.",
        "",
        "## Component Implementation Plan",
        "",
        "- Build shared layout/navigation primitives first.",
        "- Implement page-level sections in wireframe order, then enrich with structured content bindings.",
        "- Prioritize accessibility-ready interactive components before visual polish passes.",
        "",
        "## Accessibility Implementation Notes",
        "",
        "- Use semantic landmarks and predictable heading hierarchy.",
        "- Enforce keyboard navigation and visible focus indicators for all interactive controls.",
        "- Keep copy, contrast, and state feedback compatible with assistive technologies.",
        "",
        "## Testing Strategy",
        "",
        f"- Success anchor: {success_summary}",
        "- Validate structure-to-wireframe parity and route integrity.",
        "- Cover component behavior with deterministic unit/integration checks.",
        "- Include accessibility-focused verification in implementation readiness checks.",
        "",
        "## Deployment Assumptions",
        "",
        "- Deployment target remains static-host or equivalent web runtime unless revised by a future decision record.",
        "- Build outputs and CI pipelines are planned in implementation planning, not executed here.",
        "- Environment assumptions remain non-secret and workstation-safe in this phase.",
        "",
        "## Explicit Non-Goals",
        "",
    ]

    if out_of_scope:
        for item in out_of_scope:
            lines.append(f"- {item}")
    else:
        lines.append("- TODO/UNKNOWN")

    lines.extend(
        [
            "",
            "## Generated From",
            "",
            "- product.yaml",
            f"- {payload['active_scope_lock']}",
            f"- {payload['active_prd']}",
            f"- {payload['active_wireframe']}",
            "",
            "This artifact was produced deterministically by the workstation from approved Product Lane inputs.",
            "The technical plan hash is recorded in product.yaml.",
            "",
        ]
    )
    return _canonicalize_text("\n".join(lines))


def render_tech_plan_preview(payload: dict[str, Any]) -> str:
    product_record = payload["product_record"]
    product_id = str(product_record.get("product_id", "")).strip()
    label = str(product_record.get("label", "")).strip() or product_id
    review_result = payload["wireframe_review"]
    lines = [
        "Technical Plan Preview",
        "======================",
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
        "Artifact Sources:",
        f"- active_scope_lock: `{payload['active_scope_lock']}`",
        f"- active_scope_lock_hash: `{payload['active_scope_lock_hash']}`",
        f"- active_prd: `{payload['active_prd']}`",
        f"- active_prd_hash: `{payload['active_prd_hash']}`",
        f"- active_wireframe: `{payload['active_wireframe']}`",
        f"- active_wireframe_hash: `{payload['active_wireframe_hash']}`",
        "",
        "Readiness Gate Status:",
        f"- wireframe_review_status: `{review_result.get('status', 'UNSET')}`",
        "",
        "Proposed Artifact Path:",
        f"- {TECH_PLAN_DIR}/{TECH_PLAN_V1_FILENAME}",
        "",
        "## Technical Plan Sections",
        "",
        "- Architecture Overview",
        "- Frontend Structure",
        "- Data/Content Model",
        "- Routing/Navigation",
        "- Component Implementation Plan",
        "- Accessibility Implementation Notes",
        "- Testing Strategy",
        "- Deployment Assumptions",
        "- Explicit Non-Goals",
        "- Generated From",
        "",
        "Next Step:",
        f"- future {TECH_PLAN_CONFIRM_ACTION}",
    ]
    return "\n".join(lines)


def confirm_tech_plan(root: str | Path, product_id: str, *, confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise PermissionError("confirm_tech_plan requires explicit confirm=True")
    payload = validate_tech_plan_preconditions(root, product_id, require_wireframe_review_pass=True)
    product_record = payload["product_record"]
    pdir: Path = payload["product_dir"]

    artifact_dir = _safe_child(pdir, pdir / TECH_PLAN_DIR)
    artifact_path = _safe_child(artifact_dir, artifact_dir / TECH_PLAN_V1_FILENAME)
    if artifact_path.exists():
        raise FileExistsError(f"technical plan artifact already exists: {artifact_path}")

    generated_at = _utc_now_iso()
    artifact_text = _build_tech_plan_text(payload, generated_at=generated_at)
    artifact_hash = _sha256_text(artifact_text)

    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(artifact_text, encoding="utf-8", newline="\n")

    updated_record = dict(product_record)
    updated_record["active_technical_plan"] = f"{TECH_PLAN_DIR}/{TECH_PLAN_V1_FILENAME}"
    updated_record["active_technical_plan_hash"] = artifact_hash
    updated_record["active_technical_plan_revision"] = 1
    updated_record["technical_plan_status"] = "DRAFTED"
    updated_record["technical_plan_created_at"] = generated_at
    updated_record["technical_plan_reviewed_at"] = None
    updated_record["technical_plan_approved_at"] = None
    updated_record["last_action"] = TECH_PLAN_CONFIRM_ACTION
    updated_record["updated_at"] = generated_at

    product_file = save_product(updated_record, root, confirm=True, allow_overwrite=True)

    action_log = _safe_child(pdir, pdir / ACTION_LOG_FILENAME)
    if action_log.is_file():
        with action_log.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"- {generated_at} Technical plan drafted via {TECH_PLAN_CONFIRM_ACTION}\n")

    files_written = [str(artifact_path), str(product_file)]
    if action_log.is_file():
        files_written.append(str(action_log))

    return {
        "product_id": product_id,
        "technical_plan_path": str(artifact_path),
        "product_file": str(product_file),
        "active_technical_plan_hash": artifact_hash,
        "technical_plan_created_at": generated_at,
        "files_written": files_written,
        "used_model_provider_agent": False,
    }
