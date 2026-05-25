#!/usr/bin/env python3
"""Build non-executing product-development artifacts from a Discovery queue."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

LANE_VERSION = "Product Development Lane adapter v0.1"
NOT_SPECIFIED = "NOT_SPECIFIED_IN_DISCOVERY_HANDOFF"
NEEDS_DECISION = "NEEDS_HUMAN_DECISION"

OUTPUT_DIRS = (
    "product_packets",
    "prd_briefs",
    "wireframe_briefs",
    "ui_ux_briefs",
    "feature_specs",
    "implementation_plans",
    "manifests",
    "reports",
)


class ProductDevelopmentError(Exception):
    """Raised when a queue cannot be converted safely."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProductDevelopmentError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProductDevelopmentError(f"JSON root must be an object: {path}")
    return data


def ensure_output_dirs(output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    for name in OUTPUT_DIRS:
        target = output_root / name
        target.mkdir(parents=True, exist_ok=True)
        gitkeep = target / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="ascii")


def discovery_root_from_queue(queue_path: Path) -> Path:
    resolved = queue_path.resolve()
    if resolved.parent.name == "execution_queues":
        return resolved.parent.parent
    for parent in resolved.parents:
        if parent.name == "discovery_lane":
            return parent
    raise ProductDevelopmentError("queue path is not under discovery_lane/execution_queues")


def resolve_under(root: Path, relative_path: str, *, label: str) -> Path:
    candidate = (root / relative_path).resolve()
    root_resolved = root.resolve()
    if root_resolved != candidate and root_resolved not in candidate.parents:
        raise ProductDevelopmentError(f"{label} escapes expected root: {relative_path}")
    if not candidate.exists():
        raise ProductDevelopmentError(f"{label} missing: {relative_path}")
    return candidate


def parse_markdown_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = "_preamble"
    sections[current] = []
    for line in text.splitlines():
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            current = match.group(1).strip().lower()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def section(sections: dict[str, str], *names: str, default: str = NEEDS_DECISION) -> str:
    for name in names:
        value = sections.get(name.lower(), "").strip()
        if value:
            return value
    return default


def explicit_ui_value(value: str) -> str:
    if not value or value == NEEDS_DECISION:
        return NOT_SPECIFIED
    return value


def lines_block(value: str, *, fallback: str = NEEDS_DECISION) -> str:
    value = value.strip()
    return value if value else fallback


def load_phase_context(discovery_root: Path, phase: dict[str, Any]) -> dict[str, Any]:
    phase_packet = resolve_under(discovery_root, str(phase.get("phase_packet", "")), label="phase_packet")
    worker_prompt = resolve_under(discovery_root, str(phase.get("worker_prompt", "")), label="worker_prompt")
    phase_manifest = resolve_under(discovery_root, str(phase.get("phase_manifest", "")), label="phase_manifest")
    approval_record = resolve_under(discovery_root, str(phase.get("approval_record", "")), label="approval_record")
    branch_plan = resolve_under(discovery_root, str(phase.get("branch_plan", "")), label="branch_plan")
    handoff_bundle = resolve_under(discovery_root, str(phase.get("handoff_bundle", "")), label="handoff_bundle")
    handoff_md = handoff_bundle / "HANDOFF.md"
    if not handoff_md.exists():
        raise ProductDevelopmentError(f"handoff bundle missing HANDOFF.md: {phase.get('handoff_bundle')}")

    packet_text = phase_packet.read_text(encoding="utf-8")
    sections = parse_markdown_sections(packet_text)
    manifest = read_json(phase_manifest)
    approval = read_json(approval_record)
    branch = read_json(branch_plan)

    return {
        "phase_id": str(phase.get("phase_id") or manifest.get("phase_id") or section(sections, "Phase ID")),
        "phase_title": str(phase.get("phase_title") or manifest.get("phase_title") or section(sections, "Phase Title")),
        "recommended_execution_order": phase.get("recommended_execution_order"),
        "phase_packet": phase_packet,
        "worker_prompt": worker_prompt,
        "phase_manifest": phase_manifest,
        "approval_record": approval_record,
        "branch_plan": branch_plan,
        "handoff_bundle": handoff_bundle,
        "handoff_md": handoff_md,
        "packet_text": packet_text,
        "sections": sections,
        "manifest": manifest,
        "approval": approval,
        "branch": branch,
        "queue_phase": phase,
    }


