#!/usr/bin/env python3
"""Product Lane Phase 1 Slice 2 intake artifact helpers.

Scope:
- deterministic intake/questions template rendering
- guarded write path for intake start
- path-bound writes under products/<product_id>/ only
- no model/provider/agent calls
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from product_intake_questions import (
    get_blocking_questions,
    get_optional_questions,
    get_privacy_questions,
    get_question_bank,
    get_required_questions,
)
from product_registry import (
    ACTION_LOG_FILENAME,
    PRODUCT_FILENAME,
    get_product_status,
    product_dir,
    save_product,
    validate_product_id,
)


INTAKE_FILENAME = "intake.md"
QUESTIONS_FILENAME = "questions.md"
INTAKE_START_ACTION = "ws product-intake --confirm"


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


def _group_questions(question_bank: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {
        "required": [],
        "optional": [],
        "blocking": [],
        "privacy": [],
    }
    for question in question_bank:
        category = str(question.get("category", "")).strip().lower()
        if category in groups:
            groups[category].append(question)
    return groups


def intake_paths(root: str | Path, product_id: str) -> dict[str, Path]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")
    target_dir = product_dir(root, product_id)
    intake_path = _safe_child(target_dir, target_dir / INTAKE_FILENAME)
    questions_path = _safe_child(target_dir, target_dir / QUESTIONS_FILENAME)
    product_file = _safe_child(target_dir, target_dir / PRODUCT_FILENAME)
    action_log = _safe_child(target_dir, target_dir / ACTION_LOG_FILENAME)
    return {
        "product_dir": target_dir,
        "product_file": product_file,
        "intake_md": intake_path,
        "questions_md": questions_path,
        "action_log": action_log,
    }


def can_start_intake(
    product_record: dict[str, Any],
    product_root: str | Path,
) -> tuple[bool, str]:
    product_id = str(product_record.get("product_id", "")).strip()
    if not validate_product_id(product_id):
        return False, "product_id is missing or invalid"

    paths = intake_paths(product_root, product_id)
    if not paths["product_file"].is_file():
        return False, f"product not found: {product_id}"

    state = str(product_record.get("state", "")).strip()
    if state != "INBOX":
        return False, f"product must be in INBOX to start intake (found {state or 'UNKNOWN'})"

    if paths["intake_md"].exists():
        return False, f"intake template already exists: {paths['intake_md'].name}"
    if paths["questions_md"].exists():
        return False, f"questions template already exists: {paths['questions_md'].name}"
    return True, ""


def _emit_question_block(lines: list[str], question: dict[str, Any]) -> None:
    question_id = str(question.get("id", "")).strip()
    prompt = str(question.get("prompt", "")).strip()
    help_text = str(question.get("help_text", "")).strip()
    lines.append(f"### `{question_id}`")
    lines.append("")
    lines.append(prompt)
    lines.append("")
    if help_text:
        lines.append(f"_Note: {help_text}_")
        lines.append("")
    lines.append("Answer:")
    lines.append("- [ ] TODO")
    lines.append("")


def render_intake_template(
    product_record: dict[str, Any],
    question_bank: list[dict[str, Any]] | None = None,
) -> str:
    product_id = str(product_record.get("product_id", "")).strip()
    product_type = str(product_record.get("product_type", "")).strip()
    label = str(product_record.get("label", "")).strip()
    state = str(product_record.get("state", "")).strip()
    private = product_record.get("private")
    created_at = str(product_record.get("created_at", "")).strip()
    started_at = str(product_record.get("intake_started_at", "")).strip()

    questions = question_bank if question_bank is not None else get_question_bank(product_type)
    grouped = _group_questions(questions)
    required = grouped["required"]
    optional = grouped["optional"]
    privacy = grouped["privacy"]

    lines = [
        f"# Intake Template: {label or product_id}",
        "",
        "This file starts intake. It does not mean intake is complete.",
        "Generated deterministically by `ws product-intake --confirm` (no model/provider/agent calls).",
        "",
        "## Product Metadata",
        "",
        f"- product_id: `{product_id}`",
        f"- product_type: `{product_type}`",
        f"- label: {label or '(unset)'}",
        f"- state_at_template_creation: `{state}`",
        f"- private: `{private}`",
    ]
    if created_at:
        lines.append(f"- created_at: `{created_at}`")
    if started_at:
        lines.append(f"- intake_started_at: `{started_at}`")
    lines.extend(
        [
            "",
            "## Required Questions",
            "",
        ]
    )
    for question in required:
        _emit_question_block(lines, question)

    lines.extend(
        [
            "## Optional Questions",
            "",
        ]
    )
    for question in optional:
        _emit_question_block(lines, question)

    if privacy:
        lines.extend(
            [
                "## Privacy Questions",
                "",
            ]
        )
        for question in privacy:
            _emit_question_block(lines, question)

    lines.extend(
        [
            "## Intake Status Note",
            "",
            "- This artifact marks intake start only.",
            "- Intake completion, answer import, and scope lock are future steps.",
            "",
        ]
    )
    return "\n".join(lines)


def render_questions_template(
    product_record: dict[str, Any],
    question_bank: list[dict[str, Any]] | None = None,
) -> str:
    product_id = str(product_record.get("product_id", "")).strip()
    product_type = str(product_record.get("product_type", "")).strip()

    required = get_required_questions(product_type)
    optional = get_optional_questions(product_type)
    blocking = get_blocking_questions(product_type)
    privacy = get_privacy_questions(product_type)
    if question_bank is not None:
        grouped = _group_questions(question_bank)
        required = grouped["required"]
        optional = grouped["optional"]
        blocking = grouped["blocking"]
        privacy = grouped["privacy"]

    lines = [
        f"# Intake Questions: {product_id}",
        "",
        f"- product_type: `{product_type}`",
        "- source: static Product Lane question bank",
        "- generation_mode: deterministic (no model/provider/agent calls)",
        "",
        "## Required Questions",
        "",
    ]
    for question in required:
        _emit_question_block(lines, question)

    lines.extend(
        [
            "## Blocking Questions",
            "",
        ]
    )
    for question in blocking:
        _emit_question_block(lines, question)

    lines.extend(
        [
            "## Optional Questions",
            "",
        ]
    )
    for question in optional:
        _emit_question_block(lines, question)

    if privacy:
        lines.extend(
            [
                "## Privacy Questions",
                "",
            ]
        )
        for question in privacy:
            _emit_question_block(lines, question)

    lines.extend(
        [
            "## Completion Guidance",
            "",
            "- Required and blocking questions should be answered first.",
            "- Privacy questions must be answered for private/sensitive content.",
            "- This file is static and deterministic; no model-assisted generation was used.",
            "",
        ]
    )
    return "\n".join(lines)


def _append_action_log(path: Path, *, timestamp: str, message: str) -> None:
    if not path.is_file():
        return
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"- {timestamp} {message}\n")


def _prepare_updated_record(product_record: dict[str, Any], *, started_at: str) -> dict[str, Any]:
    updated = dict(product_record)
    product_type = str(updated.get("product_type", "")).strip()
    question_bank = get_question_bank(product_type)
    grouped = _group_questions(question_bank)
    unresolved = grouped["required"] + grouped["blocking"] + grouped["privacy"]
    unresolved_ids = [str(item.get("id", "")).strip() for item in unresolved if item.get("id")]

    updated["state"] = "INTAKE_STARTED"
    updated["updated_at"] = started_at
    updated["intake_started_at"] = updated.get("intake_started_at") or started_at
    updated["phase"] = "phase_1_intake_scope"
    updated["last_action"] = INTAKE_START_ACTION
    updated["open_questions"] = unresolved_ids
    return updated


def start_intake(
    product_record: dict[str, Any],
    root: str | Path,
    *,
    confirm: bool,
    overwrite: bool = False,
) -> dict[str, Any]:
    if not confirm:
        raise PermissionError("start_intake requires explicit confirm=True")

    product_id = str(product_record.get("product_id", "")).strip()
    if not validate_product_id(product_id):
        raise ValueError("product_id is missing or invalid")
    input_product_type = str(product_record.get("product_type", "")).strip()
    if input_product_type:
        # Validate explicit caller type early to fail fast on malformed payloads.
        get_question_bank(input_product_type)

    paths = intake_paths(root, product_id)
    persisted = get_product_status(root, product_id)
    allowed, reason = can_start_intake(persisted, root)
    if not allowed:
        raise ValueError(reason)

    if not overwrite and (paths["intake_md"].exists() or paths["questions_md"].exists()):
        raise FileExistsError("intake artifacts already exist")

    started_at = _utc_now_iso()
    updated_record = _prepare_updated_record(persisted, started_at=started_at)
    question_bank = get_question_bank(str(updated_record["product_type"]))

    intake_md = render_intake_template(updated_record, question_bank=question_bank)
    questions_md = render_questions_template(updated_record, question_bank=question_bank)

    paths["intake_md"].write_text(intake_md, encoding="utf-8")
    paths["questions_md"].write_text(questions_md, encoding="utf-8")
    product_file = save_product(updated_record, root, confirm=True, allow_overwrite=True)
    _append_action_log(
        paths["action_log"],
        timestamp=started_at,
        message="intake started via ws product-intake --confirm",
    )

    return {
        "product_id": product_id,
        "state_before": persisted.get("state"),
        "state_after": updated_record.get("state"),
        "intake_started_at": updated_record.get("intake_started_at"),
        "updated_at": updated_record.get("updated_at"),
        "open_question_count": len(updated_record.get("open_questions", [])),
        "files_written": [
            str(paths["intake_md"]),
            str(paths["questions_md"]),
            str(product_file),
        ],
        "action_log_updated": paths["action_log"].is_file(),
        "action_log_path": str(paths["action_log"]),
        "used_model_provider_agent": False,
    }
