#!/usr/bin/env python3
"""Create set-level intake records for phase-wise research reports.

Discovery Lane starts after a human has already created phase-wise Markdown
research reports. This tool validates the set of reports as a group. It does
not generate worker prompts, execute code, call models, move source files, or
perform git actions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import ingest_research_reports


SET_READY = "READY_FOR_INGEST"
SET_NEEDS_DECISION = "NEEDS_HUMAN_DECISION"
SET_NOT_READY = "NOT_READY"
VALID_SET_STATUSES = {SET_READY, SET_NEEDS_DECISION, SET_NOT_READY}

OUTPUT_DIRS = (
    "research_sets",
    "research_set_manifests",
    "intake_reports",
)

PHASE_NUMBER_RE = re.compile(r"(?:^|[^0-9])0*([0-9]{1,3})(?:[^0-9]|$)")
SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    slug = SLUG_RE.sub("_", value.strip().lower()).strip("_")
    return slug or "research_set"


def ensure_output_dirs(output_root: Path, set_id: str) -> None:
    for directory in OUTPUT_DIRS:
        (output_root / directory).mkdir(parents=True, exist_ok=True)
    (output_root / "research_sets" / set_id).mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        try:
            return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
        except ValueError:
            return path.resolve().as_posix()


def infer_set_id(input_path: Path) -> str:
    name = input_path.name if input_path.name else "research_set"
    if name.lower() == "inbox":
        return "inbox_research_set"
    return slugify(name)


def infer_set_title(set_id: str, reports: list[dict[str, object]]) -> str:
    if not reports:
        return set_id.replace("_", " ").title()
    first_title = str(reports[0].get("detected_phase_title", "")).strip()
    if first_title:
        return f"{set_id.replace('_', ' ').title()} Research Set"
    return set_id.replace("_", " ").title()


def phase_number(value: str) -> Optional[int]:
    match = PHASE_NUMBER_RE.search(value)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def detect_missing_phase_numbers(phase_ids: Iterable[str]) -> list[int]:
    numbers = sorted({number for value in phase_ids if (number := phase_number(value)) is not None})
    if len(numbers) < 2:
        return []
    expected = set(range(numbers[0], numbers[-1] + 1))
    return sorted(expected.difference(numbers))


def summarize_reports(reports: list[dict[str, object]]) -> dict[str, object]:
    phase_ids = [str(report.get("detected_phase_id", "")).strip() for report in reports]
    phase_id_counts = Counter(phase_id for phase_id in phase_ids if phase_id)
    return {
        "duplicate_phase_ids": sorted(phase_id for phase_id, count in phase_id_counts.items() if count > 1),
        "missing_or_unclear_phase_ids": sorted(
            str(report.get("filename", ""))
            for report in reports
            if not str(report.get("detected_phase_id", "")).strip() or report.get("phase_id_inferred") is True
        ),
        "unclear_phase_titles": sorted(
            str(report.get("filename", ""))
            for report in reports
            if not str(report.get("detected_phase_title", "")).strip() or report.get("phase_title_inferred") is True
        ),
        "missing_phase_numbers": detect_missing_phase_numbers(phase_ids),
    }


def report_has_inferred_phase_id(analysis: ingest_research_reports.ReportAnalysis) -> bool:
    return any(flag == "Phase ID was inferred from the report filename." for flag in analysis.human_decision_flags)


def report_has_inferred_phase_title(analysis: ingest_research_reports.ReportAnalysis) -> bool:
    return any(
        flag
        in {
            "Phase Title was inferred from the first Markdown H1 heading.",
            "Phase Title was inferred from the report filename.",
        }
        for flag in analysis.human_decision_flags
    )


def analyze_report(path: Path, output_root: Path, generated_at: str) -> dict[str, object]:
    text = path.read_text(encoding="utf-8", errors="replace")
    analysis = ingest_research_reports.validate_report(path, text, generated_at)
    return {
        "source_path": safe_relative(path, output_root),
        "filename": path.name,
        "sha256": sha256_file(path),
        "detected_phase_id": analysis.phase_id,
        "detected_phase_title": analysis.phase_title,
        "validation_status": analysis.status,
        "missing_required_sections": analysis.missing_required,
        "missing_recommended_sections": analysis.missing_recommended,
        "partial_heading_matches": analysis.partial_sections,
        "human_decision_flags": analysis.human_decision_flags,
        "phase_id_inferred": report_has_inferred_phase_id(analysis),
        "phase_title_inferred": report_has_inferred_phase_title(analysis),
    }


def build_research_set_manifest(input_path: Path, output_root: Path, set_id: str) -> dict[str, object]:
    if not input_path.exists():
        raise FileNotFoundError(f"input path not found: {input_path}")
    if not input_path.is_dir():
        raise NotADirectoryError(f"input path is not a directory: {input_path}")

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    report_paths = sorted(path for path in input_path.glob("*.md") if path.is_file())
    reports = [analyze_report(path, output_root, generated_at) for path in report_paths]

    summary = summarize_reports(reports)
    duplicate_phase_ids = summary["duplicate_phase_ids"]
    missing_or_unclear_phase_ids = summary["missing_or_unclear_phase_ids"]
    unclear_phase_titles = summary["unclear_phase_titles"]
    missing_phase_numbers = summary["missing_phase_numbers"]

    validation_statuses = [str(report.get("validation_status", "")) for report in reports]
    if not reports or duplicate_phase_ids or any(status == ingest_research_reports.STATUS_NOT_READY for status in validation_statuses):
        set_status = SET_NOT_READY
    elif missing_or_unclear_phase_ids or unclear_phase_titles or missing_phase_numbers or any(
        status == ingest_research_reports.STATUS_NEEDS_DECISION for status in validation_statuses
    ):
        set_status = SET_NEEDS_DECISION
    else:
        set_status = SET_READY

    if set_status == SET_READY:
        recommended_next_action = "Run `ws discovery ingest` after human review of the intake report."
    elif set_status == SET_NEEDS_DECISION:
        recommended_next_action = "Review intake report in VS Code and resolve unclear phase metadata before ingest."
    else:
        recommended_next_action = "Fix missing/duplicate/not-ready reports before running Discovery Lane ingest."

    return {
        "set_id": set_id,
        "set_title": infer_set_title(set_id, reports),
        "source_input_path": safe_relative(input_path, output_root),
        "created_timestamp": generated_at,
        "report_count": len(reports),
        "reports": reports,
        "duplicate_phase_ids": duplicate_phase_ids,
        "missing_or_unclear_phase_ids": missing_or_unclear_phase_ids,
        "unclear_phase_titles": unclear_phase_titles,
        "missing_phase_numbers": missing_phase_numbers,
        "set_status": set_status,
        "recommended_next_action": recommended_next_action,
        "generated_by": "Discovery Lane research set intake v1.3",
        "generated_files": {
            "research_set_record": f"research_sets/{set_id}/research_set.json",
            "research_set_manifest": f"research_set_manifests/{set_id}_manifest.json",
            "intake_report": f"intake_reports/{set_id}_intake_report.md",
        },
    }


def render_list(values: Iterable[object], empty: str = "None.") -> str:
    items = [str(value) for value in values if str(value).strip()]
    if not items:
        return empty
    return "\n".join(f"- {item}" for item in items)


def render_intake_report(manifest: dict[str, object]) -> str:
    reports = manifest.get("reports", [])
    if not isinstance(reports, list):
        reports = []

    lines = [
        f"# Research Set Intake Report: {manifest.get('set_id', '')}",
        "",
        "Discovery Lane starts after phase-wise Deep Research reports already exist as Markdown files.",
        "This intake report validates the report set only. It does not generate worker prompts, execute work, call models, or create branches.",
        "",
        "## Research Set ID",
        "",
        str(manifest.get("set_id", "")),
        "",
        "## Source Folder",
        "",
        f"`{manifest.get('source_input_path', '')}`",
        "",
        "## Report Count",
        "",
        str(manifest.get("report_count", 0)),
        "",
        "## Set Status",
        "",
        str(manifest.get("set_status", "")),
        "",
        "## Detected Phases",
        "",
    ]
    if reports:
        lines.extend(
            [
                "| File | Phase ID | Phase Title | Validation Status | Missing Required Sections |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for report in reports:
            if not isinstance(report, dict):
                continue
            missing = report.get("missing_required_sections", [])
            missing_text = ", ".join(str(item) for item in missing) if isinstance(missing, list) else ""
            lines.append(
                "| `{filename}` | {phase_id} | {phase_title} | {status} | {missing} |".format(
                    filename=report.get("filename", ""),
                    phase_id=report.get("detected_phase_id", ""),
                    phase_title=report.get("detected_phase_title", ""),
                    status=report.get("validation_status", ""),
                    missing=missing_text or "None",
                )
            )
    else:
        lines.append("No Markdown research reports found.")

    lines.extend(
        [
            "",
            "## Duplicate Phase IDs",
            "",
            render_list(manifest.get("duplicate_phase_ids", [])),
            "",
            "## Missing/Unclear Phase IDs",
            "",
            render_list(manifest.get("missing_or_unclear_phase_ids", [])),
            "",
            "## Unclear Phase Titles",
            "",
            render_list(manifest.get("unclear_phase_titles", [])),
            "",
            "## Missing Phase Ordering",
            "",
            render_list(manifest.get("missing_phase_numbers", [])),
            "",
            "## Contract Compatibility Summary",
            "",
        ]
    )
    for report in reports:
        if not isinstance(report, dict):
            continue
        flags = report.get("human_decision_flags", [])
        flag_count = len(flags) if isinstance(flags, list) else 0
        lines.append(
            f"- `{report.get('filename', '')}`: {report.get('validation_status', '')}; "
            f"missing_required={len(report.get('missing_required_sections', []) or [])}; "
            f"human_decision_flags={flag_count}"
        )

    lines.extend(
        [
            "",
            "## Recommended Next Action",
            "",
            str(manifest.get("recommended_next_action", "")),
            "",
            "## Files Safe To Open In VS Code",
            "",
        ]
    )
    for report in reports:
        if isinstance(report, dict):
            lines.append(f"- `{report.get('source_path', '')}`")

    human_decisions: list[str] = []
    for field, label in (
        ("duplicate_phase_ids", "Duplicate phase IDs"),
        ("missing_or_unclear_phase_ids", "Missing or unclear phase IDs"),
        ("unclear_phase_titles", "Unclear phase titles"),
        ("missing_phase_numbers", "Missing phase numbers"),
    ):
        values = manifest.get(field, [])
        if isinstance(values, list) and values:
            human_decisions.append(f"{label}: {', '.join(str(value) for value in values)}")
    for report in reports:
        if not isinstance(report, dict):
            continue
        flags = report.get("human_decision_flags", [])
        if isinstance(flags, list):
            for flag in flags:
                human_decisions.append(f"{report.get('filename', '')}: {flag}")

    lines.extend(
        [
            "",
            "## Human Decisions Required",
            "",
            render_list(human_decisions),
            "",
            "## Execution Boundary",
            "",
            "- Intake-set does not generate phase packets or worker prompts.",
            "- Intake-set does not approve packets or create handoff bundles.",
            "- Intake-set does not execute code, call models, browse, or run git commands.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_research_set(manifest: dict[str, object], output_root: Path) -> dict[str, Path]:
    set_id = str(manifest["set_id"])
    ensure_output_dirs(output_root, set_id)
    manifest_path = output_root / "research_set_manifests" / f"{set_id}_manifest.json"
    record_path = output_root / "research_sets" / set_id / "research_set.json"
    report_path = output_root / "intake_reports" / f"{set_id}_intake_report.md"
    manifest_text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    report_text = render_intake_report(manifest)
    manifest_path.write_text(manifest_text, encoding="utf-8", newline="\n")
    record_path.write_text(manifest_text, encoding="utf-8", newline="\n")
    report_path.write_text(report_text, encoding="utf-8", newline="\n")
    return {
        "research_set_manifest": manifest_path,
        "research_set_record": record_path,
        "intake_report": report_path,
    }


def intake_research_set(input_path: Path, output_root: Path, set_id: str | None = None) -> tuple[dict[str, object], dict[str, Path]]:
    resolved_set_id = slugify(set_id) if set_id else infer_set_id(input_path)
    output_root.mkdir(parents=True, exist_ok=True)
    manifest = build_research_set_manifest(input_path, output_root, resolved_set_id)
    paths = write_research_set(manifest, output_root)
    return manifest, paths


def render_summary(manifest: dict[str, object], paths: dict[str, Path], output_root: Path) -> str:
    lines = [
        "# Discovery Research Set Intake",
        "",
        f"- set_id: {manifest.get('set_id', '')}",
        f"- set_status: {manifest.get('set_status', '')}",
        f"- report_count: {manifest.get('report_count', 0)}",
        f"- duplicate_phase_ids: {len(manifest.get('duplicate_phase_ids', []) or [])}",
        f"- missing_or_unclear_phase_ids: {len(manifest.get('missing_or_unclear_phase_ids', []) or [])}",
        f"- unclear_phase_titles: {len(manifest.get('unclear_phase_titles', []) or [])}",
        "",
        "## Generated Files",
        "",
    ]
    for label, path in sorted(paths.items()):
        lines.append(f"- {label}: `{safe_relative(path, output_root)}`")
    lines.extend(
        [
            "",
            "## Recommended Next Action",
            "",
            str(manifest.get("recommended_next_action", "")),
            "",
            "No phase packet, worker prompt, approval, branch, or execution action was created.",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a set of already-created phase-wise Markdown research reports."
    )
    parser.add_argument("--input", required=True, help="Folder containing phase-wise Markdown research reports.")
    parser.add_argument("--output", default="discovery_lane", help="Discovery Lane output root.")
    parser.add_argument("--set-id", default="", help="Optional research set id override.")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        manifest, paths = intake_research_set(Path(args.input), Path(args.output), args.set_id or None)
        print(render_summary(manifest, paths, Path(args.output)))
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