def format_phase_section(phases: list[dict[str, Any]], heading: str, *section_names: str, fallback: str = NEEDS_DECISION) -> str:
    chunks = []
    for phase in phases:
        content = section(phase["sections"], *section_names, default=fallback)
        chunks.append(f"### {phase['phase_id']} - {phase['phase_title']}\n\n{lines_block(content, fallback=fallback)}")
    return f"## {heading}\n\n" + "\n\n".join(chunks)


def source_list(phases: list[dict[str, Any]], discovery_root: Path) -> str:
    lines = []
    for phase in phases:
        lines.extend(
            [
                f"- `{rel(phase['handoff_bundle'], discovery_root)}`",
                f"- `{rel(phase['phase_packet'], discovery_root)}`",
                f"- `{rel(phase['worker_prompt'], discovery_root)}`",
                f"- `{rel(phase['branch_plan'], discovery_root)}`",
                f"- `{rel(phase['approval_record'], discovery_root)}`",
                f"- `{rel(phase['phase_manifest'], discovery_root)}`",
            ]
        )
    return "\n".join(lines)


def build_artifact_texts(set_id: str, queue_rel: str, phases: list[dict[str, Any]], discovery_root: Path, output_paths: dict[str, Path], timestamp: str) -> dict[str, str]:
    downstream = "\n".join(f"- `{path.as_posix()}`" for path in output_paths.values())
    phase_rows = "\n".join(
        f"| {phase['phase_id']} | {phase['phase_title']} | {phase['queue_phase'].get('proposed_branch_name', NEEDS_DECISION)} | {phase['queue_phase'].get('execution_status', 'NOT_STARTED')} |"
        for phase in phases
    )
    source_refs = source_list(phases, discovery_root)

    product_packet = f"""# Product Packet: {set_id}

Generated by Product Development Lane from a Discovery Lane execution queue.

## Set ID

{set_id}

## Source Execution Queue

`{queue_rel}`

## Source Handoffs

{source_refs}

{format_phase_section(phases, "Product Context", "Product Context")}

{format_phase_section(phases, "Product Objectives", "Objective")}

{format_phase_section(phases, "User Workflows", "User / Operator Workflow", "UX / Wireframe Notes", fallback=NEEDS_DECISION)}

{format_phase_section(phases, "Functional Requirements", "Functional Requirements")}

{format_phase_section(phases, "Non-Functional Requirements", "Technical Requirements")}

{format_phase_section(phases, "UI/UX Requirements", "UX / Wireframe Notes", fallback=NOT_SPECIFIED)}

{format_phase_section(phases, "Wireframe Needs", "UX / Wireframe Notes", fallback=NOT_SPECIFIED)}

{format_phase_section(phases, "Feature List", "Functional Requirements")}

{format_phase_section(phases, "Acceptance Criteria", "Acceptance Criteria")}

{format_phase_section(phases, "Risks", "Risks")}

{format_phase_section(phases, "Open Decisions", "Human Decisions Required", fallback=NEEDS_DECISION)}

## Downstream Artifacts Generated

{downstream}

## Execution Boundary

- No worker prompts were executed.
- No git branches were created or checked out.
- No commit, push, or merge occurred.
- No models, providers, APIs, or browsers were called.
- This packet is a product-development planning artifact only.

## Generated Metadata

- generated_at: {timestamp}
- generated_by: {LANE_VERSION}
"""

    prd_brief = f"""# PRD Brief: {set_id}

## Product Name

{set_id}

## Product Thesis

{section(phases[0]['sections'], "Product Context")}

## Target Users

{NEEDS_DECISION}

## Problem Statement

{section(phases[0]['sections'], "Product Context")}

## Goals

{format_phase_section(phases, "Phase Goals", "Objective")}

## Non-Goals

{format_phase_section(phases, "Out of Scope", "Out of Scope")}

## User Journeys

{format_phase_section(phases, "User Journey Notes", "User / Operator Workflow", "UX / Wireframe Notes", fallback=NEEDS_DECISION)}

## Core Requirements

{format_phase_section(phases, "Core Functional Requirements", "Functional Requirements")}

## Release Scope

{format_phase_section(phases, "In Scope", "In Scope")}

## Acceptance Criteria

{format_phase_section(phases, "Acceptance Criteria", "Acceptance Criteria")}

## Risks

{format_phase_section(phases, "Risks", "Risks")}

## Open Decisions

{format_phase_section(phases, "Human Decisions Required", "Human Decisions Required", fallback=NEEDS_DECISION)}

## Boundary

This PRD brief is derived from approved Discovery Lane handoffs only. It does not approve or execute implementation.

No worker prompts were executed. No branches were created. No commit, push, or merge occurred.
"""

    wireframe_brief = f"""# Wireframe Brief: {set_id}

## Screens/Pages Required

{format_phase_section(phases, "Screen Notes", "UX / Wireframe Notes", fallback=NOT_SPECIFIED)}

## User Flows

{format_phase_section(phases, "User Flow Notes", "User / Operator Workflow", "UX / Wireframe Notes", fallback=NOT_SPECIFIED)}

## Layout Goals

{format_phase_section(phases, "Layout Notes", "UX / Wireframe Notes", fallback=NOT_SPECIFIED)}

## Key UI States

{NOT_SPECIFIED}

## Empty/Loading/Error States

{NOT_SPECIFIED}

## Inputs and Outputs

{format_phase_section(phases, "Data / State / File Requirements", "Data / State / File Requirements", fallback=NOT_SPECIFIED)}

## Navigation Model

{NOT_SPECIFIED}

## Accessibility Considerations

{NOT_SPECIFIED}

## Handoff Notes for Future UI Generation

Do not generate UI or app code from this brief without a future guarded lane. Missing UI details must remain explicit.

No worker prompts were executed. No branches were created. No commit, push, or merge occurred.
"""

    ui_ux_brief = f"""# UI/UX Brief: {set_id}

## Design Principles

{NEEDS_DECISION}

## Target User Mental Model

{NEEDS_DECISION}

## UX Priorities

{format_phase_section(phases, "UX Priority Notes", "UX / Wireframe Notes", fallback=NOT_SPECIFIED)}

## Interaction Patterns

{NOT_SPECIFIED}

## Information Architecture

{format_phase_section(phases, "Architecture Notes", "Architecture Notes", fallback=NOT_SPECIFIED)}

## Validation/Error Messaging

{NOT_SPECIFIED}

## Accessibility Notes

{NOT_SPECIFIED}

## Responsive Behaviour

{NOT_SPECIFIED}

## Constraints

{format_phase_section(phases, "Execution Boundaries", "Execution Boundaries", fallback=NEEDS_DECISION)}

## Boundary

No worker prompts were executed. No branches were created. No commit, push, or merge occurred.
"""

    feature_spec = f"""# Feature Spec: {set_id}

## Feature Sources

{source_refs}

## Feature List

{format_phase_section(phases, "Functional Requirements", "Functional Requirements")}

## Feature Acceptance Criteria

{format_phase_section(phases, "Acceptance Criteria", "Acceptance Criteria")}

## Assumptions

Any feature not explicitly listed above is out of scope unless a human updates the Discovery handoff. Inferred features must be marked `ASSUMPTION`.

## Out of Scope

{format_phase_section(phases, "Out of Scope", "Out of Scope")}

## Risks

{format_phase_section(phases, "Risks", "Risks")}

## Boundary

No worker prompts were executed. No branches were created. No commit, push, or merge occurred.
"""

    implementation_plan = f"""# Implementation Planning Packet: {set_id}

This is not execution. It is a planning packet for future lanes.

## Phase Mapping

| Phase ID | Phase Title | Proposed Branch | Execution Status |
| --- | --- | --- | --- |
{phase_rows}

## Workstreams

{format_phase_section(phases, "Suggested Parallel Workstreams", "Suggested Parallel Workstreams", fallback=NEEDS_DECISION)}

## Suggested Order

Execute phases in the `recommended_execution_order` recorded by the Discovery queue unless a human changes the plan.

## Dependencies

{format_phase_section(phases, "Dependencies", "Dependencies", fallback=NEEDS_DECISION)}

## Validation Commands / Placeholders

{format_phase_section(phases, "Validation Plan", "Validation Plan", fallback=NEEDS_DECISION)}

## File-Scope Assumptions

{NEEDS_DECISION}

## Risks

{format_phase_section(phases, "Risks", "Risks", fallback=NEEDS_DECISION)}

## Human Decisions Required

{format_phase_section(phases, "Human Decisions Required", "Human Decisions Required", fallback=NEEDS_DECISION)}

## Execution Boundary

- Do not execute worker prompts from this packet.
- Do not create branches.
- Do not commit, push, or merge.
- Future execution must consume Discovery handoffs and this planning context through a separate guarded lane.
"""

    report = f"""# Product Development Adapter Report: {set_id}

## Summary

- source queue: `{queue_rel}`
- phases converted: {len(phases)}
- generated_at: {timestamp}
- generated_by: {LANE_VERSION}

## Outputs

{downstream}

## Safety Boundary

- No worker prompts were executed.
- No branches were created or checked out.
- No commit, push, or merge occurred.
- No model/provider/API/browser call occurred.
- Discovery Lane artifacts were read, not modified.
"""

    return {
        "product_packet": product_packet,
        "prd_brief": prd_brief,
        "wireframe_brief": wireframe_brief,
        "ui_ux_brief": ui_ux_brief,
        "feature_spec": feature_spec,
        "implementation_plan": implementation_plan,
        "report": report,
    }


