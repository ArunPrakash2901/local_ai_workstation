#!/usr/bin/env python3
"""Product Lane Phase 2 PRD helpers for preview and guarded write."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from product_registry import ACTION_LOG_FILENAME, PRODUCT_FILENAME, get_product_status, product_dir, save_product, validate_product_id
from product_scope_lock import SCOPE_LOCK_FILENAME, compute_scope_lock_hash


PRD_PREVIEW_ACTION = "ws product-prd --dry-run"
PRD_WRITE_ACTION = "ws product-prd --confirm"
PRD_FILENAME = "prd.md"
SCOPE_LOCKED_STATE = "SCOPE_LOCKED"
SUPPORTED_PRODUCT_TYPES = {
    "website",
    "webapp",
    "dashboard",
    "automation",
    "job-pack",
    "cover-letter",
    "interview-prep",
    "video-script",
}

SECTION_HEADER_RE = re.compile(r"^##\s+(.*)$")


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


def _strip_inline_markup(text: str) -> str:
    value = text.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        return value[1:-1]
    return value


def prd_paths(root: str | Path, product_id: str) -> dict[str, Path]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")
    target_dir = product_dir(root, product_id)
    return {
        "product_dir": target_dir,
        "product_file": _safe_child(target_dir, target_dir / PRODUCT_FILENAME),
        "scope_lock_md": _safe_child(target_dir, target_dir / SCOPE_LOCK_FILENAME),
        "prd_md": _safe_child(target_dir, target_dir / PRD_FILENAME),
    }


def prd_path(root: str | Path, product_id: str) -> Path:
    return prd_paths(root, product_id)["prd_md"]


def classify_missing_prd_inputs(product_record: dict[str, Any], product_dir_path: str | Path) -> dict[str, Any]:
    directory = Path(product_dir_path).resolve()
    files = {
        PRODUCT_FILENAME: _safe_child(directory, directory / PRODUCT_FILENAME).is_file(),
        SCOPE_LOCK_FILENAME: _safe_child(directory, directory / SCOPE_LOCK_FILENAME).is_file(),
    }
    return {
        "product_id": str(product_record.get("product_id", "")).strip(),
        "state": str(product_record.get("state", "")).strip(),
        "files": files,
        "missing_files": [name for name, exists in files.items() if not exists],
    }


def parse_scope_lock(scope_lock_text: str) -> dict[str, Any]:
    if not isinstance(scope_lock_text, str) or not scope_lock_text.strip():
        raise ValueError("scope_lock_text must be a non-empty string")

    metadata: dict[str, str] = {}
    sections: dict[str, list[str]] = {}
    current_section: str | None = None
    in_metadata = True

    for raw_line in scope_lock_text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        heading = SECTION_HEADER_RE.match(stripped)
        if heading:
            current_section = heading.group(1).strip()
            in_metadata = False
            sections.setdefault(current_section, [])
            continue

        if in_metadata and stripped.startswith("- ") and ":" in stripped:
            key, value = stripped[2:].split(":", 1)
            metadata[key.strip()] = _strip_inline_markup(value.strip())
            continue

        if current_section is None:
            continue

        if stripped.startswith("- "):
            sections[current_section].append(_strip_inline_markup(stripped[2:].strip()))
        else:
            sections[current_section].append(_strip_inline_markup(stripped))

    return {"metadata": metadata, "sections": sections}


def _normalize_values(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value).strip()
        if not item:
            continue
        if item in seen:
            continue
        cleaned.append(item)
        seen.add(item)
    return cleaned


def _section_values(sections: dict[str, list[str]], section_name: str) -> list[str]:
    values = _normalize_values(list(sections.get(section_name, [])))
    return values or ["TODO/UNKNOWN"]


def _summarize(values: list[str]) -> str:
    clean = [value for value in values if value and value != "TODO/UNKNOWN"]
    if not clean:
        return "TODO/UNKNOWN"
    return "; ".join(clean[:2])


def validate_prd_preconditions(
    product_record: dict[str, Any],
    product_dir_path: str | Path,
    *,
    scope_lock_text: str | None = None,
) -> dict[str, Any]:
    state = str(product_record.get("state", "")).strip()
    if state != SCOPE_LOCKED_STATE:
        raise ValueError(
            f"product must be in {SCOPE_LOCKED_STATE} for PRD preview (found {state or 'UNKNOWN'})"
        )

    product_type = str(product_record.get("product_type", "")).strip()
    if product_type not in SUPPORTED_PRODUCT_TYPES:
        raise ValueError(f"unsupported product_type for PRD preview: {product_type or 'UNKNOWN'}")

    directory = Path(product_dir_path).resolve()
    lock_path = _safe_child(directory, directory / SCOPE_LOCK_FILENAME)
    if not lock_path.is_file():
        raise FileNotFoundError(
            "scope_lock.md is missing; run ws product-lock-scope --product <product_id> --confirm first"
        )

    scope_lock_hash = str(product_record.get("scope_lock_hash", "")).strip()
    if not scope_lock_hash:
        raise ValueError("scope_lock_hash is required for PRD preview")

    scope_locked_at = str(product_record.get("scope_locked_at", "")).strip()
    if not scope_locked_at:
        raise ValueError("scope_locked_at is required for PRD preview")

    lock_text = scope_lock_text if scope_lock_text is not None else lock_path.read_text(encoding="utf-8")
    actual_hash = compute_scope_lock_hash(lock_text)
    if actual_hash != scope_lock_hash:
        raise ValueError("scope_lock.md hash mismatch with product.yaml")

    parsed = parse_scope_lock(lock_text)
    return {
        "product_record": product_record,
        "product_dir": directory,
        "scope_lock_path": lock_path,
        "scope_lock_text": lock_text,
        "scope_lock_data": parsed,
        "scope_lock_hash": scope_lock_hash,
    }


def load_prd_inputs(root: str | Path, product_id: str) -> dict[str, Any]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")

    paths = prd_paths(root, product_id)
    product_record = get_product_status(root, product_id)
    payload = validate_prd_preconditions(
        product_record,
        paths["product_dir"],
    )
    payload["scope_lock_text"] = paths["scope_lock_md"].read_text(encoding="utf-8")
    payload["scope_lock_data"] = parse_scope_lock(payload["scope_lock_text"])
    source_status = classify_missing_prd_inputs(product_record, paths["product_dir"])
    payload["paths"] = paths
    payload["source_status"] = source_status
    return payload


def validate_prd_write_preconditions(root: str | Path, product_id: str) -> dict[str, Any]:
    payload = load_prd_inputs(root, product_id)
    prd_md = payload["paths"]["prd_md"]
    if prd_md.exists():
        raise FileExistsError(f"prd already exists: {prd_md}")
    payload["prd_path"] = prd_md
    return payload


def _transform_preview_to_write(preview_text: str) -> str:
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
            line = "- PRD draft written by `ws product-prd --confirm` from locked scope."
        elif line.startswith("- Preview command used: "):
            line = "- Written by `ws product-prd --confirm` from locked scope."
        lines.append(line)
    return "\n".join(lines)


def render_prd_document(
    product_record: dict[str, Any],
    scope_lock_text: str,
    *,
    dry_run: bool = False,
) -> str:
    preview_text = render_prd_preview(product_record, scope_lock_text)
    if dry_run:
        return preview_text
    return _transform_preview_to_write(preview_text)


def render_prd_preview(product_record: dict[str, Any], scope_lock_text: str) -> str:
    parsed = parse_scope_lock(scope_lock_text)
    sections = parsed["sections"]
    product_id = str(product_record.get("product_id", "")).strip()
    product_type = str(product_record.get("product_type", "")).strip()
    label = str(product_record.get("label", "")).strip() or product_id
    state = str(product_record.get("state", "")).strip() or "UNKNOWN"
    scope_lock_hash = str(product_record.get("scope_lock_hash", "")).strip() or "TODO/UNKNOWN"
    private_value = bool(product_record.get("private", False))

    goal_values = _section_values(sections, "Goal / Core Intent")
    audience_values = _section_values(sections, "Target User / Audience")
    in_scope_values = _section_values(sections, "In Scope")
    out_of_scope_values = _section_values(sections, "Out of Scope")
    constraint_values = _section_values(sections, "Constraints")
    dependency_values = _section_values(sections, "Dependencies")
    success_values = _section_values(sections, "Success Criteria")
    open_questions_values = _section_values(sections, "Open Questions At Lock")
    confirmation_values = _section_values(sections, "Operator Confirmation")

    requirements_values = in_scope_values[:]
    if requirements_values == ["TODO/UNKNOWN"]:
        requirements_values = ["TODO/UNKNOWN"]
    else:
        requirements_values.extend(
            [
                "Scope lock hash must match product.yaml before any downstream planning.",
                "Preview mode must not write files, update product.yaml, or invoke models/providers/agents.",
            ]
        )

    risk_values = [
        "If scope_lock.md and product.yaml diverge, downstream planning must stop until scope is re-locked.",
        "If any section renders TODO/UNKNOWN, treat the PRD preview as provisional.",
    ]
    if private_value:
        risk_values.append(
            "Private products must keep cloud handoff explicit and warning-gated in later phases."
        )

    lines: list[str] = [
        f"# PRD Preview: {label}",
        "",
        "DRY RUN - no files written.",
        "No product state changes.",
        "No model/provider/agent calls.",
        "",
        f"- product_id: `{product_id}`",
        f"- product_type: `{product_type}`",
        f"- label: {label}",
        f"- current_state: `{state}`",
        f"- scope_lock_hash: `{scope_lock_hash}`",
        f"- private: `{private_value}`",
        "",
        "## Executive Summary",
        "",
        f"- Locked scope source: `{SCOPE_LOCK_FILENAME}`",
        f"- Goal summary: {_summarize(goal_values)}",
        f"- Audience summary: {_summarize(audience_values)}",
        "",
        "## Problem Statement",
        "",
        f"- {_summarize(goal_values)}",
        f"- Audience: {_summarize(audience_values)}",
        "- The locked scope is the source of truth for later planning phases.",
        "",
        "## Target Users / Audience",
        "",
    ]
    lines.extend(f"- {value}" for value in audience_values)
    lines.extend(
        [
            "",
            "## Goals",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in goal_values)
    lines.extend(
        [
            "",
            "## Non-Goals",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in out_of_scope_values)
    lines.extend(
        [
            "",
            "## In Scope",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in in_scope_values)
    lines.extend(
        [
            "",
            "## Out of Scope",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in out_of_scope_values)
    lines.extend(
        [
            "",
            "## Requirements",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in requirements_values)
    lines.extend(
        [
            "",
            "## Constraints",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in constraint_values)
    lines.extend(
        [
            "",
            "## Dependencies",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in dependency_values)
    lines.extend(
        [
            "",
            "## Success Criteria",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in success_values)
    lines.extend(
        [
            "",
            "## Risks and Mitigations",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in risk_values)
    lines.extend(
        [
            "",
            "## Acceptance Criteria",
            "",
            f"- Product state remains `{SCOPE_LOCKED_STATE}`.",
            "- `scope_lock_hash` is present and matches `scope_lock.md`.",
            "- Preview mode writes no files and changes no product state.",
            "- No model/provider/agent calls occur.",
            "",
            "## Generated From",
            "",
        ]
    )
    lines.append("- product.yaml")
    lines.append("- scope_lock.md")
    lines.append("- scope_lock.md is the locked source of truth for downstream planning.")
    lines.append("- product.yaml records the lock hash and state metadata.")
    lines.extend(
        [
            "",
            "## Open Questions At Lock",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in open_questions_values)
    lines.extend(
        [
            "",
            "## Operator Confirmation",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in confirmation_values)
    lines.extend(
        [
            "",
            "## Next Step",
            "",
            "- Use `ws product-prd --confirm` to write `prd.md` when approved.",
            "- Review this preview and keep `scope_lock.md` as the source of truth.",
            f"- Preview command used: `{PRD_PREVIEW_ACTION}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_prd(
    root: str | Path,
    product_id: str,
    *,
    confirm: bool,
    overwrite: bool = False,
) -> dict[str, Any]:
    if not confirm:
        raise PermissionError("write_prd requires explicit confirm=True")

    del overwrite  # overwrite is intentionally not supported in this slice.

    payload = validate_prd_write_preconditions(root, product_id)
    product_record = payload["product_record"]
    prd_md: Path = payload["prd_path"]
    product_dir_path: Path = payload["product_dir"]
    action_log = product_dir_path / ACTION_LOG_FILENAME
    state_before = str(product_record.get("state", "")).strip()

    timestamp = _utc_now_iso()
    prd_text = render_prd_document(
        product_record,
        payload["scope_lock_text"],
        dry_run=False,
    )
    prd_md.write_text(prd_text.rstrip() + "\n", encoding="utf-8", newline="\n")

    updated_record = dict(product_record)
    updated_record["updated_at"] = timestamp
    updated_record["last_action"] = PRD_WRITE_ACTION
    updated_record["prd_created_at"] = timestamp
    
    # New active artifact pattern
    updated_record["active_prd"] = PRD_FILENAME
    updated_record["active_prd_hash"] = hashlib.sha256(prd_text.rstrip().encode("utf-8") + b"\n").hexdigest()
    updated_record["active_prd_revision"] = 1
    
    # Also ensure active scope is set if missing (for legacy transition)
    if not updated_record.get("active_scope_lock"):
        updated_record["active_scope_lock"] = SCOPE_LOCK_FILENAME
        updated_record["active_scope_lock_hash"] = str(product_record.get("scope_lock_hash", "")).strip()
        updated_record["active_scope_revision"] = 1

    product_file = save_product(updated_record, root, confirm=True, allow_overwrite=True)

    if action_log.is_file():
        with action_log.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"- {timestamp} PRD drafted via {PRD_WRITE_ACTION} (state={state_before})\n")

    files_written = [str(prd_md), str(product_file)]
    if action_log.is_file():
        files_written.append(str(action_log))

    return {
        "product_id": product_id,
        "state_before": state_before,
        "state_after": state_before,
        "prd_path": prd_md,
        "product_file": product_file,
        "scope_lock_hash": str(product_record.get("scope_lock_hash", "")).strip(),
        "prd_created_at": timestamp,
        "files_written": files_written,
        "used_model_provider_agent": False,
    }
