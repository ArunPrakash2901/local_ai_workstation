#!/usr/bin/env python3
"""Audit Product Development Lane artifacts without executing anything."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

REQUIRED_DIRS = (
    "contracts",
    "tools",
    "product_packets",
    "prd_briefs",
    "wireframe_briefs",
    "ui_ux_briefs",
    "feature_specs",
    "implementation_plans",
    "manifests",
    "reports",
    "examples",
)

REQUIRED_CONTRACTS = (
    "product_packet_contract.md",
    "prd_brief_contract.md",
    "wireframe_brief_contract.md",
    "ui_ux_brief_contract.md",
    "implementation_plan_contract.md",
)

REQUIRED_TOOLS = (
    "build_product_packet.py",
    "audit_product_development_lane.py",
    "product_dev_command.py",
)

VALID_ARTIFACT_STATUS = {"GENERATED_PRODUCT_DEVELOPMENT_PLANNING_ARTIFACTS"}
FORBIDDEN_TRUE_FLAGS = (
    "worker_prompts_executed",
    "branches_created",
    "git_actions_performed",
    "commit_performed",
    "push_performed",
    "merge_performed",
    "models_called",
    "application_code_generated",
    "discovery_artifacts_modified",
)


@dataclass
class AuditResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def read_json(path: Path, result: AuditResult) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        result.errors.append(f"invalid JSON manifest {path}: {exc}")
        return None
    if not isinstance(data, dict):
        result.errors.append(f"manifest root must be object: {path}")
        return None
    return data


def resolve_under(root: Path, relative_path: str, result: AuditResult, label: str) -> Path | None:
    try:
        candidate = (root / relative_path).resolve()
        root_resolved = root.resolve()
        if candidate != root_resolved and root_resolved not in candidate.parents:
            result.errors.append(f"{label} escapes product_development_lane: {relative_path}")
            return None
        if not candidate.exists():
            result.errors.append(f"{label} missing: {relative_path}")
            return None
        return candidate
    except Exception as exc:
        result.errors.append(f"{label} invalid path {relative_path!r}: {exc}")
        return None


def artifact_text_is_safe(path: Path, result: AuditResult) -> None:
    text = path.read_text(encoding="utf-8", errors="replace").lower()
    unsafe_claims = (
        "worker prompts were executed: true",
        "branches_created: true",
        "git_actions_performed: true",
        "commit_performed: true",
        "push_performed: true",
        "merge_performed: true",
        "models_called: true",
        "application code generated: true",
    )
    for claim in unsafe_claims:
        if claim in text:
            result.errors.append(f"artifact claims unsafe action: {path}: {claim}")
    if "no worker prompts were executed" not in text and "not execution" not in text:
        result.warnings.append(f"artifact lacks explicit non-execution wording: {path}")


def audit_product_development_lane(root: Path) -> AuditResult:
    root = root.resolve()
    result = AuditResult()
    if not root.exists():
        result.errors.append(f"product development root missing: {root}")
        return result

    for name in REQUIRED_DIRS:
        if not (root / name).is_dir():
            result.errors.append(f"required folder missing: {name}")
    for name in REQUIRED_CONTRACTS:
        if not (root / "contracts" / name).is_file():
            result.errors.append(f"required contract missing: contracts/{name}")
    for name in REQUIRED_TOOLS:
        if not (root / "tools" / name).is_file():
            result.errors.append(f"required tool missing: tools/{name}")

    manifest_paths = sorted((root / "manifests").glob("*_product_development_manifest.json"))
    result.counts["manifests"] = len(manifest_paths)
    result.counts["product_packets"] = len(list((root / "product_packets").glob("*.md"))) if (root / "product_packets").exists() else 0
    result.counts["prd_briefs"] = len(list((root / "prd_briefs").glob("*.md"))) if (root / "prd_briefs").exists() else 0
    result.counts["wireframe_briefs"] = len(list((root / "wireframe_briefs").glob("*.md"))) if (root / "wireframe_briefs").exists() else 0
    result.counts["ui_ux_briefs"] = len(list((root / "ui_ux_briefs").glob("*.md"))) if (root / "ui_ux_briefs").exists() else 0
    result.counts["feature_specs"] = len(list((root / "feature_specs").glob("*.md"))) if (root / "feature_specs").exists() else 0
    result.counts["implementation_plans"] = len(list((root / "implementation_plans").glob("*.md"))) if (root / "implementation_plans").exists() else 0
    result.counts["reports"] = len(list((root / "reports").glob("*.md"))) if (root / "reports").exists() else 0

    discovery_root = root.parent / "discovery_lane"
    for manifest_path in manifest_paths:
        manifest = read_json(manifest_path, result)
        if manifest is None:
            continue
        if manifest.get("artifact_status") not in VALID_ARTIFACT_STATUS:
            result.errors.append(f"invalid artifact_status in {manifest_path}: {manifest.get('artifact_status')!r}")
        for flag in FORBIDDEN_TRUE_FLAGS:
            if manifest.get(flag) is not False:
                result.errors.append(f"{manifest_path} must record {flag}=false")

        source_queue = manifest.get("source_execution_queue")
        if not isinstance(source_queue, str):
            result.errors.append(f"{manifest_path} missing source_execution_queue")
        else:
            queue_path = discovery_root / source_queue
            if not queue_path.exists():
                result.errors.append(f"source execution queue missing: {source_queue}")

        outputs = manifest.get("outputs")
        if not isinstance(outputs, dict):
            result.errors.append(f"{manifest_path} missing outputs mapping")
            continue
        for key in (
            "product_packet",
            "prd_brief",
            "wireframe_brief",
            "ui_ux_brief",
            "feature_spec",
            "implementation_plan",
            "report",
        ):
            output_rel = outputs.get(key)
            if not isinstance(output_rel, str):
                result.errors.append(f"{manifest_path} missing output path for {key}")
                continue
            output_path = resolve_under(root, output_rel, result, f"output {key}")
            if output_path and output_path.suffix == ".md":
                artifact_text_is_safe(output_path, result)

        wireframe_rel = outputs.get("wireframe_brief")
        ui_rel = outputs.get("ui_ux_brief")
        for label, item in (("wireframe", wireframe_rel), ("ui_ux", ui_rel)):
            if isinstance(item, str):
                path = root / item
                if path.exists():
                    text = path.read_text(encoding="utf-8", errors="replace")
                    if "NOT_SPECIFIED_IN_DISCOVERY_HANDOFF" not in text and "No UI is required" not in text:
                        result.warnings.append(f"{label} brief does not explicitly mark unspecified UI details: {item}")

    return result


def render_audit(result: AuditResult, root: Path) -> str:
    lines = [
        "# Product Development Lane Audit",
        "",
        f"- root: `{root}`",
        f"- result: {'PASS' if result.ok else 'FAIL'}",
        f"- errors: {len(result.errors)}",
        f"- warnings: {len(result.warnings)}",
        "",
        "## Counts",
        "",
    ]
    for key in sorted(result.counts):
        lines.append(f"- {key}: {result.counts[key]}")
    lines.extend(["", "## Errors", ""])
    lines.extend(f"- {error}" for error in result.errors) if result.errors else lines.append("None.")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {warning}" for warning in result.warnings) if result.warnings else lines.append("None.")
    lines.extend(
        [
            "",
            "## Execution Boundary",
            "",
            "- Audit is read-only.",
            "- No worker prompt was executed.",
            "- No branch was created, checked out, pushed, merged, or deleted.",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit Product Development Lane non-executing artifacts.")
    parser.add_argument("--root", default="product_development_lane", help="Product Development Lane root")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root)
    result = audit_product_development_lane(root)
    print(render_audit(result, root))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

