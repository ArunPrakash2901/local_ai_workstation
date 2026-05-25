#!/usr/bin/env python3
"""Ingest one approved research set into phase packets and worker prompts.

This tool consumes a v1.3 research-set manifest. It only operates after the set
is `READY_FOR_INGEST`, verifies that source report checksums still match, and
generates set-prefixed Discovery Lane phase artifacts. It does not approve
packets, create handoffs, create branches, execute workers, or call models.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import ingest_research_reports
import intake_research_set


STATUS_INGESTED = "INGESTED"
STATUS_SOURCE_CHANGED = "NOT_INGESTED_SOURCE_CHANGED"
STATUS_SET_NOT_READY = "NOT_INGESTED_SET_NOT_READY"
STATUS_MISSING_SOURCE = "NOT_INGESTED_MISSING_SOURCE"
STATUS_VALIDATION_FAILED = "NOT_INGESTED_VALIDATION_FAILED"
VALID_INGEST_STATUSES = {
    STATUS_INGESTED,
    STATUS_SOURCE_CHANGED,
    STATUS_SET_NOT_READY,
    STATUS_MISSING_SOURCE,
    STATUS_VALIDATION_FAILED,
}

OUTPUT_DIRS = (
    "research_set_ingests",
    "research_set_ingest_reports",
)


def safe_relative(path: Path, root: Path) -> str:
    return ingest_research_reports.safe_relative(path, root)


def ensure_output_dirs(root: Path) -> None:
    for directory in OUTPUT_DIRS:
        (root / directory).mkdir(parents=True, exist_ok=True)


def load_research_set_manifest(root: Path, set_id: str) -> tuple[dict[str, object], Path]:
    manifest_path = root / "research_set_manifests" / f"{set_id}_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"research set manifest not found: {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"research set manifest must be a JSON object: {manifest_path}")
    return data, manifest_path


def resolve_source_path(root: Path, source_path: str) -> Path:
    raw = Path(source_path)
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
    candidates.extend([root / raw, Path.cwd() / raw])
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def failed_manifest(
    *,
    set_id: str,
    root: Path,
    manifest_path: Path,
    source_reports: list[dict[str, object]],
    ingest_status: str,
    errors: list[str],
    warnings: Optional[list[str]] = None,
    checksum_status: str = "NOT_VERIFIED",
) -> dict[str, object]:
    return {
        "set_id": set_id,
        "source_research_set_manifest": safe_relative(manifest_path, root),
        "ingest_timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "report_count": len(source_reports),
        "source_reports": source_reports,
        "generated_phase_packets": [],
        "generated_worker_prompts": [],
        "generated_manifests": [],
        "checksum_verification_status": checksum_status,
        "ingest_status": ingest_status,
        "errors": errors,
        "warnings": warnings or [],
        "generated_by": "Discovery Lane research set ingest v1.4",
        "approvals_created": False,
        "handoffs_created": False,
        "branches_created": False,
    }


def verify_sources(root: Path, manifest: dict[str, object]) -> tuple[list[Path], list[dict[str, object]], list[str], list[str], str]:
    reports = manifest.get("reports", [])
    if not isinstance(reports, list):
        return [], [], ["research set manifest reports field is not a list"], [], "NOT_VERIFIED"

    source_paths: list[Path] = []
    source_records: list[dict[str, object]] = []
    errors: list[str] = []
    warnings: list[str] = []
    checksum_mismatches = 0

    for index, report in enumerate(reports):
        if not isinstance(report, dict):
            errors.append(f"report entry {index} is not an object")
            continue
        source_path_text = str(report.get("source_path", ""))
        expected_sha = str(report.get("sha256", ""))
        source_path = resolve_source_path(root, source_path_text)
        record = {
            "source_path": safe_relative(source_path, root) if source_path.exists() else source_path_text,
            "filename": report.get("filename", ""),
            "expected_sha256": expected_sha,
            "actual_sha256": "",
            "checksum_status": "NOT_VERIFIED",
        }
        if not source_path.exists():
            record["checksum_status"] = "MISSING_SOURCE"
            errors.append(f"source report missing: {source_path_text}")
            source_records.append(record)
            continue
        actual_sha = intake_research_set.sha256_file(source_path)
        record["actual_sha256"] = actual_sha
        if not expected_sha:
            record["checksum_status"] = "MISSING_EXPECTED_CHECKSUM"
            warnings.append(f"missing expected checksum for {source_path_text}")
        elif actual_sha != expected_sha:
            record["checksum_status"] = "MISMATCH"
            checksum_mismatches += 1
            errors.append(f"checksum mismatch for {source_path_text}")
        else:
            record["checksum_status"] = "MATCH"
        source_records.append(record)
        source_paths.append(source_path)

    if errors and any(record.get("checksum_status") == "MISSING_SOURCE" for record in source_records):
        checksum_status = "FAILED_MISSING_SOURCE"
    elif checksum_mismatches:
        checksum_status = "FAILED_SOURCE_CHANGED"
    elif warnings:
        checksum_status = "WARNINGS"
    else:
        checksum_status = "MATCH"
    return source_paths, source_records, errors, warnings, checksum_status


def write_phase_outputs(
    *,
    root: Path,
    set_id: str,
    manifest_path: Path,
    source_paths: list[Path],
    generated_at: str,
    overwrite: bool,
) -> tuple[list[ingest_research_reports.ReportAnalysis], list[str]]:
    analyses: list[ingest_research_reports.ReportAnalysis] = []
    warnings: list[str] = []
    ingest_research_reports.ensure_output_dirs(root)
    for source_path in source_paths:
        text = source_path.read_text(encoding="utf-8", errors="replace")
        analysis = ingest_research_reports.validate_report(source_path, text, generated_at)
        try:
            analysis = ingest_research_reports.write_report_outputs(
                analysis,
                root,
                filename_prefix=set_id,
                overwrite=overwrite,
            )
        except FileExistsError:
            raise
        manifest_file = root / str(analysis.generated_files["manifest"])
        phase_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        phase_manifest["research_set_id"] = set_id
        phase_manifest["source_research_set_manifest"] = safe_relative(manifest_path, root)
        manifest_file.write_text(
            json.dumps(phase_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        if analysis.status != ingest_research_reports.STATUS_READY:
            warnings.append(f"{source_path} generated packet status {analysis.status}")
        analyses.append(analysis)
    return analyses, warnings


def build_ingest_manifest(root: Path, set_id: str, overwrite: bool = False) -> dict[str, object]:
    research_set_manifest, research_set_manifest_path = load_research_set_manifest(root, set_id)
    ingest_timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    set_status = str(research_set_manifest.get("set_status", ""))
    reports = research_set_manifest.get("reports", [])
    report_count = len(reports) if isinstance(reports, list) else 0

    if set_status != intake_research_set.SET_READY:
        return failed_manifest(
            set_id=set_id,
            root=root,
            manifest_path=research_set_manifest_path,
            source_reports=[],
            ingest_status=STATUS_SET_NOT_READY,
            errors=[f"research set status is {set_status}; expected READY_FOR_INGEST"],
        )

    source_paths, source_records, errors, warnings, checksum_status = verify_sources(root, research_set_manifest)
    if errors:
        if checksum_status == "FAILED_SOURCE_CHANGED":
            status = STATUS_SOURCE_CHANGED
        elif checksum_status == "FAILED_MISSING_SOURCE":
            status = STATUS_MISSING_SOURCE
        else:
            status = STATUS_VALIDATION_FAILED
        return failed_manifest(
            set_id=set_id,
            root=root,
            manifest_path=research_set_manifest_path,
            source_reports=source_records,
            ingest_status=status,
            errors=errors,
            warnings=warnings,
            checksum_status=checksum_status,
        )

    try:
        analyses, output_warnings = write_phase_outputs(
            root=root,
            set_id=set_id,
            manifest_path=research_set_manifest_path,
            source_paths=source_paths,
            generated_at=ingest_timestamp,
            overwrite=overwrite,
        )
    except Exception as exc:
        return failed_manifest(
            set_id=set_id,
            root=root,
            manifest_path=research_set_manifest_path,
            source_reports=source_records,
            ingest_status=STATUS_VALIDATION_FAILED,
            errors=[str(exc)],
            warnings=warnings,
            checksum_status=checksum_status,
        )

    index_text = ingest_research_reports.render_discovery_index(root, ingest_timestamp)
    (root / "discovery_index.md").write_text(index_text, encoding="utf-8", newline="\n")

    return {
        "set_id": set_id,
        "source_research_set_manifest": safe_relative(research_set_manifest_path, root),
        "ingest_timestamp": ingest_timestamp,
        "report_count": report_count,
        "source_reports": source_records,
        "generated_phase_packets": [analysis.generated_files["phase_packet"] for analysis in analyses],
        "generated_worker_prompts": [analysis.generated_files["worker_prompt"] for analysis in analyses],
        "generated_manifests": [analysis.generated_files["manifest"] for analysis in analyses],
        "checksum_verification_status": checksum_status,
        "ingest_status": STATUS_INGESTED,
        "errors": [],
        "warnings": warnings + output_warnings,
        "overwrite": overwrite,
        "generated_by": "Discovery Lane research set ingest v1.4",
        "approvals_created": False,
        "handoffs_created": False,
        "branches_created": False,
    }


def render_ingest_report(ingest_manifest: dict[str, object]) -> str:
    lines = [
        f"# Research Set Ingest Report: {ingest_manifest.get('set_id', '')}",
        "",
        "Ingest-set converts one READY_FOR_INGEST research set into phase packets and worker prompts.",
        "It does not approve packets, create handoffs, create branches, execute worker prompts, or call models.",
        "",
        "## Ingest Status",
        "",
        str(ingest_manifest.get("ingest_status", "")),
        "",
        "## Source Research Set Manifest",
        "",
        f"`{ingest_manifest.get('source_research_set_manifest', '')}`",
        "",
        "## Checksum Verification Status",
        "",
        str(ingest_manifest.get("checksum_verification_status", "")),
        "",
        "## Source Reports",
        "",
    ]
    for report in ingest_manifest.get("source_reports", []) or []:
        if isinstance(report, dict):
            lines.append(
                f"- `{report.get('source_path', '')}`: {report.get('checksum_status', '')}"
            )
    lines.extend(["", "## Generated Phase Packets", ""])
    lines.extend([f"- `{path}`" for path in ingest_manifest.get("generated_phase_packets", []) or []] or ["None."])
    lines.extend(["", "## Generated Worker Prompts", ""])
    lines.extend([f"- `{path}`" for path in ingest_manifest.get("generated_worker_prompts", []) or []] or ["None."])
    lines.extend(["", "## Generated Manifests", ""])
    lines.extend([f"- `{path}`" for path in ingest_manifest.get("generated_manifests", []) or []] or ["None."])
    lines.extend(["", "## Errors", ""])
    lines.extend([f"- {error}" for error in ingest_manifest.get("errors", []) or []] or ["None."])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {warning}" for warning in ingest_manifest.get("warnings", []) or []] or ["None."])
    lines.extend(
        [
            "",
            "## Execution Boundary",
            "",
            "- No approval record was created.",
            "- No handoff bundle was created.",
            "- No branch was created.",
            "- No worker prompt was executed.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_ingest_records(root: Path, ingest_manifest: dict[str, object]) -> dict[str, Path]:
    ensure_output_dirs(root)
    set_id = str(ingest_manifest["set_id"])
    manifest_path = root / "research_set_ingests" / f"{set_id}_ingest_manifest.json"
    report_path = root / "research_set_ingest_reports" / f"{set_id}_ingest_report.md"
    manifest_path.write_text(
        json.dumps(ingest_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    report_path.write_text(render_ingest_report(ingest_manifest), encoding="utf-8", newline="\n")
    return {"ingest_manifest": manifest_path, "ingest_report": report_path}


def ingest_research_set(root: Path, set_id: str, overwrite: bool = False) -> tuple[dict[str, object], dict[str, Path]]:
    root.mkdir(parents=True, exist_ok=True)
    ingest_manifest = build_ingest_manifest(root, set_id, overwrite=overwrite)
    paths = write_ingest_records(root, ingest_manifest)
    return ingest_manifest, paths


def render_summary(ingest_manifest: dict[str, object], paths: dict[str, Path], root: Path) -> str:
    lines = [
        "# Discovery Research Set Ingest",
        "",
        f"- set_id: {ingest_manifest.get('set_id', '')}",
        f"- ingest_status: {ingest_manifest.get('ingest_status', '')}",
        f"- report_count: {ingest_manifest.get('report_count', 0)}",
        f"- checksum_verification_status: {ingest_manifest.get('checksum_verification_status', '')}",
        "",
        "## Generated Files",
        "",
    ]
    for label, path in sorted(paths.items()):
        lines.append(f"- {label}: `{safe_relative(path, root)}`")
    lines.extend(
        [
            "",
            "## Phase Artifacts",
            "",
        ]
    )
    for path in ingest_manifest.get("generated_phase_packets", []) or []:
        lines.append(f"- phase_packet: `{path}`")
    for path in ingest_manifest.get("generated_worker_prompts", []) or []:
        lines.append(f"- worker_prompt: `{path}`")
    if not ingest_manifest.get("generated_phase_packets"):
        lines.append("None.")
    lines.extend(["", "## Errors", ""])
    lines.extend([f"- {error}" for error in ingest_manifest.get("errors", []) or []] or ["None."])
    lines.extend(["", "No approval, handoff, branch, or execution action was created."])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest one READY_FOR_INGEST Discovery Lane research set.")
    parser.add_argument("--set-id", required=True, help="Research set id from research_set_manifests/<set_id>_manifest.json.")
    parser.add_argument("--root", default="discovery_lane", help="Discovery Lane root.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing generated packet/prompt/manifest files.")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        manifest, paths = ingest_research_set(Path(args.root), args.set_id, overwrite=args.overwrite)
        print(render_summary(manifest, paths, Path(args.root)))
        return 0 if manifest.get("ingest_status") == STATUS_INGESTED else 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
