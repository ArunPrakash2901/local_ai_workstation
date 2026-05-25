#!/usr/bin/env python3
"""Record human approval or rejection for a Discovery Lane phase packet.

This script does not execute worker prompts, run models, or perform git actions.
It snapshots reviewed packet artifacts into an immutable handoff bundle and
records a planned branch name for a later execution lane.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Optional


STATUS_READY = "READY_FOR_HUMAN_REVIEW"
STATUS_NEEDS_DECISION = "NEEDS_HUMAN_DECISION"
STATUS_NOT_READY = "NOT_EXECUTION_READY"

APPROVED = "APPROVED_FOR_EXECUTION_HANDOFF"
REJECTED = "REJECTED_BY_HUMAN"
APPROVED_OVERRIDE = "APPROVED_WITH_OVERRIDES"
BLOCKED = "BLOCKED_NEEDS_REVISION"

BRANCH_STATUS = "PLANNED_NOT_CREATED"
EXECUTION_STATUS = "NOT_STARTED"

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
INLINE_CODE_RE = re.compile(r"`([^`]+)`")
SLUG_RE = re.compile(r"[^a-z0-9]+")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str, separator: str = "-") -> str:
    slug = SLUG_RE.sub(separator, value.strip().lower()).strip(separator)
    return slug or "phase"


def packet_slug(phase_id: str, phase_title: str) -> str:
    phase_slug = slugify(phase_id)
    title_slug = slugify(phase_title)
    if title_slug and title_slug not in phase_slug:
        return f"{phase_slug}-{title_slug}".strip("-")
    return phase_slug


def json_slug(phase_id: str, phase_title: str) -> str:
    return packet_slug(phase_id, phase_title).replace("-", "_")


def parse_markdown_sections(text: str) -> Dict[str, str]:
    sections: Dict[str, list[str]] = {}
    current: Optional[str] = None

    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            heading = normalize_heading(match.group(2))
            current = heading
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(line)

    return {key: "\n".join(value).strip() for key, value in sections.items()}


def normalize_heading(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.strip().lower())).strip()


def section(sections: Dict[str, str], name: str) -> str:
    return sections.get(normalize_heading(name), "").strip()


def first_code_path(value: str) -> Optional[str]:
    match = INLINE_CODE_RE.search(value)
    if match:
        return match.group(1).strip()
    stripped = value.strip().splitlines()
    return stripped[0].strip() if stripped else None


def resolve_reference(path_text: Optional[str], output_root: Path, packet_path: Path) -> Optional[Path]:
    if not path_text:
        return None
    raw = Path(path_text)
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.extend([output_root / raw, packet_path.parent / raw, Path.cwd() / raw])

    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve() if candidates else None


def safe_relative(path: Optional[Path], root: Path) -> str:
    if path is None:
        return ""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        try:
            return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            return path.resolve().as_posix()


def ensure_dirs(output_root: Path) -> None:
    for name in (
        "approved_packets",
        "rejected_packets",
        "execution_handoffs",
        "approval_records",
        "branch_plans",
    ):
        (output_root / name).mkdir(parents=True, exist_ok=True)


def refresh_discovery_index(output_root: Path) -> None:
    try:
        from ingest_research_reports import render_discovery_index
    except ImportError:
        return
    generated_at = utc_now()
    index_path = output_root / "discovery_index.md"
    index_path.write_text(render_discovery_index(output_root, generated_at), encoding="utf-8", newline="\n")


def load_packet(packet_path: Path, output_root: Path) -> Dict[str, object]:
    if not packet_path.exists():
        raise FileNotFoundError(f"phase packet not found: {packet_path}")
    text = packet_path.read_text(encoding="utf-8", errors="replace")
    sections = parse_markdown_sections(text)

    phase_id = section(sections, "Phase ID")
    phase_title = section(sections, "Phase Title")
    current_status = section(sections, "Current Status")

    if not phase_id:
        raise ValueError("phase packet is missing Phase ID")
    if not phase_title:
        raise ValueError("phase packet is missing Phase Title")
    if not current_status:
        raise ValueError("phase packet is missing Current Status")

    worker_ref = first_code_path(section(sections, "Generated Worker Prompt Location"))
    manifest_ref = first_code_path(section(sections, "Manifest Location"))
    worker_path = resolve_reference(worker_ref, output_root, packet_path)
    manifest_path = resolve_reference(manifest_ref, output_root, packet_path)

    if worker_ref and (worker_path is None or not worker_path.exists()):
        raise FileNotFoundError(f"referenced worker prompt not found: {worker_ref}")
    if manifest_ref and (manifest_path is None or not manifest_path.exists()):
        raise FileNotFoundError(f"referenced manifest not found: {manifest_ref}")

    if worker_path is None:
        inferred = output_root / "worker_prompts" / f"{slugify(packet_path.stem.replace('_packet', ''), '_')}_worker_prompt.md"
        if inferred.exists():
            worker_path = inferred.resolve()

    if worker_path is None or not worker_path.exists():
        raise FileNotFoundError("matching worker prompt could not be located")

    return {
        "packet_text": text,
        "sections": sections,
        "phase_id": phase_id.splitlines()[0].strip(),
        "phase_title": phase_title.splitlines()[0].strip(),
        "current_status": current_status.splitlines()[0].strip(),
        "worker_prompt_path": worker_path,
        "manifest_path": manifest_path if manifest_path and manifest_path.exists() else None,
    }


def infer_conflict_risk(packet_text: str) -> str:
    lowered = packet_text.lower()
    risk_terms = []
    for term in ("shared", "global", "registry", "routing", "migration", "schema", "database", "state"):
        if term in lowered:
            risk_terms.append(term)
    if risk_terms:
        return "Potential conflict risk from shared surface terms: " + ", ".join(sorted(set(risk_terms))) + "."
    return "No specific conflict risk inferred from packet text; execution lane should still review touched files."


def build_branch_plan(
    *,
    phase_id: str,
    phase_title: str,
    packet_path: Path,
    worker_path: Path,
    approval_record_path: Path,
    handoff_dir: Path,
    branch_name: str,
    output_root: Path,
    commit_allowed: bool,
    push_allowed: bool,
    merge_allowed: bool,
    generated_at: str,
    packet_text: str,
) -> Dict[str, object]:
    return {
        "phase_id": phase_id,
        "phase_title": phase_title,
        "proposed_branch_name": branch_name,
        "source_phase_packet": safe_relative(packet_path, output_root),
        "source_worker_prompt": safe_relative(worker_path, output_root),
        "source_approval_record": safe_relative(approval_record_path, output_root),
        "source_handoff_bundle": safe_relative(handoff_dir, output_root),
        "branch_status": BRANCH_STATUS,
        "created_by_discovery_lane": False,
        "commit_allowed": commit_allowed,
        "push_allowed": push_allowed,
        "merge_allowed": merge_allowed,
        "parallel_execution_notes": (
            "Handoff folder is the immutable approved contract. "
            "The git branch is only the future mutable implementation workspace."
        ),
        "expected_merge_target": "main",
        "conflict_risk_notes": infer_conflict_risk(packet_text),
        "generated_timestamp": generated_at,
    }


def build_approval_record(
    *,
    phase_id: str,
    phase_title: str,
    status: str,
    packet_status: str,
    packet_path: Path,
    worker_path: Optional[Path],
    manifest_path: Optional[Path],
    handoff_dir: Optional[Path],
    branch_plan_path: Optional[Path],
    branch_name: Optional[str],
    output_root: Path,
    reason: str,
    override: bool,
    commit_allowed: bool,
    push_allowed: bool,
    merge_allowed: bool,
    generated_at: str,
) -> Dict[str, object]:
    return {
        "phase_id": phase_id,
        "phase_title": phase_title,
        "approval_status": status,
        "packet_validation_status": packet_status,
        "approval_timestamp": generated_at,
        "reason": reason,
        "override_used": override,
        "source_phase_packet": safe_relative(packet_path, output_root),
        "source_worker_prompt": safe_relative(worker_path, output_root),
        "source_manifest": safe_relative(manifest_path, output_root),
        "handoff_bundle": safe_relative(handoff_dir, output_root),
        "branch_plan": safe_relative(branch_plan_path, output_root),
        "proposed_branch_name": branch_name or "",
        "branch_status": BRANCH_STATUS if branch_name else "",
        "execution_lane_status": EXECUTION_STATUS if status in {APPROVED, APPROVED_OVERRIDE} else "",
        "permissions": {
            "commit": commit_allowed,
            "push": push_allowed,
            "merge": merge_allowed,
        },
        "git_actions_performed": False,
        "execution_performed": False,
    }


def render_handoff(
    *,
    phase_id: str,
    phase_title: str,
    approval_status: str,
    approval_timestamp: str,
    packet_path: Path,
    worker_path: Path,
    manifest_path: Optional[Path],
    branch_plan_path: Path,
    branch_name: str,
    reason: str,
    output_root: Path,
    commit_allowed: bool,
    push_allowed: bool,
    merge_allowed: bool,
) -> str:
    return "\n".join(
        [
            f"# Execution Handoff: {phase_id} - {phase_title}",
            "",
            "## Phase ID",
            "",
            phase_id,
            "",
            "## Phase Title",
            "",
            phase_title,
            "",
            "## Approval Status",
            "",
            approval_status,
            "",
            "## Approval Timestamp",
            "",
            approval_timestamp,
            "",
            "## Source Phase Packet",
            "",
            f"`{safe_relative(packet_path, output_root)}`",
            "",
            "## Source Worker Prompt",
            "",
            f"`{safe_relative(worker_path, output_root)}`",
            "",
            "## Source Manifest",
            "",
            f"`{safe_relative(manifest_path, output_root) if manifest_path else 'not available'}`",
            "",
            "## Source Branch Plan",
            "",
            f"`{safe_relative(branch_plan_path, output_root)}`",
            "",
            "## Proposed Git Branch",
            "",
            branch_name,
            "",
            "## Branch Status",
            "",
            BRANCH_STATUS,
            "",
            "## Human Approval Notes / Reason",
            "",
            reason or "No additional approval note provided.",
            "",
            "## Execution Permissions",
            "",
            f"- commit: {str(commit_allowed).lower()}",
            f"- push: {str(push_allowed).lower()}",
            f"- merge: {str(merge_allowed).lower()}",
            "",
            "## Required Human Review Before Execution",
            "",
            "yes",
            "",
            "## Execution Lane Status",
            "",
            EXECUTION_STATUS,
            "",
            "## Next Suggested Slash Command Placeholder",
            "",
            f"`/discovery handoff {slugify(phase_id)}`",
            "",
            "## Approval Boundary",
            "",
            "Approval for handoff does NOT mean:",
            "",
            "- execute automatically",
            "- commit automatically",
            "- push automatically",
            "- merge automatically",
            "",
            "Approval for handoff only means:",
            "",
            "- this phase packet is approved as an execution input later",
            "",
        ]
    )


def render_handoff_readme(phase_id: str, phase_title: str, branch_name: str) -> str:
    return "\n".join(
        [
            f"# Handoff Bundle: {phase_id} - {phase_title}",
            "",
            "This directory is the immutable approved contract of record for a later execution lane.",
            "",
            f"- proposed_branch_name: `{branch_name}`",
            f"- branch_status: `{BRANCH_STATUS}`",
            f"- execution_lane_status: `{EXECUTION_STATUS}`",
            "",
            "Do not treat this bundle as permission to execute, commit, push, or merge. Those actions require a later guarded execution workflow.",
            "",
        ]
    )


def write_json(path: Path, data: Dict[str, object]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def record_blocked(packet_path: Path, output_root: Path, packet: Dict[str, object], reason: str) -> Path:
    ensure_dirs(output_root)
    generated_at = utc_now()
    phase_id = str(packet["phase_id"])
    phase_title = str(packet["phase_title"])
    record_path = output_root / "approval_records" / f"{json_slug(phase_id, phase_title)}_blocked_record.json"
    record = build_approval_record(
        phase_id=phase_id,
        phase_title=phase_title,
        status=BLOCKED,
        packet_status=str(packet["current_status"]),
        packet_path=packet_path,
        worker_path=packet.get("worker_prompt_path") if isinstance(packet.get("worker_prompt_path"), Path) else None,
        manifest_path=packet.get("manifest_path") if isinstance(packet.get("manifest_path"), Path) else None,
        handoff_dir=None,
        branch_plan_path=None,
        branch_name=None,
        output_root=output_root,
        reason=reason,
        override=False,
        commit_allowed=False,
        push_allowed=False,
        merge_allowed=False,
        generated_at=generated_at,
    )
    write_json(record_path, record)
    refresh_discovery_index(output_root)
    return record_path


def approve_packet(args: argparse.Namespace) -> Dict[str, str]:
    output_root = Path(args.output).resolve()
    packet_path = Path(args.packet).resolve()
    ensure_dirs(output_root)
    packet = load_packet(packet_path, output_root)

    phase_id = str(packet["phase_id"])
    phase_title = str(packet["phase_title"])
    packet_text = str(packet["packet_text"])
    packet_status = str(packet["current_status"])
    worker_path = packet["worker_prompt_path"]
    manifest_path = packet["manifest_path"]
    if not isinstance(worker_path, Path):
        raise TypeError("worker prompt path resolution failed")
    if manifest_path is not None and not isinstance(manifest_path, Path):
        raise TypeError("manifest path resolution failed")

    if args.reject:
        if not args.reason:
            raise ValueError("--reason is required when rejecting a packet")
        return reject_packet(args, packet, output_root, packet_path)

    if packet_status != STATUS_READY and not args.override:
        record_path = record_blocked(
            packet_path,
            output_root,
            packet,
            f"Approval blocked because packet status is {packet_status}. Use --override --reason only after review.",
        )
        raise PermissionError(
            f"packet status is {packet_status}; approval blocked. Block record written: {safe_relative(record_path, output_root)}"
        )

    if args.override and not args.reason:
        raise ValueError("--reason is required with --override")

    approval_status = APPROVED_OVERRIDE if args.override else APPROVED
    generated_at = utc_now()
    slug = json_slug(phase_id, phase_title)
    folder_slug = packet_slug(phase_id, phase_title)
    branch_name = args.branch_name or f"work/discovery/{folder_slug}"

    approval_record_path = output_root / "approval_records" / f"{slug}_approval_record.json"
    handoff_dir = output_root / "execution_handoffs" / folder_slug
    branch_plan_path = output_root / "branch_plans" / f"{slug}_branch_plan.json"

    if handoff_dir.exists():
        raise FileExistsError(f"handoff bundle already exists: {handoff_dir}")
    if approval_record_path.exists():
        raise FileExistsError(f"approval record already exists: {approval_record_path}")
    if branch_plan_path.exists():
        raise FileExistsError(f"branch plan already exists: {branch_plan_path}")

    handoff_dir.mkdir(parents=True, exist_ok=False)
    approval_record = build_approval_record(
        phase_id=phase_id,
        phase_title=phase_title,
        status=approval_status,
        packet_status=packet_status,
        packet_path=packet_path,
        worker_path=worker_path,
        manifest_path=manifest_path,
        handoff_dir=handoff_dir,
        branch_plan_path=branch_plan_path,
        branch_name=branch_name,
        output_root=output_root,
        reason=args.reason or "Approved after human review.",
        override=args.override,
        commit_allowed=args.allow_commit,
        push_allowed=args.allow_push,
        merge_allowed=args.allow_merge,
        generated_at=generated_at,
    )
    branch_plan = build_branch_plan(
        phase_id=phase_id,
        phase_title=phase_title,
        packet_path=packet_path,
        worker_path=worker_path,
        approval_record_path=approval_record_path,
        handoff_dir=handoff_dir,
        branch_name=branch_name,
        output_root=output_root,
        commit_allowed=args.allow_commit,
        push_allowed=args.allow_push,
        merge_allowed=args.allow_merge,
        generated_at=generated_at,
        packet_text=packet_text,
    )

    write_json(approval_record_path, approval_record)
    write_json(branch_plan_path, branch_plan)
    copy_file(packet_path, output_root / "approved_packets" / f"{slug}_phase_packet.md")
    copy_file(packet_path, handoff_dir / "phase_packet.md")
    copy_file(worker_path, handoff_dir / "worker_prompt.md")
    copy_file(approval_record_path, handoff_dir / "approval_record.json")
    copy_file(branch_plan_path, handoff_dir / "branch_plan.json")
    if manifest_path:
        copy_file(manifest_path, handoff_dir / "manifest_snapshot.json")
    (handoff_dir / "HANDOFF.md").write_text(
        render_handoff(
            phase_id=phase_id,
            phase_title=phase_title,
            approval_status=approval_status,
            approval_timestamp=generated_at,
            packet_path=packet_path,
            worker_path=worker_path,
            manifest_path=manifest_path,
            branch_plan_path=branch_plan_path,
            branch_name=branch_name,
            reason=args.reason or "Approved after human review.",
            output_root=output_root,
            commit_allowed=args.allow_commit,
            push_allowed=args.allow_push,
            merge_allowed=args.allow_merge,
        ),
        encoding="utf-8",
        newline="\n",
    )
    (handoff_dir / "README.md").write_text(
        render_handoff_readme(phase_id, phase_title, branch_name),
        encoding="utf-8",
        newline="\n",
    )
    refresh_discovery_index(output_root)

    return {
        "approval_status": approval_status,
        "approval_record": safe_relative(approval_record_path, output_root),
        "handoff_bundle": safe_relative(handoff_dir, output_root),
        "branch_plan": safe_relative(branch_plan_path, output_root),
        "proposed_branch_name": branch_name,
    }


def reject_packet(args: argparse.Namespace, packet: Dict[str, object], output_root: Path, packet_path: Path) -> Dict[str, str]:
    generated_at = utc_now()
    phase_id = str(packet["phase_id"])
    phase_title = str(packet["phase_title"])
    slug = json_slug(phase_id, phase_title)
    record_path = output_root / "approval_records" / f"{slug}_rejection_record.json"
    rejected_packet_path = output_root / "rejected_packets" / f"{slug}_phase_packet.md"

    if record_path.exists():
        raise FileExistsError(f"rejection record already exists: {record_path}")

    copy_file(packet_path, rejected_packet_path)
    record = build_approval_record(
        phase_id=phase_id,
        phase_title=phase_title,
        status=REJECTED,
        packet_status=str(packet["current_status"]),
        packet_path=packet_path,
        worker_path=packet.get("worker_prompt_path") if isinstance(packet.get("worker_prompt_path"), Path) else None,
        manifest_path=packet.get("manifest_path") if isinstance(packet.get("manifest_path"), Path) else None,
        handoff_dir=None,
        branch_plan_path=None,
        branch_name=None,
        output_root=output_root,
        reason=args.reason,
        override=False,
        commit_allowed=False,
        push_allowed=False,
        merge_allowed=False,
        generated_at=generated_at,
    )
    record["rejected_packet_snapshot"] = safe_relative(rejected_packet_path, output_root)
    write_json(record_path, record)
    refresh_discovery_index(output_root)

    return {
        "approval_status": REJECTED,
        "approval_record": safe_relative(record_path, output_root),
        "rejected_packet": safe_relative(rejected_packet_path, output_root),
    }


def render_result(result: Dict[str, str]) -> str:
    lines = ["# Discovery Lane Approval Result", ""]
    for key, value in result.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "No worker prompt was executed.",
            "No git branch was created.",
            "No commit, push, or merge was performed.",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Approve or reject a Discovery Lane phase packet.")
    parser.add_argument("--packet", required=True, help="Generated phase packet Markdown path.")
    parser.add_argument("--output", default="discovery_lane", help="Discovery Lane root or example output root.")
    parser.add_argument("--reject", action="store_true", help="Reject the packet instead of approving it.")
    parser.add_argument("--override", action="store_true", help="Approve a non-ready packet with an explicit reason.")
    parser.add_argument("--reason", default="", help="Human approval, rejection, or override reason.")
    parser.add_argument("--allow-commit", action="store_true", help="Record future commit permission only.")
    parser.add_argument("--allow-push", action="store_true", help="Record future push permission only.")
    parser.add_argument("--allow-merge", action="store_true", help="Record future merge permission only.")
    parser.add_argument("--branch-name", default="", help="Custom planned branch name. No branch is created.")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = approve_packet(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(render_result(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
