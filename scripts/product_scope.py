#!/usr/bin/env python3
"""Product Lane Phase 1 Slice 4 scope preview helpers.

Scope:
- deterministic no-write scope draft rendering
- reads only product.yaml + intake/question metadata + answers.md
- refuses non-SCOPE_READY or unresolved required/blocking/privacy answers
- no model/provider/agent calls
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from product_answer_import import ANSWERS_FILENAME, unanswered_required_questions
from product_intake_artifacts import INTAKE_FILENAME, QUESTIONS_FILENAME
from product_intake_questions import get_question_bank
from product_registry import PRODUCT_FILENAME, get_product_status, product_dir, validate_product_id


SCOPE_DRY_RUN_ACTION = "ws product-scope --dry-run"
SCOPE_READY_STATE = "SCOPE_READY"


def _safe_child(base: Path, child: Path) -> Path:
    base_resolved = base.resolve()
    child_resolved = child.resolve()
    if child_resolved == base_resolved:
        return child_resolved
    if base_resolved not in child_resolved.parents:
        raise ValueError(f"path escapes expected base: {child_resolved} not under {base_resolved}")
    return child_resolved


def scope_paths(root: str | Path, product_id: str) -> dict[str, Path]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")
    target_dir = product_dir(root, product_id)
    return {
        "product_dir": target_dir,
        "product_file": _safe_child(target_dir, target_dir / PRODUCT_FILENAME),
        "intake_md": _safe_child(target_dir, target_dir / INTAKE_FILENAME),
        "questions_md": _safe_child(target_dir, target_dir / QUESTIONS_FILENAME),
        "answers_md": _safe_child(target_dir, target_dir / ANSWERS_FILENAME),
    }


def classify_missing_scope_inputs(
    product_record: dict[str, Any],
    product_dir_path: str | Path,
) -> dict[str, Any]:
    directory = Path(product_dir_path).resolve()
    files = {
        PRODUCT_FILENAME: _safe_child(directory, directory / PRODUCT_FILENAME).is_file(),
        INTAKE_FILENAME: _safe_child(directory, directory / INTAKE_FILENAME).is_file(),
        QUESTIONS_FILENAME: _safe_child(directory, directory / QUESTIONS_FILENAME).is_file(),
        ANSWERS_FILENAME: _safe_child(directory, directory / ANSWERS_FILENAME).is_file(),
    }
    return {
        "product_id": str(product_record.get("product_id", "")).strip(),
        "state": str(product_record.get("state", "")).strip(),
        "files": files,
        "missing_files": [name for name, exists in files.items() if not exists],
    }


QUESTION_HEADER_RE = re.compile(r"^### `([^`]+)`\s*$")


def parse_answers_md(text: str) -> dict[str, str]:
    if not isinstance(text, str):
        raise ValueError("answers.md text must be a string")

    answers: dict[str, str] = {}
    current_question_id: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = QUESTION_HEADER_RE.match(line)
        if match:
            current_question_id = match.group(1).strip()
            continue
        if current_question_id is None:
            continue
        if not line.startswith("Answer:"):
            continue
        answer = line.split(":", 1)[1].strip()
        if answer == "(unanswered)":
            answer = ""
        if current_question_id in answers:
            raise ValueError(f"duplicate question_id in answers.md: {current_question_id}")
        answers[current_question_id] = answer
        current_question_id = None
    return answers


def validate_scope_ready(
    product_record: dict[str, Any],
    answers: dict[str, str],
    question_bank: list[dict[str, Any]],
) -> dict[str, list[str]]:
    state = str(product_record.get("state", "")).strip()
    if state != SCOPE_READY_STATE:
        raise ValueError(
            f"product must be in {SCOPE_READY_STATE} for scope preview "
            f"(found {state or 'UNKNOWN'})"
        )

    unresolved = unanswered_required_questions(product_record, question_bank, answers)
    if unresolved["all"]:
        unresolved_text = ", ".join(unresolved["all"])
        raise ValueError(
            "cannot render scope preview with unresolved required/blocking/privacy questions: "
            f"{unresolved_text}"
        )
    return unresolved


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


def _collect_answer_values(
    answers: dict[str, str],
    ids: list[str],
) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for question_id in ids:
        answer = str(answers.get(question_id, "")).strip()
        if not answer:
            continue
        if answer in seen:
            continue
        values.append(answer)
        seen.add(answer)
    return values


def summarize_answers_by_category(
    product_type: str,
    question_bank: list[dict[str, Any]],
    answers: dict[str, str],
) -> dict[str, list[dict[str, Any]]]:
    del product_type  # categories are encoded in question metadata.
    summary: dict[str, list[dict[str, Any]]] = {
        "required": [],
        "blocking": [],
        "privacy": [],
        "optional": [],
    }
    for question in question_bank:
        question_id = str(question.get("id", "")).strip()
        if not question_id:
            continue
        category = str(question.get("category", "")).strip().lower()
        if category not in summary:
            continue
        answer = str(answers.get(question_id, "")).strip()
        summary[category].append(
            {
                "id": question_id,
                "prompt": str(question.get("prompt", "")).strip(),
                "answer": answer,
                "answered": bool(answer),
            }
        )
    return summary


def _render_section_lines(title: str, values: list[str]) -> list[str]:
    lines = [f"## {title}", ""]
    if values:
        for value in values:
            lines.append(f"- {value}")
    else:
        lines.append("- TODO/UNKNOWN")
    lines.append("")
    return lines


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


def render_scope_draft(
    product_record: dict[str, Any],
    question_bank: list[dict[str, Any]],
    answers: dict[str, str],
    *,
    source_status: dict[str, Any] | None = None,
) -> str:
    product_id = str(product_record.get("product_id", "")).strip()
    product_type = str(product_record.get("product_type", "")).strip()
    label = str(product_record.get("label", "")).strip() or product_id
    state = str(product_record.get("state", "")).strip() or "UNKNOWN"
    private_value = bool(product_record.get("private", False))

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
    success_values = _section_values(
        question_bank,
        answers,
        include_tokens=(".success_criteria",),
    )
    privacy_values = _section_values(
        question_bank,
        answers,
        include_tokens=(".privacy_", ".privacy"),
    )

    assumptions_values: list[str] = []
    explicit_non_goal_values = out_of_scope_values[:]

    unresolved_sections: list[str] = []
    section_pairs = (
        ("Goal / Core Intent", goal_values),
        ("Target User / Audience", audience_values),
        ("In Scope", in_scope_values),
        ("Out of Scope", out_of_scope_values),
        ("Constraints", constraint_values),
        ("Assumptions", assumptions_values),
        ("Dependencies", dependency_values),
        ("Privacy Level", privacy_values),
        ("Success Criteria", success_values),
        ("Explicit Non-Goals", explicit_non_goal_values),
    )
    for section_name, values in section_pairs:
        if not values:
            unresolved_sections.append(section_name)

    source_files = source_status.get("files", {}) if source_status else {}

    lines: list[str] = [
        f"# Scope Draft Preview: {label}",
        "",
        "DRY RUN - no files written.",
        "No product state changes.",
        "No model/provider/agent calls.",
        "",
        f"- product_id: `{product_id}`",
        f"- product_type: `{product_type}`",
        f"- label: {label}",
        f"- current_state: `{state}`",
        f"- private: `{private_value}`",
        "",
    ]

    lines.extend(_render_section_lines("Goal / Core Intent", goal_values))
    lines.extend(_render_section_lines("Target User / Audience", audience_values))
    lines.extend(_render_section_lines("In Scope", in_scope_values))
    lines.extend(_render_section_lines("Out of Scope", out_of_scope_values))
    lines.extend(_render_section_lines("Constraints", constraint_values))
    lines.extend(_render_section_lines("Assumptions", assumptions_values))
    lines.extend(_render_section_lines("Dependencies", dependency_values))

    privacy_level_values = privacy_values[:]
    if not privacy_level_values:
        privacy_level_values = ["private" if private_value else "standard"]
    lines.extend(_render_section_lines("Privacy Level", privacy_level_values))

    lines.extend(_render_section_lines("Success Criteria", success_values))
    lines.extend(_render_section_lines("Explicit Non-Goals", explicit_non_goal_values))

    lines.append("## Unanswered / Unknown Fields")
    lines.append("")
    if unresolved_sections:
        for section_name in unresolved_sections:
            lines.append(f"- {section_name}")
    else:
        lines.append("- None")
    lines.append("")

    lines.extend(
        [
            "## Generated From",
            "",
            f"- product.yaml ({'available' if source_files.get(PRODUCT_FILENAME) else 'missing'})",
            f"- intake.md ({'available' if source_files.get(INTAKE_FILENAME) else 'missing'})",
            f"- questions.md ({'available' if source_files.get(QUESTIONS_FILENAME) else 'missing'})",
            f"- answers.md ({'available' if source_files.get(ANSWERS_FILENAME) else 'missing'})",
            "",
            "## Next Step",
            "",
            "- Future write-mode scope commands are not implemented in Phase 1 Slice 4.",
            "- Review this preview and keep intake answers updated for later guarded lock flow.",
            f"- Preview command used: `{SCOPE_DRY_RUN_ACTION} --product <product_id>`",
            "",
        ]
    )
    return "\n".join(lines)


def load_product_scope_inputs(root: str | Path, product_id: str) -> dict[str, Any]:
    if not validate_product_id(product_id):
        raise ValueError(f"invalid product_id: {product_id!r}")

    paths = scope_paths(root, product_id)
    product_record = get_product_status(root, product_id)
    product_type = str(product_record.get("product_type", "")).strip()
    question_bank = get_question_bank(product_type)

    source_status = classify_missing_scope_inputs(product_record, paths["product_dir"])
    if not source_status["files"].get(ANSWERS_FILENAME):
        raise FileNotFoundError(
            "answers.md is missing; run ws product-answer-import --product <product_id> --file <answers_file> --confirm first"
        )

    answers_md_text = paths["answers_md"].read_text(encoding="utf-8")
    answers = parse_answers_md(answers_md_text)

    known_ids = {
        str(question.get("id", "")).strip()
        for question in question_bank
        if str(question.get("id", "")).strip()
    }
    unknown_answer_ids = sorted(question_id for question_id in answers if question_id not in known_ids)
    if unknown_answer_ids:
        raise ValueError(
            "answers.md contains unknown question_id(s): " + ", ".join(unknown_answer_ids)
        )

    validate_scope_ready(product_record, answers, question_bank)
    return {
        "product_record": product_record,
        "question_bank": question_bank,
        "answers": answers,
        "paths": paths,
        "source_status": source_status,
    }
