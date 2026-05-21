#!/usr/bin/env python3
"""Static Product Lane Phase 1 intake question bank helpers.

Phase 1 Slice 1 scope:
- static question bank only
- no model/provider/agent calls
- no file writes
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


SUPPORTED_PRODUCT_TYPES: tuple[str, ...] = (
    "website",
    "webapp",
    "dashboard",
    "automation",
    "job-pack",
    "cover-letter",
    "interview-prep",
    "video-script",
)


def _question(
    *,
    question_id: str,
    prompt: str,
    required: bool,
    category: str,
    blocking: bool,
    privacy: bool,
    applies_to: str,
    help_text: str = "",
) -> dict[str, Any]:
    return {
        "id": question_id,
        "prompt": prompt,
        "required": required,
        "category": category,
        "blocking": blocking,
        "privacy": privacy,
        "help_text": help_text,
        "applies_to": applies_to,
    }


def _pack(
    product_type: str,
    required: list[tuple[str, str]],
    optional: list[tuple[str, str]],
    blocking: list[tuple[str, str]],
    privacy: list[tuple[str, str]],
    completion_criteria: list[str],
) -> dict[str, Any]:
    return {
        "required": [
            _question(
                question_id=question_id,
                prompt=prompt,
                required=True,
                category="required",
                blocking=False,
                privacy=False,
                applies_to=product_type,
            )
            for question_id, prompt in required
        ],
        "optional": [
            _question(
                question_id=question_id,
                prompt=prompt,
                required=False,
                category="optional",
                blocking=False,
                privacy=False,
                applies_to=product_type,
            )
            for question_id, prompt in optional
        ],
        "blocking": [
            _question(
                question_id=question_id,
                prompt=prompt,
                required=True,
                category="blocking",
                blocking=True,
                privacy=False,
                applies_to=product_type,
                help_text="Unresolved blocking questions prevent scope lock.",
            )
            for question_id, prompt in blocking
        ],
        "privacy": [
            _question(
                question_id=question_id,
                prompt=prompt,
                required=True,
                category="privacy",
                blocking=False,
                privacy=True,
                applies_to=product_type,
                help_text="Privacy questions must be answered before scope lock.",
            )
            for question_id, prompt in privacy
        ],
        "completion_criteria": completion_criteria[:],
    }


QUESTION_BANK: dict[str, dict[str, Any]] = {
    "website": _pack(
        product_type="website",
        required=[
            ("website.goal", "What is the primary business or communication goal of the website?"),
            ("website.audience", "Who is the target audience?"),
            ("website.primary_pages", "Which pages or sections are in scope for v1?"),
            ("website.conversion", "What action should visitors take?"),
            ("website.content_sources", "What content already exists and what must be written?"),
            ("website.success_criteria", "How will the operator know the site is successful?"),
        ],
        optional=[
            (
                "website.brand_constraints",
                "Are there brand, tone, color, typography, or asset constraints?",
            ),
            ("website.seo", "Are SEO titles, descriptions, or content keywords required?"),
            ("website.analytics", "Is analytics or tracking required?"),
            ("website.hosting", "Is a hosting/deployment target known?"),
        ],
        blocking=[
            ("website.blocking_content", "Is any required page content missing?"),
            (
                "website.blocking_assets",
                "Are required logos, product images, or legal assets missing?",
            ),
            (
                "website.blocking_approval",
                "Is external approval required before scope can lock?",
            ),
        ],
        privacy=[
            (
                "website.privacy_sensitive_content",
                "Does the site include personal contact details, private portfolio material, or client-confidential work?",
            ),
            (
                "website.privacy_handoff_exclusions",
                "Should any page or asset be excluded from cloud handoff in later phases?",
            ),
        ],
        completion_criteria=[
            "Goal, audience, primary pages, conversion action, and success criteria are answered.",
            "Missing content/assets are either resolved or recorded as blockers.",
        ],
    ),
    "webapp": _pack(
        product_type="webapp",
        required=[
            ("webapp.goal", "What problem does the web app solve?"),
            ("webapp.users", "Who are the primary users and what are their roles?"),
            ("webapp.core_workflows", "What are the core workflows in v1?"),
            ("webapp.data_model", "What data does the app create, read, update, or delete?"),
            ("webapp.auth", "Does v1 require authentication or user accounts?"),
            ("webapp.success_criteria", "What must work for v1 to be considered useful?"),
        ],
        optional=[
            ("webapp.integrations", "What external services or APIs are needed?"),
            ("webapp.permissions", "Are role-based permissions required?"),
            ("webapp.offline", "Does the app need offline/local-only behavior?"),
            ("webapp.deployment", "Where will it run in v1?"),
        ],
        blocking=[
            ("webapp.blocking_auth", "Is the auth requirement unclear enough to block scope?"),
            (
                "webapp.blocking_data",
                "Are required data sources unavailable or unsafe to inspect?",
            ),
            (
                "webapp.blocking_integrations",
                "Are required external integrations unknown or unapproved?",
            ),
        ],
        privacy=[
            (
                "webapp.privacy_sensitive_data",
                "Will the app store personal, private, regulated, or credential-like data?",
            ),
            (
                "webapp.privacy_handoff_exclusions",
                "Should any user data be excluded from future model/provider context?",
            ),
        ],
        completion_criteria=[
            "Users, workflows, data model, auth stance, and success criteria are clear.",
            "Unresolved integration or data blockers are recorded.",
        ],
    ),
    "dashboard": _pack(
        product_type="dashboard",
        required=[
            ("dashboard.goal", "What decisions should the dashboard support?"),
            ("dashboard.audience", "Who reads or operates the dashboard?"),
            (
                "dashboard.metrics",
                "Which metrics, statuses, or entities must appear in v1?",
            ),
            ("dashboard.sources", "What data sources feed the dashboard?"),
            ("dashboard.refresh", "How fresh does the data need to be?"),
            (
                "dashboard.success_criteria",
                "What makes the dashboard operationally useful?",
            ),
        ],
        optional=[
            ("dashboard.filters", "What filters or drilldowns are needed?"),
            ("dashboard.alerts", "Are warnings, thresholds, or alerts needed?"),
            ("dashboard.export", "Is export or reporting required?"),
            ("dashboard.display", "Where will the dashboard be viewed?"),
        ],
        blocking=[
            ("dashboard.blocking_sources", "Are any required data sources unavailable?"),
            (
                "dashboard.blocking_definitions",
                "Are key metric definitions unresolved?",
            ),
            ("dashboard.blocking_access", "Is access to data blocked or unsafe?"),
        ],
        privacy=[
            (
                "dashboard.privacy_sensitive_data",
                "Does the dashboard expose private, financial, customer, employment, or credential-adjacent data?",
            ),
            (
                "dashboard.privacy_handoff_exclusions",
                "Should any data source be excluded from cloud/provider handoff later?",
            ),
        ],
        completion_criteria=[
            "Audience, core metrics, data sources, refresh expectations, and success criteria are answered.",
            "Unavailable data sources are blockers.",
        ],
    ),
    "automation": _pack(
        product_type="automation",
        required=[
            ("automation.goal", "What repeated task should be automated?"),
            ("automation.trigger", "How is the automation triggered?"),
            ("automation.inputs", "What inputs does it read?"),
            ("automation.outputs", "What outputs or side effects does it produce?"),
            ("automation.safety", "What must never be changed or deleted?"),
            (
                "automation.success_criteria",
                "How will safe completion be verified?",
            ),
        ],
        optional=[
            ("automation.schedule", "Is a schedule needed?"),
            ("automation.rollback", "Is rollback or undo needed?"),
            ("automation.logging", "What logs or audit trail should be kept?"),
            ("automation.permissions", "What permissions are required?"),
        ],
        blocking=[
            ("automation.blocking_write_scope", "Is the write scope unclear?"),
            (
                "automation.blocking_confirmation",
                "Does the automation need confirmation UX before any write?",
            ),
            (
                "automation.blocking_permissions",
                "Are required permissions unavailable?",
            ),
        ],
        privacy=[
            (
                "automation.privacy_sensitive_inputs",
                "Does the automation read secrets, credentials, private files, large datasets, or raw model output?",
            ),
            (
                "automation.privacy_forbidden_paths",
                "Should any input path be forbidden by default?",
            ),
        ],
        completion_criteria=[
            "Trigger, inputs, outputs, write scope, safety constraints, and verification criteria are clear.",
            "Unsafe or ambiguous write scope blocks scope lock.",
        ],
    ),
    "job-pack": _pack(
        product_type="job-pack",
        required=[
            ("job_pack.goal", "What job application outcome is this pack for?"),
            (
                "job_pack.target_role",
                "What role, company, or role family is being targeted?",
            ),
            (
                "job_pack.materials",
                "Which materials are in scope: resume bullets, cover letter, interview notes, portfolio summary, or outreach?",
            ),
            ("job_pack.source_material", "What source material may be used?"),
            ("job_pack.voice", "What voice and positioning should the pack use?"),
            (
                "job_pack.success_criteria",
                "What makes the pack ready to use?",
            ),
        ],
        optional=[
            ("job_pack.deadline", "Is there an application deadline?"),
            (
                "job_pack.constraints",
                "Are there claims, skills, or employers that must not be mentioned?",
            ),
            (
                "job_pack.versions",
                "Are multiple role/company variants needed?",
            ),
            ("job_pack.links", "Are portfolio or LinkedIn links in scope?"),
        ],
        blocking=[
            ("job_pack.blocking_source", "Is required source material missing?"),
            ("job_pack.blocking_claims", "Are factual claims unverified?"),
            (
                "job_pack.blocking_privacy",
                "Is private employment material present without an explicit privacy stance?",
            ),
        ],
        privacy=[
            (
                "job_pack.privacy_default_private",
                "Confirm this product is private: true unless explicitly overridden.",
            ),
            (
                "job_pack.privacy_sensitive_fields",
                "What personal data, employer names, salary details, or contact details are included?",
            ),
            (
                "job_pack.privacy_handoff_block",
                "Should all cloud/model/provider handoffs remain blocked for this product until a future explicit confirmation flow exists?",
            ),
        ],
        completion_criteria=[
            "Target role, materials, allowed source material, voice, privacy stance, and success criteria are answered.",
            "Unverified personal claims remain blockers.",
        ],
    ),
    "cover-letter": _pack(
        product_type="cover-letter",
        required=[
            ("cover_letter.goal", "What application is this cover letter for?"),
            (
                "cover_letter.company_role",
                "What company and role is being targeted?",
            ),
            (
                "cover_letter.key_fit",
                "What two or three points prove fit for the role?",
            ),
            (
                "cover_letter.source_material",
                "What resume or background material may be used?",
            ),
            ("cover_letter.tone", "What tone should the letter use?"),
            (
                "cover_letter.success_criteria",
                "What makes the letter ready to send?",
            ),
        ],
        optional=[
            (
                "cover_letter.length",
                "Is there a length or format requirement?",
            ),
            (
                "cover_letter.referral",
                "Is there a referral, recruiter, or contact to mention?",
            ),
            (
                "cover_letter.constraints",
                "Are there topics or claims to avoid?",
            ),
            ("cover_letter.deadline", "Is there a deadline?"),
        ],
        blocking=[
            ("cover_letter.blocking_role", "Is the target role/company unknown?"),
            (
                "cover_letter.blocking_claims",
                "Are key claims unsupported by source material?",
            ),
            (
                "cover_letter.blocking_privacy",
                "Is private personal data present without confirmation?",
            ),
        ],
        privacy=[
            (
                "cover_letter.privacy_default_private",
                "Confirm this product is private: true unless explicitly overridden.",
            ),
            (
                "cover_letter.privacy_sensitive_fields",
                "Does the letter include address, phone, salary, employer-confidential, immigration, or health/personal details?",
            ),
            (
                "cover_letter.privacy_handoff_block",
                "Should cloud handoff remain unavailable for this product in Phase 1?",
            ),
        ],
        completion_criteria=[
            "Company/role, fit points, source material, tone, and privacy stance are answered.",
            "Unsupported claims block scope lock.",
        ],
    ),
    "interview-prep": _pack(
        product_type="interview-prep",
        required=[
            (
                "interview_prep.goal",
                "What interview or assessment is being prepared for?",
            ),
            (
                "interview_prep.role_context",
                "What role, company, and interview stage are in scope?",
            ),
            (
                "interview_prep.focus_areas",
                "Which skills, topics, stories, or exercises need preparation?",
            ),
            (
                "interview_prep.source_material",
                "What resume, job description, or notes may be used?",
            ),
            (
                "interview_prep.output_format",
                "What should the final prep artifact contain?",
            ),
            (
                "interview_prep.success_criteria",
                "What makes the prep useful?",
            ),
        ],
        optional=[
            ("interview_prep.schedule", "When is the interview?"),
            (
                "interview_prep.interviewers",
                "Are interviewer names or roles known?",
            ),
            (
                "interview_prep.practice",
                "Are practice questions, STAR stories, or drills needed?",
            ),
            (
                "interview_prep.constraints",
                "Are any topics off-limits?",
            ),
        ],
        blocking=[
            (
                "interview_prep.blocking_role",
                "Is the role/stage unclear?",
            ),
            (
                "interview_prep.blocking_source",
                "Is required job description or resume material missing?",
            ),
            (
                "interview_prep.blocking_privacy",
                "Is private personal or employer data present without confirmation?",
            ),
        ],
        privacy=[
            (
                "interview_prep.privacy_default_private",
                "Confirm this product is private: true unless explicitly overridden.",
            ),
            (
                "interview_prep.privacy_sensitive_fields",
                "Does this include personal history, salary, employer-confidential work, or interviewer details?",
            ),
            (
                "interview_prep.privacy_handoff_block",
                "Should all cloud/provider handoffs remain blocked until a future explicit privacy confirmation exists?",
            ),
        ],
        completion_criteria=[
            "Role context, focus areas, source material, output format, privacy stance, and success criteria are answered.",
            "Missing job description or resume source material blocks scope lock.",
        ],
    ),
    "video-script": _pack(
        product_type="video-script",
        required=[
            ("video_script.goal", "What is the purpose of the video?"),
            ("video_script.audience", "Who is the target viewer?"),
            (
                "video_script.format",
                "What format is needed: short, tutorial, demo, explainer, ad, or narration?",
            ),
            ("video_script.key_points", "What key points must be covered?"),
            (
                "video_script.call_to_action",
                "What should the viewer do next?",
            ),
            (
                "video_script.success_criteria",
                "What makes the script usable?",
            ),
        ],
        optional=[
            ("video_script.length", "Target length or word count?"),
            ("video_script.tone", "Tone, pacing, and style?"),
            (
                "video_script.visuals",
                "Are visual beats, captions, or scene notes needed?",
            ),
            (
                "video_script.references",
                "Are there reference videos or examples?",
            ),
        ],
        blocking=[
            (
                "video_script.blocking_audience",
                "Is the audience or purpose unclear?",
            ),
            (
                "video_script.blocking_claims",
                "Are factual claims unsupported?",
            ),
            (
                "video_script.blocking_assets",
                "Are required product visuals, screenshots, or legal approvals missing?",
            ),
        ],
        privacy=[
            (
                "video_script.privacy_sensitive_content",
                "Does the script include personal details, client material, unreleased product details, or confidential claims?",
            ),
            (
                "video_script.privacy_handoff_exclusions",
                "Should any references be excluded from later cloud/provider handoff?",
            ),
        ],
        completion_criteria=[
            "Purpose, audience, format, key points, call to action, and success criteria are answered.",
            "Unsupported claims or missing required assets are blockers.",
        ],
    ),
}


def _ensure_supported(product_type: str) -> None:
    if product_type not in QUESTION_BANK:
        supported = ", ".join(SUPPORTED_PRODUCT_TYPES)
        raise ValueError(f"unsupported product_type: {product_type!r}. supported: {supported}")


def get_supported_product_types() -> list[str]:
    return list(SUPPORTED_PRODUCT_TYPES)


def get_question_bank(product_type: str) -> list[dict[str, Any]]:
    _ensure_supported(product_type)
    section = QUESTION_BANK[product_type]
    items = (
        section["required"]
        + section["optional"]
        + section["blocking"]
        + section["privacy"]
    )
    return deepcopy(items)


def get_required_questions(product_type: str) -> list[dict[str, Any]]:
    _ensure_supported(product_type)
    return deepcopy(QUESTION_BANK[product_type]["required"])


def get_optional_questions(product_type: str) -> list[dict[str, Any]]:
    _ensure_supported(product_type)
    return deepcopy(QUESTION_BANK[product_type]["optional"])


def get_blocking_questions(product_type: str) -> list[dict[str, Any]]:
    _ensure_supported(product_type)
    return deepcopy(QUESTION_BANK[product_type]["blocking"])


def get_privacy_questions(product_type: str) -> list[dict[str, Any]]:
    _ensure_supported(product_type)
    return deepcopy(QUESTION_BANK[product_type]["privacy"])


def get_completion_criteria(product_type: str) -> list[str]:
    _ensure_supported(product_type)
    return list(QUESTION_BANK[product_type]["completion_criteria"])


def validate_question_bank() -> list[str]:
    errors: list[str] = []
    if set(SUPPORTED_PRODUCT_TYPES) != set(QUESTION_BANK):
        errors.append("supported product type list does not match question bank keys")

    required_fields = {
        "id",
        "prompt",
        "required",
        "category",
        "blocking",
        "privacy",
        "help_text",
        "applies_to",
    }

    for product_type in SUPPORTED_PRODUCT_TYPES:
        if product_type not in QUESTION_BANK:
            errors.append(f"missing question pack for {product_type}")
            continue

        pack = QUESTION_BANK[product_type]
        ids: set[str] = set()
        required_questions = pack["required"]
        if not required_questions:
            errors.append(f"{product_type}: missing required questions")

        combined = (
            pack["required"] + pack["optional"] + pack["blocking"] + pack["privacy"]
        )
        for question in combined:
            missing = required_fields - set(question)
            if missing:
                errors.append(
                    f"{product_type}: question missing fields {sorted(missing)}"
                )
                continue

            question_id = question["id"]
            if not isinstance(question_id, str) or not question_id:
                errors.append(f"{product_type}: question id must be non-empty string")
            elif question_id in ids:
                errors.append(f"{product_type}: duplicate question id {question_id}")
            else:
                ids.add(question_id)

            if not isinstance(question["prompt"], str) or not question["prompt"]:
                errors.append(f"{product_type}: {question_id} prompt must be non-empty string")
            if not isinstance(question["required"], bool):
                errors.append(f"{product_type}: {question_id} required must be boolean")
            if not isinstance(question["blocking"], bool):
                errors.append(f"{product_type}: {question_id} blocking must be boolean")
            if not isinstance(question["privacy"], bool):
                errors.append(f"{product_type}: {question_id} privacy must be boolean")
            if question.get("applies_to") != product_type:
                errors.append(f"{product_type}: {question_id} applies_to mismatch")

    return errors


def render_questions(product_type: str, format: str = "markdown") -> str:
    _ensure_supported(product_type)
    if format not in {"markdown", "text"}:
        raise ValueError("format must be 'markdown' or 'text'")

    required = get_required_questions(product_type)
    optional = get_optional_questions(product_type)
    blocking = get_blocking_questions(product_type)
    privacy = get_privacy_questions(product_type)

    if format == "text":
        lines = [
            f"DRY RUN - Product questions preview ({product_type})",
            "Static question bank only. No files written. No model/provider/agent calls.",
            "",
        ]

        def emit_text(title: str, items: list[dict[str, Any]]) -> None:
            lines.append(f"{title}:")
            for item in items:
                lines.append(f"- [{item['id']}] {item['prompt']}")
            lines.append("")

        emit_text("Required", required)
        emit_text("Optional", optional)
        emit_text("Blocking", blocking)
        emit_text("Privacy", privacy)
        return "\n".join(lines).rstrip() + "\n"

    lines = [
        f"# Product Intake Questions: {product_type}",
        "",
        "DRY RUN - static question bank preview only.",
        "",
        "- No files written.",
        "- No model/provider/agent calls.",
        "",
    ]

    def emit_markdown(title: str, items: list[dict[str, Any]]) -> None:
        lines.append(f"## {title}")
        lines.append("")
        for item in items:
            lines.append(f"- `{item['id']}`: {item['prompt']}")
        lines.append("")

    emit_markdown("Required Questions", required)
    emit_markdown("Optional Questions", optional)
    emit_markdown("Blocking Questions", blocking)
    emit_markdown("Privacy Questions", privacy)
    return "\n".join(lines).rstrip() + "\n"


def render_intake_preview(product_record_or_type: dict[str, Any] | str) -> str:
    if isinstance(product_record_or_type, dict):
        product_type = str(product_record_or_type.get("product_type", "")).strip()
        product_id = str(product_record_or_type.get("product_id", "")).strip()
        label = str(product_record_or_type.get("label", "")).strip()
        private = product_record_or_type.get("private")
    else:
        product_type = str(product_record_or_type).strip()
        product_id = ""
        label = ""
        private = None

    _ensure_supported(product_type)
    required = get_required_questions(product_type)
    blocking = get_blocking_questions(product_type)
    privacy = get_privacy_questions(product_type)
    completion = get_completion_criteria(product_type)

    lines = [
        f"# Product Intake Preview: {product_type}",
        "",
        "DRY RUN - Phase 1 Slice 1 preview only.",
        "",
        "- No files written.",
        "- No product state updates.",
        "- No model/provider/agent calls.",
        "",
        "Future apply-mode artifacts (not implemented in this slice):",
        "- `products/<product_id>/intake.md`",
        "- `products/<product_id>/questions.md`",
        "- `products/<product_id>/answers.md`",
        "",
    ]

    if product_id:
        lines.append(f"- Product ID: `{product_id}`")
    if label:
        lines.append(f"- Label: {label}")
    if private is not None:
        lines.append(f"- Private: `{private}`")
    if product_id or label or private is not None:
        lines.append("")

    lines.extend(
        [
            f"- Required question count: `{len(required)}`",
            f"- Blocking question count: `{len(blocking)}`",
            f"- Privacy question count: `{len(privacy)}`",
            "",
            "Completion criteria:",
        ]
    )
    for item in completion:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)