def output_paths_for_set(output_root: Path, set_id: str) -> dict[str, Path]:
    return {
        "product_packet": output_root / "product_packets" / f"{set_id}_product_packet.md",
        "prd_brief": output_root / "prd_briefs" / f"{set_id}_prd_brief.md",
        "wireframe_brief": output_root / "wireframe_briefs" / f"{set_id}_wireframe_brief.md",
        "ui_ux_brief": output_root / "ui_ux_briefs" / f"{set_id}_ui_ux_brief.md",
        "feature_spec": output_root / "feature_specs" / f"{set_id}_feature_spec.md",
        "implementation_plan": output_root / "implementation_plans" / f"{set_id}_implementation_plan.md",
        "manifest": output_root / "manifests" / f"{set_id}_product_development_manifest.json",
        "report": output_root / "reports" / f"{set_id}_adapter_report.md",
    }


def build_product_packet(queue_path: Path, output_root: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    queue_path = queue_path.resolve()
    output_root = output_root.resolve()
    if not queue_path.exists():
        raise ProductDevelopmentError(f"queue manifest missing: {queue_path}")

    queue = read_json(queue_path)
    if queue.get("queue_status") != "READY_FOR_EXECUTION_LANE":
        raise ProductDevelopmentError(
            f"queue_status must be READY_FOR_EXECUTION_LANE, found {queue.get('queue_status')!r}"
        )
    if queue.get("worker_prompts_executed") is True or queue.get("branches_created") is True:
        raise ProductDevelopmentError("queue manifest claims execution or branch creation occurred")

    set_id = str(queue.get("set_id") or queue_path.stem.replace("_execution_queue", ""))
    discovery_root = discovery_root_from_queue(queue_path)
    ensure_output_dirs(output_root)

    queued_phases = queue.get("queued_phases")
    if not isinstance(queued_phases, list) or not queued_phases:
        raise ProductDevelopmentError("READY queue must include queued_phases")

    phases = [load_phase_context(discovery_root, phase) for phase in queued_phases if isinstance(phase, dict)]
    if len(phases) != len(queued_phases):
        raise ProductDevelopmentError("queued_phases must contain objects")

    paths = output_paths_for_set(output_root, set_id)
    output_rel = {key: rel(path, output_root) for key, path in paths.items()}
    timestamp = utc_now()
    queue_rel = rel(queue_path, discovery_root)
    artifact_texts = build_artifact_texts(set_id, queue_rel, phases, discovery_root, paths, timestamp)

    for key, text in artifact_texts.items():
        paths[key].write_text(text.rstrip() + "\n", encoding="utf-8")

    inputs = []
    for phase in phases:
        inputs.append(
            {
                "phase_id": phase["phase_id"],
                "phase_title": phase["phase_title"],
                "phase_packet": rel(phase["phase_packet"], discovery_root),
                "worker_prompt": rel(phase["worker_prompt"], discovery_root),
                "phase_manifest": rel(phase["phase_manifest"], discovery_root),
                "approval_record": rel(phase["approval_record"], discovery_root),
                "branch_plan": rel(phase["branch_plan"], discovery_root),
                "handoff_bundle": rel(phase["handoff_bundle"], discovery_root),
                "handoff": rel(phase["handoff_md"], discovery_root),
                "phase_packet_sha256": sha256(phase["phase_packet"]),
                "worker_prompt_sha256": sha256(phase["worker_prompt"]),
            }
        )

    manifest = {
        "set_id": set_id,
        "generated_timestamp": timestamp,
        "generated_by": LANE_VERSION,
        "source_execution_queue": rel(queue_path, discovery_root),
        "source_execution_queue_sha256": sha256(queue_path),
        "source_queue_status": queue.get("queue_status"),
        "queued_phase_count": len(phases),
        "source_handoffs": [item["handoff_bundle"] for item in inputs],
        "source_phase_packets": [item["phase_packet"] for item in inputs],
        "source_worker_prompts": [item["worker_prompt"] for item in inputs],
        "source_branch_plans": [item["branch_plan"] for item in inputs],
        "source_approval_records": [item["approval_record"] for item in inputs],
        "inputs": inputs,
        "outputs": output_rel,
        "worker_prompts_executed": False,
        "branches_created": False,
        "git_actions_performed": False,
        "commit_performed": False,
        "push_performed": False,
        "merge_performed": False,
        "models_called": False,
        "application_code_generated": False,
        "discovery_artifacts_modified": False,
        "artifact_status": "GENERATED_PRODUCT_DEVELOPMENT_PLANNING_ARTIFACTS",
    }
    paths["manifest"].write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest, paths


def render_summary(manifest: dict[str, Any], paths: dict[str, Path], output_root: Path) -> str:
    lines = [
        "# Product Development Packet Build",
        "",
        f"- set_id: {manifest['set_id']}",
        f"- source_queue_status: {manifest['source_queue_status']}",
        f"- queued_phase_count: {manifest['queued_phase_count']}",
        "- execution: not performed",
        "- branches_created: false",
        "- git_actions_performed: false",
        "- models_called: false",
        "",
        "## Outputs",
    ]
    for key in (
        "product_packet",
        "prd_brief",
        "wireframe_brief",
        "ui_ux_brief",
        "feature_spec",
        "implementation_plan",
        "manifest",
        "report",
    ):
        lines.append(f"- {key}: `{rel(paths[key], output_root)}`")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build non-executing Product Development Lane artifacts from a READY Discovery queue."
    )
    parser.add_argument("--queue", required=True, help="Discovery Lane execution queue manifest")
    parser.add_argument("--output", default="product_development_lane", help="Product Development Lane output root")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        manifest, paths = build_product_packet(Path(args.queue), Path(args.output))
    except ProductDevelopmentError as exc:
        print(f"ERROR: {exc}")
        return 2
    print(render_summary(manifest, paths, Path(args.output).resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
