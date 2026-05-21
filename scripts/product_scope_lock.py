#!/usr/bin/env python3
"""Product Lane Phase 1 Slice 5 scope lock helpers.

Scope:
- deterministic scope lock rendering
- guarded write for scope_lock.md + product.yaml lock metadata
- immutable lock behavior (refuse overwrite)
- path-bound writes under products/<product_id>/ only
- no model/provider/agent calls
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from product_answer_import import ANSWERS_FILENAME
from product_intake_artifacts import INTAKE_FILENAME, QUESTIONS_FILENAME
from product_registry import (
    ACTION_LOG_FILENAME,
    PRODUCT_FILENAME,
    get_product_status,
    product_dir,
    save_product,
    validate_product_id,
)
from product_scope import load_product_scope_inputs


SCOPE_LOCK_FILENAME = "scope_lock.md"
SCOPE_LOCK_ACTION = "ws product-lock-scope --confirm"
SCOPE_READY_STATE = "SCOPE_READY"
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


def _canonicalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    normalized = "\n".join(line.rstrip() for line in lines)
    return normalized.rstrip("\n") + "\n"


def scope_lock_path(root: str | Path, product_id: str) -> Path:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")
    target_dir = product_dir(root, product_id)
    return _safe_child(target_dir, target_dir / SCOPE_LOCK_FILENAME)


def compute_scope_lock_hash(scope_lock_text: str) -> str:
    if not isinstance(scope_lock_text, str) or not scope_lock_text.strip():
        raise ValueError("scope lock text must be a non-empty string")
    canonical = _canonicalize_text(scope_lock_text)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _question_ids_matching(
    question_bank: list[dict[str, Any]],
    predicate: Any,
) -> list[str]:
    ids: list[str] = []
    for question in question_bank:
        question_id = str(question.get("id", "")).strip()
        if not question_id:
            continue
        if predicate(question_id):
            ids.append(question_id)
    return ids


def _collect_answer_values(answers: dict[str, str], ids: list[str]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for question_id in ids:
        answer = str(answers.get(question_id, "")).strip()
        if not answer or answer in seen:
            continue
        values.append(answer)
        seen.add(answer)
    return values


def _section_values(
    question_bank: list[dict[str, Any]],
    answers: dict[str, str],
    *,
    include_tokens: tuple[str, ...],
) -> list[str]:
    ids = _question_ids_matching(
        question_bank,
        lambda question_id: any(token in question_id for token in include_tokens),
    )
    return _collect_answer_values(answers, ids)


def _render_section_lines(title: str, values: list[str]) -> list[str]:
    lines = [f"## {title}", ""]
    if values:
        for value in values:
            lines.append(f"- {value}")
    else:
        lines.append("- TODO/UNKNOWN")
    lines.append("")
    return lines


def _append_action_log(path: Path, *, timestamp: str, message: str) -> None:
    if not path.is_file():
        return
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"- {timestamp} {message}\n")


def render_scope_lock(
    product_record: dict[str, Any],
    question_bank: list[dict[str, Any]],
    answers: dict[str, str],
    *,
    locked_at: str,
) -> str:
    product_id = str(product_record.get("product_id", "")).strip()
    product_type = str(product_record.get("product_type", "")).strip()
    label = str(product_record.get("label", "")).strip() or product_id
    private_value = bool(product_record.get("private", False))
    state = str(product_record.get("state", "")).strip() or SCOPE_READY_STATE

    goal_values = _section_values(question_bank, answers, include_tokens=(".goal",))
    audience_values = _section_values(
        question_bank,
        answers,
        include_tokens=(".audience", ".users", ".target_role", ".company_role", ".role_context"),
    )
    in_scope_values = _section_values(
        question_bank,
        answers,
        include_tokens=(
            ".primary_pages",
            ".core_workflows",
            ".metrics",
            ".materials",
            ".focus_areas",
            ".key_points",
            ".inputs",
            ".outputs",
            ".data_model",
            ".conversion",
            ".call_to_action",
            ".format",
            ".output_format",
            ".content_sources",
        ),
    )
    out_of_scope_values = _section_values(
        question_bank,
        answers,
        include_tokens=(".non_goal", ".non_goals", ".out_of_scope"),
    )
    constraint_values = _section_values(
        question_bank,
        answers,
        include_tokens=(".constraints", ".safety", ".blocking_"),
    )
    dependency_values = _section_values(
        question_bank,
        answers,
        include_tokens=(
            ".dependencies",
            ".integrations",
            ".sources",
            ".source_material",
            ".content_sources",
            ".hosting",
            ".deployment",
            ".permissions",
        ),
    )
    success_values = _section_values(question_bank, answers, include_tokens=(".success_criteria",))
    privacy_values = _section_values(question_bank, answers, include_tokens=(".privacy_", ".privacy"))
    assumptions_values: list[str] = []
    explicit_non_goal_values = out_of_scope_values[:]
    open_questions_at_lock = list(product_record.get("open_questions", []) or [])

    privacy_level_values = privacy_values[:]
    if not privacy_level_values:
        privacy_level_values = ["private" if private_value else "standard"]

    lines: list[str] = [
        f"# Scope Lock: {label}",
        "",
        f"- product_id: `{product_id}`",
        f"- product_type: `{product_type}`",
        f"- label: {label}",
        f"- state_at_lock: `{state}`",
        f"- private: `{private_value}`",
        f"- locked_at: `{locked_at}`",
        "- scope_lock_hash: recorded in product.yaml (sha256 of this file content)",
        "- models/providers/agents: none",
        "",
    ]

    lines.extend(_render_section_lines("Goal / Core Intent", goal_values))
    lines.extend(_render_section_lines("Target User / Audience", audience_values))
    lines.extend(_render_section_lines("In Scope", in_scope_values))
    lines.extend(_render_section_lines("Out of Scope", out_of_scope_values))
    lines.extend(_render_section_lines("Constraints", constraint_values))
    lines.extend(_render_section_lines("Assumptions", assumptions_values))
    lines.extend(_render_section_lines("Dependencies", dependency_values))
    lines.extend(_render_section_lines("Privacy Level", privacy_level_values))
    lines.extend(_render_section_lines("Success Criteria", success_values))
    lines.extend(_render_section_lines("Explicit Non-Goals", explicit_non_goal_values))

    lines.append("## Generated From")
    lines.append("")
    lines.append("- product.yaml")
    lines.append("- intake.md")
    lines.append("- questions.md")
    lines.append("- answers.md")
    lines.append("- ws product-scope --product <product_id> --dry-run output reviewed by operator")
    lines.append("")

    lines.append("## Open Questions At Lock")
    lines.append("")
    if open_questions_at_lock:
        for question_id in open_questions_at_lock:
            lines.append(f"- {question_id}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Operator Confirmation")
    lines.append("")
    lines.append(
        "I confirm this scope is the basis for downstream planning. "
        "Changes require a future scope change decision record."
    )
    lines.append("")
    lines.append(
        "This lock operation does not run agents, models, providers, browser automation, or cloud handoffs."
    )
    lines.append("")

    return _canonicalize_text("\n".join(lines))


def validate_scope_lock_preconditions(root: str | Path, product_id: str) -> dict[str, Any]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")

    product_record = get_product_status(root, product_id)
    state = str(product_record.get("state", "")).strip()
    if state != SCOPE_READY_STATE:
        raise ValueError(
            f"product must be in {SCOPE_READY_STATE} to lock scope (found {state or 'UNKNOWN'})"
        )

    payload = load_product_scope_inputs(root, product_id)

    source_files = payload.get("source_status", {}).get("files", {})
    for required_file in (PRODUCT_FILENAME, INTAKE_FILENAME, QUESTIONS_FILENAME, ANSWERS_FILENAME):
        if not source_files.get(required_file):
            raise FileNotFoundError(
                f"{required_file} is required before scope lock; complete intake and answer import first"
            )

    lock_path = scope_lock_path(root, product_id)
    if lock_path.exists():
        raise FileExistsError(f"scope lock already exists: {lock_path.name}")

    locked_at = product_record.get("scope_locked_at")
    lock_hash = product_record.get("scope_lock_hash")
    if locked_at not in (None, ""):
        raise ValueError("scope lock metadata already set: scope_locked_at")
    if lock_hash not in (None, ""):
        raise ValueError("scope lock metadata already set: scope_lock_hash")

    return {
        **payload,
        "lock_path": lock_path,
    }


def lock_scope(root: str | Path, product_id: str, *, confirm: bool) -> dict[str, Any]:
    if not confirm:
        raise PermissionError("lock_scope requires explicit confirm=True")

    payload = validate_scope_lock_preconditions(root, product_id)
    product_record = payload["product_record"]
    lock_path: Path = payload["lock_path"]
    product_dir_path = product_dir(root, product_id)
    action_log = _safe_child(product_dir_path, product_dir_path / ACTION_LOG_FILENAME)
    state_before = str(product_record.get("state", "")).strip()

    timestamp = _utc_now_iso()
    scope_lock_text = render_scope_lock(
        product_record,
        payload["question_bank"],
        payload["answers"],
        locked_at=timestamp,
    )
    lock_hash = compute_scope_lock_hash(scope_lock_text)

    lock_path.write_text(scope_lock_text, encoding="utf-8", newline="\n")

    updated_record = dict(product_record)
    updated_record["state"] = SCOPE_LOCKED_STATE
    updated_record["scope_locked_at"] = timestamp
    updated_record["scope_lock_hash"] = lock_hash
    updated_record["updated_at"] = timestamp
    updated_record["last_action"] = SCOPE_LOCK_ACTION
    updated_record["open_questions"] = []
    product_file = save_product(updated_record, root, confirm=True, allow_overwrite=True)

    _append_action_log(
        action_log,
        timestamp=timestamp,
        message=f"scope locked via {SCOPE_LOCK_ACTION} (state={state_before}->{SCOPE_LOCKED_STATE})",
    )

    return {
        "product_id": product_id,
        "state_before": state_before,
        "state_after": SCOPE_LOCKED_STATE,
        "scope_locked_at": timestamp,
        "scope_lock_hash": lock_hash,
        "scope_lock_path": str(lock_path),
        "product_file": str(product_file),
        "action_log_updated": action_log.is_file(),
        "action_log_path": str(action_log),
        "used_model_provider_agent": False,
    }
