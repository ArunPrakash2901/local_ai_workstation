#!/usr/bin/env python3
"""Audit Product Development Lane review artifacts."""

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
    "review_artifacts",
    "review_artifacts/contracts",
    "review_artifacts/html",
    "review_artifacts/manifests",
    "review_artifacts/reports",
)

REQUIRED_DOCS = (
    "review_artifacts/contracts/review_bucket_doctrine.md",
    "review_artifacts/contracts/html_review_surface_contract.md",
)

@dataclass
class AuditResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

def audit_review_artifacts(root: Path) -> AuditResult:
    result = AuditResult()
    root = root.resolve()
    
    if not root.exists():
        result.errors.append(f"Root missing: {root}")
        return result

    for d in REQUIRED_DIRS:
        if not (root / d).is_dir():
            result.errors.append(f"Required folder missing: {d}")

    for doc in REQUIRED_DOCS:
        if not (root / doc).is_file():
            result.errors.append(f"Required documentation missing: {doc}")

    manifest_dir = root / "review_artifacts/manifests"
    if not manifest_dir.exists():
        return result

    manifest_paths = list(manifest_dir.glob("*_review_artifact_manifest.json"))
    result.counts["review_manifests"] = len(manifest_paths)

    for mp in manifest_paths:
        try:
            with mp.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            result.errors.append(f"Invalid JSON manifest {mp}: {e}")
            continue

        set_id = data.get("set_id")
        if not set_id:
            result.errors.append(f"Manifest missing set_id: {mp}")
            continue

        dashboard_rel = data.get("dashboard")
        if not dashboard_rel:
            result.errors.append(f"Manifest missing dashboard path: {mp}")
        else:
            dashboard_path = root.parent / dashboard_rel
            if not dashboard_path.exists():
                result.errors.append(f"Dashboard file missing: {dashboard_rel}")

        artifacts = data.get("artifacts", {})
        if not artifacts:
            result.errors.append(f"Manifest has no artifacts: {mp}")
        
        for key, art in artifacts.items():
            html_rel = art.get("html_path")
            source_rel = art.get("source_path")
            source_hash = art.get("source_hash")

            if not html_rel:
                result.errors.append(f"Artifact {key} missing html_path in {mp}")
            else:
                html_path = root.parent / html_rel
                if not html_path.exists():
                    result.errors.append(f"HTML surface missing: {html_rel}")
                else:
                    audit_html_safety(html_path, result)

            if not source_rel:
                result.errors.append(f"Artifact {key} missing source_path in {mp}")
            else:
                source_path = root / source_rel
                if not source_path.exists():
                    result.errors.append(f"Source artifact missing: {source_rel}")

            if not source_hash:
                result.errors.append(f"Artifact {key} missing source_hash in {mp}")

        report_path = root / f"review_artifacts/reports/{set_id}_review_artifact_report.md"
        if not report_path.exists():
            result.errors.append(f"Review report missing: {report_path.relative_to(root)}")

    return result

def audit_html_safety(path: Path, result: AuditResult) -> None:
    content = path.read_text(encoding="utf-8")
    
    if "Review surface only. Canonical source remains Markdown/JSON." not in content:
        result.errors.append(f"HTML surface lacks canonical source warning: {path}")
    
    if "No execution of worker prompts occurred." not in content:
        result.errors.append(f"HTML surface lacks execution disclaimer: {path}")

    if "No branches were created" not in content:
        result.errors.append(f"HTML surface lacks branching disclaimer: {path}")

    if "http://" in content or "https://" in content:
        # Check if it's a real external link or just part of a string
        # Our generator shouldn't have any.
        # This might be too strict if there are URLs in the source content, 
        # but the task says "No external CDN URLs".
        # We'll allow it if it's just in the content section (pre-escaped)
        # but we should flag it if it's in a <script> or <link> or <img>.
        if "<script" in content and ("src=" in content.lower()):
            result.errors.append(f"HTML surface contains external script: {path}")
        if "<link" in content and ("href=" in content.lower()):
            result.errors.append(f"HTML surface contains external link/stylesheet: {path}")
        if "<img" in content and ("src=\"http" in content.lower()):
            result.errors.append(f"HTML surface contains external image: {path}")

def render_audit(result: AuditResult, root: Path) -> str:
    lines = [
        "# Review Artifacts Audit",
        "",
        f"- Root: `{root}`",
        f"- Result: {'PASS' if result.ok else 'FAIL'}",
        f"- Errors: {len(result.errors)}",
        f"- Warnings: {len(result.warnings)}",
        "",
        "## Counts",
        "",
    ]
    for key, count in result.counts.items():
        lines.append(f"- {key}: {count}")
    
    lines.extend(["", "## Errors", ""])
    if not result.errors:
        lines.append("None.")
    else:
        for err in result.errors:
            lines.append(f"- {err}")

    lines.extend(["", "## Warnings", ""])
    if not result.warnings:
        lines.append("None.")
    else:
        for warn in result.warnings:
            lines.append(f"- {warn}")

    lines.extend([
        "",
        "## Safety Claims",
        "",
        "- Audit is read-only.",
        "- No processes were started.",
        "- HTML surfaces were validated for safety warnings.",
    ])
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Audit review artifacts.")
    parser.add_argument("--root", default="product_development_lane", help="Path to lane root")
    
    args = parser.parse_args()
    root = Path(args.root)
    
    result = audit_review_artifacts(root)
    print(render_audit(result, root))
    sys.exit(0 if result.ok else 1)

if __name__ == "__main__":
    main()
