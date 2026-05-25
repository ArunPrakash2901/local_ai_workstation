#!/usr/bin/env python3
"""Convert phase-wise Markdown research reports into bounded handoff packets.

Discovery Lane starts after manual ChatGPT/Gemini discovery and Deep Research.
This tool does not research, call models, execute commands from reports, or move
source files. It compresses already-created Markdown reports into deterministic
local artifacts for human review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


STATUS_READY = "READY_FOR_HUMAN_REVIEW"
STATUS_NEEDS_DECISION = "NEEDS_HUMAN_DECISION"
STATUS_NOT_READY = "NOT_EXECUTION_READY"

OUTPUT_DIRS = (
    "phase_packets",
    "worker_prompts",
    "manifests",
)

REQUIRED_SECTIONS = {
    "phase_id",
    "phase_title",
    "product_context",
    "objective",
    "scope",
    "non_goals",
    "functional_requirements",
    "technical_requirements",
    "implementation_tasks",
    "validation_test_strategy",
    "acceptance_criteria",
    "open_questions",
}

RECOMMENDED_SECTIONS = {
    "assumptions",
    "user_operator_workflow",
    "architecture_guidance",
    "data_file_state_requirements",
    "ui_ux_wireframe_guidance",
    "parallel_workstreams",
    "dependencies",
    "risks",
    "sources_references",
}

PACKET_SECTION_LABELS = {
    "phase_id": "Phase ID",
    "phase_title": "Phase Title",
    "product_context": "Product Context",
    "objective": "Objective",
    "scope": "In Scope",
    "non_goals": "Out of Scope",
    "assumptions": "Assumptions",
    "functional_requirements": "Functional Requirements",
    "technical_requirements": "Technical Requirements",
    "architecture_guidance": "Architecture Notes",
    "data_file_state_requirements": "Data / State / File Requirements",
    "ui_ux_wireframe_guidance": "UX / Wireframe Notes",
    "implementation_tasks": "Implementation Plan",
    "parallel_workstreams": "Suggested Parallel Workstreams",
    "dependencies": "Dependencies",
    "risks": "Risks",
    "validation_test_strategy": "Validation Plan",
    "acceptance_criteria": "Acceptance Criteria",
}

ALIASES: Dict[str, List[Tuple[str, str]]] = {
    "phase_id": [
        ("phase id", "exact"),
        ("phase identifier", "exact"),
        ("phase number", "exact"),
    ],
    "phase_title": [
        ("phase title", "exact"),
        ("phase name", "exact"),
        ("title", "partial"),
    ],
    "product_context": [
        ("product context", "exact"),
        ("context", "partial"),
        ("background", "partial"),
    ],
    "objective": [
        ("objective", "exact"),
        ("objectives", "exact"),
        ("goal", "partial"),
        ("goals", "partial"),
        ("purpose", "partial"),
    ],
    "scope": [
        ("scope", "exact"),
        ("in scope", "exact"),
        ("phase scope", "exact"),
        ("scope of work", "exact"),
    ],
    "non_goals": [
        ("non goals", "exact"),
        ("non-goals", "exact"),
        ("out of scope", "exact"),
        ("exclusions", "partial"),
    ],
    "user_operator_workflow": [
        ("user operator workflow", "exact"),
        ("user / operator workflow", "exact"),
        ("operator workflow", "exact"),
        ("user workflow", "partial"),
        ("workflow", "partial"),
    ],
    "functional_requirements": [
        ("functional requirements", "exact"),
        ("features", "partial"),
        ("capabilities", "partial"),
    ],
    "technical_requirements": [
        ("technical requirements", "exact"),
        ("technical constraints", "partial"),
        ("engineering requirements", "partial"),
    ],
    "architecture_guidance": [
        ("architecture guidance", "exact"),
        ("architecture notes", "exact"),
        ("architecture", "partial"),
        ("system design", "partial"),
    ],
    "data_file_state_requirements": [
        ("data file state requirements", "exact"),
        ("data / file / state requirements", "exact"),
        ("data state file requirements", "exact"),
        ("data requirements", "partial"),
        ("file requirements", "partial"),
        ("state requirements", "partial"),
    ],
    "ui_ux_wireframe_guidance": [
        ("ui ux wireframe guidance", "exact"),
        ("ui / ux / wireframe guidance", "exact"),
        ("ux wireframe guidance", "exact"),
        ("ui ux guidance", "partial"),
        ("wireframe guidance", "partial"),
        ("ui guidance", "partial"),
        ("ux guidance", "partial"),
    ],
    "implementation_tasks": [
        ("implementation tasks", "exact"),
        ("tasks", "partial"),
        ("implementation plan", "partial"),
        ("work plan", "partial"),
    ],
    "parallel_workstreams": [
        ("suggested parallel workstreams", "exact"),
        ("parallel workstreams", "exact"),
        ("workstreams", "partial"),
    ],
    "dependencies": [
        ("dependencies", "exact"),
        ("prerequisites", "partial"),
    ],
    "risks": [
        ("risks", "exact"),
        ("risk assessment", "exact"),
        ("risks and mitigations", "exact"),
    ],
    "validation_test_strategy": [
        ("validation test strategy", "exact"),
        ("validation / test strategy", "exact"),
        ("validation strategy", "exact"),
        ("test strategy", "exact"),
        ("testing strategy", "exact"),
        ("validation plan", "exact"),
        ("tests", "partial"),
    ],
    "acceptance_criteria": [
        ("acceptance criteria", "exact"),
        ("success criteria", "partial"),
        ("definition of done", "partial"),
    ],
    "open_questions": [
        ("open questions", "exact"),
        ("unresolved questions", "exact"),
        ("questions", "partial"),
        ("decisions needed", "partial"),
    ],
    "sources_references": [
        ("sources references", "exact"),
        ("sources / references", "exact"),
        ("references", "exact"),
        ("sources", "exact"),
    ],
    "assumptions": [
        ("assumptions", "exact"),
        ("working assumptions", "exact"),
    ],
}

FRONTMATTER_ALIASES = {
    "phase_id": {"phase_id", "phase", "phase_number", "phase-id"},
    "phase_title": {"phase_title", "title", "phase_name", "phase-title"},
}

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class Section:
    heading: str
    content: str
    quality: str


@dataclass
class ReportAnalysis:
    source_path: Path
    slug: str
    phase_id: str
    phase_title: str
    status: str
    sections: Dict[str, Section]
    missing_required: List[str]
    missing_recommended: List[str]
    partial_sections: List[str]
    human_decision_flags: List[str]
    generated_files: Dict[str, str]
    generated_at: str


def normalize_heading(value: str) -> str:
    lowered = value.strip().lower().replace("&", "and")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", lowered)).strip()


def slugify(value: str) -> str:
    slug = SLUG_RE.sub("_", value.strip().lower()).strip("_")
    return slug or "phase_report"


def slug_from_source(path: Path) -> str:
    stem = slugify(path.stem)
    for suffix in ("_research_report", "_deep_research_report", "_research"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)].strip("_")
    return stem or "phase_report"


def parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end_index: Optional[int] = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break

    if end_index is None:
        return {}, text

    metadata: Dict[str, str] = {}
    for line in lines[1:end_index]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = key.strip().lower().replace("-", "_")
        metadata[normalized_key] = value.strip().strip('"').strip("'")

    remaining = "\n".join(lines[end_index + 1 :])
    return metadata, remaining


def match_heading(heading: str) -> Tuple[Optional[str], Optional[str]]:
    normalized = normalize_heading(heading)
    for canonical, aliases in ALIASES.items():
        for alias, quality in aliases:
            if normalized == normalize_heading(alias):
                return canonical, quality
    return None, None


def parse_sections(text: str) -> Tuple[Dict[str, Section], Optional[str]]:
    sections: Dict[str, Section] = {}
    first_h1: Optional[str] = None
    current_key: Optional[str] = None
    current_heading = ""
    current_quality = "exact"
    current_lines: List[str] = []

    def flush() -> None:
        nonlocal current_key, current_heading, current_quality, current_lines
        if current_key is None:
            current_lines = []
            return
        content = "\n".join(current_lines).strip()
        existing = sections.get(current_key)
        if existing:
            combined = "\n\n".join(part for part in (existing.content, content) if part).strip()
            quality = "exact" if "exact" in {existing.quality, current_quality} else current_quality
            sections[current_key] = Section(existing.heading, combined, quality)
        else:
            sections[current_key] = Section(current_heading, content, current_quality)
        current_key = None
        current_heading = ""
        current_quality = "exact"
        current_lines = []

    for line in text.splitlines():
        heading_match = HEADING_RE.match(line)
        if heading_match:
            flush()
            heading_level, raw_heading = heading_match.groups()
            heading = raw_heading.rstrip("#").strip()
            if heading_level == "#" and first_h1 is None:
                first_h1 = heading
            key, quality = match_heading(heading)
            current_key = key
            current_heading = heading
            current_quality = quality or "exact"
            current_lines = []
            continue
        if current_key is not None:
            current_lines.append(line)

    flush()
    return sections, first_h1


def frontmatter_value(metadata: Dict[str, str], canonical: str) -> Optional[str]:
    keys = FRONTMATTER_ALIASES.get(canonical, set())
    for key in keys:
        normalized = key.replace("-", "_")
        if normalized in metadata and metadata[normalized].strip():
            return metadata[normalized].strip()
    return None


def section_text(sections: Dict[str, Section], canonical: str) -> str:
    section = sections.get(canonical)
    if not section or not section.content.strip():
        label = PACKET_SECTION_LABELS.get(canonical, canonical.replace("_", " ").title())
        return f"NEEDS_HUMAN_DECISION: Missing {label} in source research report."
    return section.content.strip()


def looks_empty_decision(value: str) -> bool:
    cleaned = re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()
    return cleaned in {"", "none", "n a", "na", "not applicable", "no open questions"}


def validate_report(path: Path, text: str, generated_at: str) -> ReportAnalysis:
    metadata, body = parse_frontmatter(text)
    sections, first_h1 = parse_sections(body)
    slug = slug_from_source(path)

    human_decision_flags: List[str] = []

    phase_id = frontmatter_value(metadata, "phase_id") or (
        sections.get("phase_id").content.strip() if sections.get("phase_id") else ""
    )
    if not phase_id:
        phase_id = slug
        human_decision_flags.append("Phase ID was inferred from the report filename.")

    phase_title = frontmatter_value(metadata, "phase_title") or (
        sections.get("phase_title").content.strip() if sections.get("phase_title") else ""
    )
    if not phase_title and first_h1:
        phase_title = first_h1
        human_decision_flags.append("Phase Title was inferred from the first Markdown H1 heading.")
    if not phase_title:
        phase_title = slug.replace("_", " ").title()
        human_decision_flags.append("Phase Title was inferred from the report filename.")

    satisfied_by_metadata = set()
    if frontmatter_value(metadata, "phase_id"):
        satisfied_by_metadata.add("phase_id")
    if frontmatter_value(metadata, "phase_title") or (first_h1 and "phase_title" not in sections):
        satisfied_by_metadata.add("phase_title")
    if "Phase ID was inferred from the report filename." in human_decision_flags:
        satisfied_by_metadata.add("phase_id")
    if "Phase Title was inferred from the first Markdown H1 heading." in human_decision_flags:
        satisfied_by_metadata.add("phase_title")
    if "Phase Title was inferred from the report filename." in human_decision_flags:
        satisfied_by_metadata.add("phase_title")

    missing_required = sorted(
        key
        for key in REQUIRED_SECTIONS
        if key not in satisfied_by_metadata and (key not in sections or not sections[key].content.strip())
    )
    missing_recommended = sorted(
        key for key in RECOMMENDED_SECTIONS if key not in sections or not sections[key].content.strip()
    )
    partial_sections = sorted(key for key, section in sections.items() if section.quality == "partial")

    for key in missing_required:
        human_decision_flags.append(f"Missing required section: {PACKET_SECTION_LABELS.get(key, key)}.")
    for key in missing_recommended:
        human_decision_flags.append(f"Missing recommended section: {PACKET_SECTION_LABELS.get(key, key)}.")
    for key in partial_sections:
        human_decision_flags.append(f"Heading match is partial and needs review: {PACKET_SECTION_LABELS.get(key, key)}.")

    open_questions = sections.get("open_questions")
    if open_questions and not looks_empty_decision(open_questions.content):
        human_decision_flags.append("Open Questions section contains unresolved decisions.")

    if missing_required:
        status = STATUS_NOT_READY
    elif human_decision_flags:
        status = STATUS_NEEDS_DECISION
    else:
        status = STATUS_READY

    return ReportAnalysis(
        source_path=path,
        slug=slug,
        phase_id=phase_id.strip().splitlines()[0],
        phase_title=phase_title.strip().splitlines()[0],
        status=status,
        sections=sections,
        missing_required=missing_required,
        missing_recommended=missing_recommended,
        partial_sections=partial_sections,
        human_decision_flags=human_decision_flags,
        generated_files={},
        generated_at=generated_at,
    )


def safe_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        try:
            return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            return path.resolve().as_posix()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def render_human_decisions(flags: List[str]) -> str:
    if not flags:
        return "None."
    return "\n".join(f"- NEEDS_HUMAN_DECISION: {flag}" for flag in flags)


def render_phase_packet(analysis: ReportAnalysis, output_root: Path, packet_path: Path, prompt_path: Path, manifest_path: Path) -> str:
    sections = analysis.sections
    source_report = safe_relative(analysis.source_path, output_root)
    prompt_location = safe_relative(prompt_path, output_root)
    manifest_location = safe_relative(manifest_path, output_root)

    lines = [
        f"# Phase Packet: {analysis.phase_id} - {analysis.phase_title}",
        "",
        "Generated by Discovery Lane from an already-created Markdown research report.",
        "",
        "## Phase ID",
        "",
        analysis.phase_id,
        "",
        "## Phase Title",
        "",
        analysis.phase_title,
        "",
        "## Source Research Report",
        "",
        f"`{source_report}`",
        "",
        "## Current Status",
        "",
        analysis.status,
        "",
        "## Product Context",
        "",
        section_text(sections, "product_context"),
        "",
        "## Objective",
        "",
        section_text(sections, "objective"),
        "",
        "## In Scope",
        "",
        section_text(sections, "scope"),
        "",
        "## Out of Scope",
        "",
        section_text(sections, "non_goals"),
        "",
        "## Assumptions",
        "",
        section_text(sections, "assumptions"),
        "",
        "## Human Decisions Required",
        "",
        render_human_decisions(analysis.human_decision_flags),
        "",
        "## Functional Requirements",
        "",
        section_text(sections, "functional_requirements"),
        "",
        "## Technical Requirements",
        "",
        section_text(sections, "technical_requirements"),
        "",
        "## Architecture Notes",
        "",
        section_text(sections, "architecture_guidance"),
        "",
        "## Data / State / File Requirements",
        "",
        section_text(sections, "data_file_state_requirements"),
        "",
        "## UX / Wireframe Notes",
        "",
        section_text(sections, "ui_ux_wireframe_guidance"),
        "",
        "## Implementation Plan",
        "",
        section_text(sections, "implementation_tasks"),
        "",
        "## Suggested Parallel Workstreams",
        "",
        section_text(sections, "parallel_workstreams"),
        "",
        "## Dependencies",
        "",
        section_text(sections, "dependencies"),
        "",
        "## Risks",
        "",
        section_text(sections, "risks"),
        "",
        "## Validation Plan",
        "",
        section_text(sections, "validation_test_strategy"),
        "",
        "## Acceptance Criteria",
        "",
        section_text(sections, "acceptance_criteria"),
        "",
        "## Execution Boundaries",
        "",
        "- This packet is for human review before execution handoff.",
        "- Do not reinterpret the product from this packet.",
        "- Do not expand scope beyond the listed implementation tasks.",
        "- Do not run external research, browser automation, model calls, or APIs from this packet.",
        "- Missing requirements must be resolved by a human decision before implementation.",
        "- Commit, push, and merge permissions are not granted by this packet.",
        "",
        "## Generated Worker Prompt Location",
        "",
        f"`{prompt_location}`",
        "",
        "## Manifest Location",
        "",
        f"`{manifest_location}`",
        "",
        "## Generated Metadata",
        "",
        f"- generated_at: {analysis.generated_at}",
        "",
    ]
    return "\n".join(lines)


def render_worker_prompt(analysis: ReportAnalysis, output_root: Path, packet_path: Path) -> str:
    packet_location = safe_relative(packet_path, output_root)
    readiness_notice = ""
    if analysis.status == STATUS_NOT_READY:
        readiness_notice = (
            "This prompt is NOT_EXECUTION_READY. Do not implement this phase until the phase packet is corrected and approved."
        )
    elif analysis.status == STATUS_NEEDS_DECISION:
        readiness_notice = (
            "This prompt requires human approval before execution. Resolve all NEEDS_HUMAN_DECISION flags first."
        )
    else:
        readiness_notice = "This prompt is ready for human review before execution handoff."

    lines = [
        f"# Worker Prompt: {analysis.phase_id} - {analysis.phase_title}",
        "",
        readiness_notice,
        "",
        "## Required First Step",
        "",
        f"Read the phase packet first: `{packet_location}`",
        "",
        "## Scope Boundary",
        "",
        "- You are implementing only this phase.",
        "- Do not reinterpret the product.",
        "- Do not expand scope.",
        "- Do not introduce new frameworks without justification.",
        "- Do not perform unrelated cleanup.",
        "- Do not modify files outside the phase scope unless explicitly necessary and documented.",
        "- Preserve existing architecture.",
        "- Implement only the listed tasks.",
        "- Run validation commands where available.",
        "- If blocked, write a blocker report instead of guessing.",
        "- Do not commit or push unless the execution lane explicitly allows it.",
        "",
        "## Phase Status",
        "",
        f"- current_status: {analysis.status}",
        "",
        "## Placeholders For Execution Lane",
        "",
        "- target_repository_path: TO_BE_CONFIRMED_BY_OPERATOR",
        "- branch_name: TO_BE_CONFIRMED_BY_OPERATOR",
        "- allowed_files: TO_BE_FILLED_AFTER_HUMAN_REVIEW",
        "- forbidden_files: TO_BE_FILLED_AFTER_HUMAN_REVIEW",
        "- validation_commands: TO_BE_CONFIRMED_BY_OPERATOR",
        "- commit_permission: false",
        "- push_permission: false",
        "- merge_permission: false",
        "",
        "## Human Decisions Required Before Execution",
        "",
        render_human_decisions(analysis.human_decision_flags),
        "",
        "## Final Summary Required",
        "",
        "When finished, report:",
        "",
        "- files changed",
        "- tests run",
        "- risks",
        "- blockers",
        "- next steps",
        "",
    ]
    return "\n".join(lines)


def manifest_for(
    analysis: ReportAnalysis,
    output_root: Path,
    packet_path: Path,
    prompt_path: Path,
    manifest_path: Path,
    packet_text: str,
    prompt_text: str,
) -> Dict[str, object]:
    return {
        "generated_at": analysis.generated_at,
        "source_file": safe_relative(analysis.source_path, output_root),
        "phase_id": analysis.phase_id,
        "phase_title": analysis.phase_title,
        "validation_status": analysis.status,
        "missing_required_sections": analysis.missing_required,
        "missing_recommended_sections": analysis.missing_recommended,
        "partial_heading_matches": analysis.partial_sections,
        "human_decision_flags": analysis.human_decision_flags,
        "generated_files": {
            "phase_packet": safe_relative(packet_path, output_root),
            "worker_prompt": safe_relative(prompt_path, output_root),
            "manifest": safe_relative(manifest_path, output_root),
        },
        "hashes": {
            "source_sha256": sha256_text(analysis.source_path.read_text(encoding="utf-8", errors="replace")),
            "phase_packet_sha256": sha256_text(packet_text),
            "worker_prompt_sha256": sha256_text(prompt_text),
        },
        "execution_ready": analysis.status == STATUS_READY,
        "approval_required": True,
    }


def ensure_output_dirs(output_root: Path) -> None:
    for directory in OUTPUT_DIRS:
        (output_root / directory).mkdir(parents=True, exist_ok=True)


def write_report_outputs(
    analysis: ReportAnalysis,
    output_root: Path,
    filename_prefix: str = "",
    overwrite: bool = True,
) -> ReportAnalysis:
    ensure_output_dirs(output_root)
    safe_prefix = f"{filename_prefix}__" if filename_prefix else ""
    packet_path = output_root / "phase_packets" / f"{safe_prefix}{analysis.slug}_packet.md"
    prompt_path = output_root / "worker_prompts" / f"{safe_prefix}{analysis.slug}_worker_prompt.md"
    manifest_path = output_root / "manifests" / f"{safe_prefix}{analysis.slug}_manifest.json"

    if not overwrite:
        existing = [path for path in (packet_path, prompt_path, manifest_path) if path.exists()]
        if existing:
            joined = ", ".join(str(path) for path in existing)
            raise FileExistsError(f"refusing to overwrite existing Discovery Lane generated files: {joined}")

    packet_text = render_phase_packet(analysis, output_root, packet_path, prompt_path, manifest_path)
    prompt_text = render_worker_prompt(analysis, output_root, packet_path)
    manifest = manifest_for(analysis, output_root, packet_path, prompt_path, manifest_path, packet_text, prompt_text)

    packet_path.write_text(packet_text, encoding="utf-8", newline="\n")
    prompt_path.write_text(prompt_text, encoding="utf-8", newline="\n")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    analysis.generated_files = {
        "phase_packet": safe_relative(packet_path, output_root),
        "worker_prompt": safe_relative(prompt_path, output_root),
        "manifest": safe_relative(manifest_path, output_root),
    }
    return analysis


def load_manifests(output_root: Path) -> List[Dict[str, object]]:
    manifest_dir = output_root / "manifests"
    if not manifest_dir.exists():
        return []
    manifests: List[Dict[str, object]] = []
    for path in sorted(manifest_dir.glob("*_manifest.json")):
        try:
            manifests.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            manifests.append(
                {
                    "phase_id": path.stem.replace("_manifest", ""),
                    "phase_title": "Unreadable manifest",
                    "validation_status": STATUS_NOT_READY,
                    "source_file": "",
                    "generated_files": {"manifest": safe_relative(path, output_root)},
                    "human_decision_flags": ["Manifest JSON is unreadable."],
                }
            )
    return manifests


def load_json_records(directory: Path, pattern: str) -> List[Dict[str, object]]:
    if not directory.exists():
        return []
    records: List[Dict[str, object]] = []
    for path in sorted(directory.glob(pattern)):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data["_record_path"] = safe_relative(path, directory.parent)
                records.append(data)
        except json.JSONDecodeError:
            continue
    return records


def latest_record_by_phase(records: List[Dict[str, object]], timestamp_key: str) -> Dict[str, Dict[str, object]]:
    by_phase: Dict[str, Dict[str, object]] = {}
    for record in records:
        phase_id = str(record.get("phase_id", ""))
        if not phase_id:
            continue
        current = by_phase.get(phase_id)
        if current is None or str(record.get(timestamp_key, "")) >= str(current.get(timestamp_key, "")):
            by_phase[phase_id] = record
    return by_phase


def render_discovery_index(output_root: Path, generated_at: str) -> str:
    manifests = load_manifests(output_root)
    approvals = latest_record_by_phase(
        load_json_records(output_root / "approval_records", "*_record.json"),
        "approval_timestamp",
    )
    branch_plans = latest_record_by_phase(
        load_json_records(output_root / "branch_plans", "*_branch_plan.json"),
        "generated_timestamp",
    )
    lines = [
        "# Discovery Lane Index",
        "",
        f"Last updated: {generated_at}",
        "",
        "This index is generated from Discovery Lane manifests. Review phase packets before handing work to an execution lane.",
        "",
        "| Phase ID | Phase Title | Validation Status | Approval Status | Handoff Location | Proposed Branch | Branch Status | Phase Packet | Worker Prompt |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for manifest in manifests:
        files = manifest.get("generated_files", {})
        if not isinstance(files, dict):
            files = {}
        phase_id = str(manifest.get("phase_id", ""))
        approval = approvals.get(phase_id, {})
        branch_plan = branch_plans.get(phase_id, {})
        lines.append(
            "| {phase_id} | {phase_title} | {validation_status} | {approval_status} | `{handoff}` | `{branch}` | {branch_status} | `{packet}` | `{prompt}` |".format(
                phase_id=phase_id,
                phase_title=str(manifest.get("phase_title", "")),
                validation_status=str(manifest.get("validation_status", "")),
                approval_status=str(approval.get("approval_status", "PENDING_HUMAN_REVIEW")),
                handoff=str(approval.get("handoff_bundle", "")),
                branch=str(branch_plan.get("proposed_branch_name", approval.get("proposed_branch_name", ""))),
                branch_status=str(branch_plan.get("branch_status", approval.get("branch_status", ""))),
                packet=str(files.get("phase_packet", "")),
                prompt=str(files.get("worker_prompt", "")),
            )
        )
    lines.extend(
        [
            "",
            "## Approval Checkpoint",
            "",
            "- `READY_FOR_HUMAN_REVIEW` still requires operator review before execution.",
            "- `NEEDS_HUMAN_DECISION` must be clarified before execution.",
            "- `NOT_EXECUTION_READY` must not be handed to a worker.",
            "",
        ]
    )
    return "\n".join(lines)


def ingest_reports(input_dir: Path, output_root: Path) -> List[ReportAnalysis]:
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {input_dir}")

    output_root.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    reports = sorted(path for path in input_dir.glob("*.md") if path.is_file())
    analyses: List[ReportAnalysis] = []

    ensure_output_dirs(output_root)
    for report_path in reports:
        text = report_path.read_text(encoding="utf-8", errors="replace")
        analysis = validate_report(report_path, text, generated_at)
        analyses.append(write_report_outputs(analysis, output_root))

    index_text = render_discovery_index(output_root, generated_at)
    (output_root / "discovery_index.md").write_text(index_text, encoding="utf-8", newline="\n")
    return analyses


def render_run_summary(analyses: Iterable[ReportAnalysis], input_dir: Path, output_root: Path) -> str:
    analyses = list(analyses)
    lines = [
        "# Discovery Lane Ingest Summary",
        "",
        f"- input: `{input_dir}`",
        f"- output: `{output_root}`",
        f"- reports_processed: {len(analyses)}",
        "",
    ]
    if not analyses:
        lines.extend(
            [
                "No Markdown reports found in the input directory.",
                "",
                "Generated/updated `discovery_index.md` with the current manifest inventory.",
            ]
        )
        return "\n".join(lines)

    for analysis in analyses:
        lines.extend(
            [
                f"## {analysis.phase_id} - {analysis.phase_title}",
                "",
                f"- status: {analysis.status}",
                f"- source: `{analysis.source_path}`",
                f"- phase_packet: `{analysis.generated_files.get('phase_packet', '')}`",
                f"- worker_prompt: `{analysis.generated_files.get('worker_prompt', '')}`",
                f"- manifest: `{analysis.generated_files.get('manifest', '')}`",
                f"- missing_required_sections: {len(analysis.missing_required)}",
                f"- human_decision_flags: {len(analysis.human_decision_flags)}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest phase-wise Markdown research reports into Discovery Lane packets."
    )
    parser.add_argument("--input", required=True, help="Directory containing phase-wise Markdown research reports.")
    parser.add_argument("--output", required=True, help="Discovery Lane output root.")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_root = Path(args.output)

    try:
        analyses = ingest_reports(input_dir, output_root)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(render_run_summary(analyses, input_dir, output_root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
