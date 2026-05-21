#!/usr/bin/env python3
"""Product Lane Phase 1 Slice 3 answer import helpers.

Scope:
- deterministic operator answer parsing
- guarded write path for answers import
- intake completion classification
- path-bound writes under products/<product_id>/ only
- no model/provider/agent calls
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from product_intake_artifacts import INTAKE_FILENAME, QUESTIONS_FILENAME
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


ANSWERS_FILENAME = "answers.md"
ANSWER_IMPORT_ACTION = "ws product-answer-import --confirm"
ALLOWED_IMPORT_STATES = {"INTAKE_STARTED", "CLARIFICATION_NEEDED"}


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


def answer_paths(root: str | Path, product_id: str) -> dict[str, Path]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")
    target_dir = product_dir(root, product_id)
    return {
        "product_dir": target_dir,
        "product_file": _safe_child(target_dir, target_dir / PRODUCT_FILENAME),
        "intake_md": _safe_child(target_dir, target_dir / INTAKE_FILENAME),
        "questions_md": _safe_child(target_dir, target_dir / QUESTIONS_FILENAME),
        "answers_md": _safe_child(target_dir, target_dir / ANSWERS_FILENAME),
        "action_log": _safe_child(target_dir, target_dir / ACTION_LOG_FILENAME),
    }


def parse_answers_text(text: str) -> dict[str, str]:
    if not isinstance(text, str):
        raise ValueError("answers text must be a string")
    answers: dict[str, str] = {}
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(
                f"line {line_number}: expected '<question_id>: <answer>' format"
            )
        question_id, answer = line.split(":", 1)
        question_id = question_id.strip()
        answer = answer.strip()
        if not question_id:
            raise ValueError(f"line {line_number}: question_id is empty")
        if question_id in answers:
            raise ValueError(f"line {line_number}: duplicate question_id '{question_id}'")
        answers[question_id] = answer
    return answers


def validate_answers(
    product_record: dict[str, Any],
    question_bank: list[dict[str, Any]],
    answers: dict[str, str],
) -> dict[str, str]:
    if not isinstance(product_record, dict):
        raise ValueError("product_record must be a mapping")
    if not isinstance(question_bank, list):
        raise ValueError("question_bank must be a list")
    if not isinstance(answers, dict):
        raise ValueError("answers must be a mapping")

    known_ids = {
        str(question.get("id", "")).strip()
        for question in question_bank
        if str(question.get("id", "")).strip()
    }
    unknown = sorted(question_id for question_id in answers if question_id not in known_ids)
    if unknown:
        raise ValueError(f"unknown question_id(s): {', '.join(unknown)}")

    normalized: dict[str, str] = {}
    for question_id, answer in answers.items():
        normalized[question_id] = str(answer).strip()
    return normalized


def unanswered_required_questions(
    product_record: dict[str, Any],
    question_bank: list[dict[str, Any]],
    answers: dict[str, str],
) -> dict[str, list[str]]:
    del product_record  # current classification is question-bank driven.

    required: list[str] = []
    blocking: list[str] = []
    privacy: list[str] = []
    for question in question_bank:
        question_id = str(question.get("id", "")).strip()
        if not question_id:
            continue
        category = str(question.get("category", "")).strip().lower()
        answer = str(answers.get(question_id, "")).strip()
        if answer:
            continue
        if category == "required":
            required.append(question_id)
        elif category == "blocking":
            blocking.append(question_id)
        elif category == "privacy":
            privacy.append(question_id)

    return {
        "required": required,
        "blocking": blocking,
        "privacy": privacy,
        "all": required + blocking + privacy,
    }


def classify_intake_state(
    product_record: dict[str, Any],
    question_bank: list[dict[str, Any]],
    answers: dict[str, str],
) -> dict[str, Any]:
    unresolved = unanswered_required_questions(product_record, question_bank, answers)
    state_after = "SCOPE_READY" if not unresolved["all"] else "CLARIFICATION_NEEDED"
    return {
        "state_before": str(product_record.get("state", "")).strip(),
        "state_after": state_after,
        "unresolved_required": unresolved["required"],
        "unresolved_blocking": unresolved["blocking"],
        "unresolved_privacy": unresolved["privacy"],
        "unresolved_all": unresolved["all"],
    }


def _render_question_group(
    lines: list[str],
    title: str,
    questions: list[dict[str, Any]],
    answers: dict[str, str],
) -> None:
    lines.append(f"## {title}")
    lines.append("")
    for question in questions:
        question_id = str(question.get("id", "")).strip()
        if not question_id:
            continue
        prompt = str(question.get("prompt", "")).strip()
        answer = str(answers.get(question_id, "")).strip()
        lines.append(f"### `{question_id}`")
        lines.append("")
        if prompt:
            lines.append(prompt)
            lines.append("")
        if answer:
            lines.append(f"Answer: {answer}")
        else:
            lines.append("Answer: (unanswered)")
        lines.append("")


def render_answers_md(
    product_record: dict[str, Any],
    question_bank: list[dict[str, Any]],
    answers: dict[str, str],
    classification: dict[str, Any],
) -> str:
    product_id = str(product_record.get("product_id", "")).strip()
    product_type = str(product_record.get("product_type", "")).strip()
    label = str(product_record.get("label", "")).strip()

    required = get_required_questions(product_type)
    blocking = get_blocking_questions(product_type)
    privacy = get_privacy_questions(product_type)
    optional = get_optional_questions(product_type)
    if question_bank:
        by_category: dict[str, list[dict[str, Any]]] = {
            "required": [],
            "blocking": [],
            "privacy": [],
            "optional": [],
        }
        for question in question_bank:
            category = str(question.get("category", "")).strip().lower()
            if category in by_category:
                by_category[category].append(question)
        required = by_category["required"]
        blocking = by_category["blocking"]
        privacy = by_category["privacy"]
        optional = by_category["optional"]

    lines = [
        f"# Intake Answers: {label or product_id}",
        "",
        f"- product_id: `{product_id}`",
        f"- product_type: `{product_type}`",
        f"- imported_at: `{product_record.get('updated_at', '')}`",
        f"- state_before: `{classification['state_before']}`",
        f"- state_after: `{classification['state_after']}`",
        "- import_mode: operator-provided answers only",
        "- models/providers/agents: none",
        "",
    ]
    _render_question_group(lines, "Required Questions", required, answers)
    _render_question_group(lines, "Blocking Questions", blocking, answers)
    _render_question_group(lines, "Privacy Questions", privacy, answers)
    _render_question_group(lines, "Optional Questions", optional, answers)

    lines.extend(
        [
            "## Intake Classification",
            "",
            f"- unresolved_required: {len(classification['unresolved_required'])}",
            f"- unresolved_blocking: {len(classification['unresolved_blocking'])}",
            f"- unresolved_privacy: {len(classification['unresolved_privacy'])}",
            "",
        ]
    )
    if classification["unresolved_all"]:
        lines.append("Unresolved question IDs:")
        for question_id in classification["unresolved_all"]:
            lines.append(f"- `{question_id}`")
        lines.append("")

    return "\n".join(lines)


def _append_action_log(path: Path, *, timestamp: str, message: str) -> None:
    if not path.is_file():
        return
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"- {timestamp} {message}\n")


def _prepare_updated_record(
    product_record: dict[str, Any],
    *,
    classification: dict[str, Any],
    timestamp: str,
) -> dict[str, Any]:
    updated = dict(product_record)
    state_after = classification["state_after"]
    updated["state"] = state_after
    updated["updated_at"] = timestamp
    updated["last_action"] = ANSWER_IMPORT_ACTION
    updated["open_questions"] = list(classification["unresolved_all"])
    updated["scope_locked_at"] = updated.get("scope_locked_at")
    if state_after == "SCOPE_READY":
        updated["intake_completed_at"] = timestamp
        updated["scope_ready_at"] = timestamp
    else:
        updated["intake_completed_at"] = None
        updated["scope_ready_at"] = None
    return updated


def import_answers(
    product_record: dict[str, Any],
    root: str | Path,
    answers_text: str,
    *,
    confirm: bool,
    overwrite: bool = False,
) -> dict[str, Any]:
    if not confirm:
        raise PermissionError("import_answers requires explicit confirm=True")

    product_id = str(product_record.get("product_id", "")).strip()
    if not validate_product_id(product_id):
        raise ValueError("product_id is missing or invalid")
    input_product_type = str(product_record.get("product_type", "")).strip()
    if input_product_type:
        # Validate explicit caller type early to fail fast on malformed payloads.
        get_question_bank(input_product_type)

    paths = answer_paths(root, product_id)
    persisted = get_product_status(root, product_id)
    state_before = str(persisted.get("state", "")).strip()
    if state_before not in ALLOWED_IMPORT_STATES:
        allowed = ", ".join(sorted(ALLOWED_IMPORT_STATES))
        raise ValueError(
            f"product must be in {allowed} to import answers (found {state_before or 'UNKNOWN'})"
        )

    if not paths["intake_md"].is_file() or not paths["questions_md"].is_file():
        raise FileNotFoundError(
            "intake templates missing; run ws product-intake --product <product_id> --confirm first"
        )

    if paths["answers_md"].exists() and not overwrite:
        raise FileExistsError(f"answers file already exists: {paths['answers_md'].name}")

    product_type = str(persisted.get("product_type", "")).strip()
    question_bank = get_question_bank(product_type)
    parsed_answers = parse_answers_text(answers_text)
    normalized_answers = validate_answers(persisted, question_bank, parsed_answers)
    classification = classify_intake_state(persisted, question_bank, normalized_answers)

    timestamp = _utc_now_iso()
    updated_record = _prepare_updated_record(
        persisted,
        classification=classification,
        timestamp=timestamp,
    )

    answers_md = render_answers_md(
        updated_record,
        question_bank,
        normalized_answers,
        classification,
    )
    paths["answers_md"].write_text(answers_md, encoding="utf-8")
    product_file = save_product(updated_record, root, confirm=True, allow_overwrite=True)
    _append_action_log(
        paths["action_log"],
        timestamp=timestamp,
        message=(
            "answers imported via ws product-answer-import --confirm "
            f"(state={state_before}->{classification['state_after']})"
        ),
    )

    return {
        "product_id": product_id,
        "state_before": state_before,
        "state_after": classification["state_after"],
        "unresolved_required": list(classification["unresolved_required"]),
        "unresolved_blocking": list(classification["unresolved_blocking"]),
        "unresolved_privacy": list(classification["unresolved_privacy"]),
        "unresolved_all": list(classification["unresolved_all"]),
        "open_question_count": len(classification["unresolved_all"]),
        "answers_path": str(paths["answers_md"]),
        "product_file": str(product_file),
        "action_log_updated": paths["action_log"].is_file(),
        "action_log_path": str(paths["action_log"]),
        "used_model_provider_agent": False,
    }
