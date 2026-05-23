#!/usr/bin/env python3
"""Deterministic no-write Product Lane implementation exchange preview helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from product_implementation_plan_review import (
    review_implementation_plan_text,
    validate_implementation_plan_review_preconditions,
)


ALLOWED_TARGETS = {"codex_cli", "gemini_cli", "local_ollama"}


def render_implementation_exchange_preview(
    root: str | Path,
    product_id: str,
    target: str,
) -> str:
    if target not in ALLOWED_TARGETS:
        raise ValueError(f"unsupported target: {target!r}. allowed: {', '.join(sorted(ALLOWED_TARGETS))}")

    payload = validate_implementation_plan_review_preconditions(root, product_id)
    review_result = review_implementation_plan_text(
        payload["product_record"],
        payload["impl_plan_text"],
        payload_extras=payload,
    )

    if review_result["status"] != "PASS":
        raise ValueError(
            f"implementation exchange preview requires implementation plan review PASS (found {review_result['status']})"
        )

    product_record = payload["product_record"]
    label = str(product_record.get("label", "")).strip() or product_id
    
    summary = f"Implement {label} from approved implementation plan"
    
    lines = [
        "Implementation Exchange Preview",
        "===============================",
        "",
        "DRY RUN / no files written",
        "",
        f"- product_id: `{product_id}`",
        f"- target: `{target}`",
        "",
        "Source Artifacts:",
        f"- active_scope_lock: `{payload['active_scope_lock']}`",
        f"- active_prd: `{payload['active_prd']}`",
        f"- active_wireframe: `{payload['active_wireframe']}`",
        f"- active_technical_plan: `{payload['active_technical_plan']}`",
        f"- active_implementation_plan: `{product_record.get('active_implementation_plan', '')}`",
        "",
        "Proposed Exchange Summary:",
        f"\"{summary}\"",
        "",
        "Proposed Safety Mode:",
        "REVIEW_ONLY (first handoff)",
        "",
        "Proposed Task Type:",
        "implementation_review",
        "",
        "Forbidden Actions:",
        "- no direct product artifact mutation",
        "- no source/app changes in preview",
        "- no apply without future approval",
        "",
        "Proposed Future Command:",
        f"ws exchange-new --target {target} --task-type implementation_review --summary \"{summary}\" --safety-mode REVIEW_ONLY --dry-run",
        "",
        "Ready for handoff: YES",
    ]
    return "\n".join(lines)
