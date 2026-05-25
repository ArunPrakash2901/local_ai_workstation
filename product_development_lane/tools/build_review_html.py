#!/usr/bin/env python3
"""Build static HTML review surfaces for Product Development Lane artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True

CSS_TEMPLATE = """
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem;
    background-color: #f9f9f9;
}
header {
    border-bottom: 2px solid #eee;
    margin-bottom: 2rem;
    padding-bottom: 1rem;
}
.banner {
    background-color: #fff3cd;
    border: 1px solid #ffeeba;
    color: #856404;
    padding: 1rem;
    border-radius: 4px;
    margin-bottom: 2rem;
    font-weight: bold;
    text-align: center;
}
.metadata {
    background-color: #fff;
    border: 1px solid #ddd;
    padding: 1rem;
    border-radius: 4px;
    margin-bottom: 2rem;
    font-size: 0.9rem;
}
.metadata dl {
    display: grid;
    grid-template-columns: 200px 1fr;
    margin: 0;
}
.metadata dt {
    font-weight: bold;
    color: #666;
}
.metadata dd {
    margin: 0;
    font-family: monospace;
    word-break: break-all;
}
section {
    background-color: #fff;
    border: 1px solid #ddd;
    padding: 1.5rem;
    border-radius: 4px;
    margin-bottom: 2rem;
}
h1, h2, h3 {
    color: #2c3e50;
}
h1 { border-bottom: 1px solid #eee; padding-bottom: 0.5rem; }
.content pre {
    white-space: pre-wrap;
    word-wrap: break-word;
    background-color: #f8f9fa;
    padding: 1rem;
    border: 1px solid #e9ecef;
    border-radius: 4px;
    font-family: inherit;
    font-size: 1rem;
}
.checklist {
    list-style: none;
    padding: 0;
}
.checklist li {
    margin-bottom: 0.5rem;
}
.checklist input {
    margin-right: 0.5rem;
}
footer {
    border-top: 1px solid #eee;
    margin-top: 4rem;
    padding-top: 1rem;
    font-size: 0.85rem;
    color: #777;
    text-align: center;
}
.status-badge {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: bold;
    text-transform: uppercase;
}
.status-generated { background-color: #d1ecf1; color: #0c5460; }
"""

HTML_SKELETON = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {css}
    </style>
</head>
<body>
    <div class="banner">
        Review surface only. Canonical source remains Markdown/JSON.
    </div>

    <header>
        <h1>{title}</h1>
        <p>{description}</p>
    </header>

    <div class="metadata">
        <dl>
            <dt>Set ID</dt><dd>{set_id}</dd>
            <dt>Source Path</dt><dd>{source_path}</dd>
            <dt>Source SHA-256</dt><dd>{source_hash}</dd>
            <dt>Generated At</dt><dd>{timestamp}</dd>
        </dl>
    </div>

    <section class="content">
        <h2>Content</h2>
        <div class="markdown-body">
            {content_html}
        </div>
    </section>

    {extra_sections}

    <section>
        <h2>Human Review Checklist</h2>
        <ul class="checklist">
            <li><input type="checkbox"> Scope matches intent</li>
            <li><input type="checkbox"> Non-goals are clear</li>
            <li><input type="checkbox"> UI/UX expectations are clear</li>
            <li><input type="checkbox"> Risks are visible</li>
            <li><input type="checkbox"> Open decisions are surfaced</li>
            <li><input type="checkbox"> Ready for next lane</li>
        </ul>
    </section>

    <footer>
        <p>This is a static projection for human review. No execution of worker prompts occurred.</p>
        <p>No branches were created, checked out, or modified. No commit, push, or merge actions were performed.</p>
    </footer>
</body>
</html>
"""

def compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")

def simple_markdown_to_html(text: str) -> str:
    """Very basic markdown conversion for structure."""
    lines = text.splitlines()
    html_lines = []
    in_list = False
    
    for line in lines:
        stripped = line.strip()
        
        # Headers
        if stripped.startswith("### "):
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<h3>{escape_html(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<h2>{escape_html(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<h1>{escape_html(stripped[2:])}</h1>")
        
        # Lists
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list: html_lines.append("<ul>"); in_list = True
            html_lines.append(f"<li>{escape_html(stripped[2:])}</li>")
        
        # Blank lines
        elif not stripped:
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append("<br>")
            
        # Paragraphs
        else:
            if in_list: html_lines.append("</ul>"); in_list = False
            html_lines.append(f"<p>{escape_html(stripped)}</p>")
            
    if in_list: html_lines.append("</ul>")
    return "\n".join(html_lines)

def detect_special_sections(text: str) -> str:
    sections = []
    text_lower = text.lower()
    
    special_keys = {
        "Risks": ["risk", "mitigation"],
        "Acceptance Criteria": ["acceptance criteria", "success criteria"],
        "Open Questions / Needs Human Decision": ["needs_human_decision", "open questions", "unresolved"],
        "Assumptions": ["assumption"]
    }
    
    # This is a very simple detector. A better one would parse headers.
    # For now, we'll just show a "Detected Highlights" section if keywords are found.
    detected = []
    for label, keywords in special_keys.items():
        if any(kw in text_lower for kw in keywords):
            detected.append(f"<li><strong>{label}</strong>: Keywords detected in source.</li>")
            
    if detected:
        return f"""
        <section>
            <h2>Detected Highlights</h2>
            <ul>
                {"".join(detected)}
            </ul>
            <p>Please review the content section above for full details on these items.</p>
        </section>
        """
    return ""

def build_review_html(manifest_path: Path, output_root: Path) -> dict[str, Any]:
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    set_id = manifest.get("set_id", "unknown")
    outputs = manifest.get("outputs", {})
    timestamp = datetime.now(timezone.utc).isoformat()
    
    lane_root = manifest_path.parent.parent
    html_dir = output_root / "html"
    manifests_dir = output_root / "manifests"
    reports_dir = output_root / "reports"
    
    for d in [html_dir, manifests_dir, reports_dir]:
        d.mkdir(parents=True, exist_ok=True)
        
    review_artifacts = {}
    
    artifact_map = {
        "product_packet": "Product Packet Review",
        "prd_brief": "PRD Brief Review",
        "wireframe_brief": "Wireframe Brief Review",
        "ui_ux_brief": "UI/UX Brief Review",
        "feature_spec": "Feature Spec Review",
        "implementation_plan": "Implementation Plan Review"
    }
    
    for key, title in artifact_map.items():
        rel_path = outputs.get(key)
        if not rel_path:
            continue
            
        source_path = lane_root / rel_path
        if not source_path.exists():
            print(f"Warning: Source artifact {rel_path} missing.")
            continue
            
        source_hash = compute_sha256(source_path)
        source_content = source_path.read_text(encoding="utf-8")
        
        content_html = simple_markdown_to_html(source_content)
        extra_sections = detect_special_sections(source_content)
        
        html_filename = f"{set_id}_{key}_review.html"
        html_path = html_dir / html_filename
        
        html_content = HTML_SKELETON.format(
            title=title,
            description=f"Human review surface for {key}.",
            css=CSS_TEMPLATE,
            set_id=set_id,
            source_path=rel_path,
            source_hash=source_hash,
            timestamp=timestamp,
            content_html=content_html,
            extra_sections=extra_sections
        )
        
        html_path.write_text(html_content, encoding="utf-8")
        review_artifacts[key] = {
            "html_path": str(html_path.resolve().relative_to(lane_root.resolve().parent)),
            "source_path": rel_path,
            "source_hash": source_hash
        }

    # Dashboard
    dashboard_filename = f"{set_id}_review_dashboard.html"
    dashboard_path = html_dir / dashboard_filename
    
    links_html = "".join([
        f'<li><a href="{Path(art["html_path"]).name}">{artifact_map[key]}</a> (Source: {art["source_path"]})</li>'
        for key, art in review_artifacts.items()
    ])
    
    dashboard_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Review Dashboard - {set_id}</title>
    <style>
        {CSS_TEMPLATE}
        .artifact-list {{ list-style: none; padding: 0; }}
        .artifact-list li {{ 
            background: #fff; border: 1px solid #ddd; margin-bottom: 1rem; padding: 1rem; border-radius: 4px;
        }}
        .artifact-list a {{ font-weight: bold; text-decoration: none; color: #007bff; }}
    </style>
</head>
<body>
    <div class="banner">Review Dashboard. Canonical source remains Markdown/JSON.</div>
    <header>
        <h1>Review Dashboard: {set_id}</h1>
        <p>Set ID: {set_id} | Generated: {timestamp}</p>
    </header>
    
    <section>
        <h2>Generated Review Surfaces</h2>
        <ul class="artifact-list">
            {links_html}
        </ul>
    </section>
    
    <section>
        <h2>Status</h2>
        <p><span class="status-badge status-generated">REVIEW_SURFACES_GENERATED</span></p>
        <p><strong>Next Step:</strong> Review the documents above. Decisions must be recorded back to the workstation using standard approval commands.</p>
    </section>

    <footer>
        <p>This dashboard does not approve or execute anything.</p>
    </footer>
</body>
</html>
"""
    dashboard_path.write_text(dashboard_content, encoding="utf-8")
    
    # Manifest
    review_manifest = {
        "set_id": set_id,
        "generated_timestamp": timestamp,
        "source_manifest": str(manifest_path.resolve().relative_to(lane_root.resolve().parent)),
        "artifacts": review_artifacts,
        "dashboard": str(dashboard_path.resolve().relative_to(lane_root.resolve().parent)),
        "status": "REVIEW_SURFACES_GENERATED"
    }
    
    manifest_file = manifests_dir / f"{set_id}_review_artifact_manifest.json"
    with manifest_file.open("w", encoding="utf-8") as f:
        json.dump(review_manifest, f, indent=2)
        
    # Report
    report_file = reports_dir / f"{set_id}_review_artifact_report.md"
    report_content = f"""# Review Artifact Generation Report: {set_id}

- Generated At: {timestamp}
- Set ID: {set_id}
- Status: PASS

## Generated Surfaces

"""
    for key, art in review_artifacts.items():
        report_content += f"- **{artifact_map[key]}**: `{art['html_path']}`\n"
        
    report_content += f"\n- **Dashboard**: `{review_manifest['dashboard']}`\n"
    report_content += "\n## Safety Check\n- No execution performed.\n- No branches created.\n- Source artifacts unmodified.\n"
    
    report_file.write_text(report_content, encoding="utf-8")
    
    return review_manifest

def main():
    parser = argparse.ArgumentParser(description="Build static HTML review surfaces.")
    parser.add_argument("--manifest", required=True, help="Path to product development manifest")
    parser.add_argument("--output", required=True, help="Path to review_artifacts root")
    
    args = parser.parse_args()
    
    manifest_path = Path(args.manifest)
    output_root = Path(args.output)
    
    if not manifest_path.exists():
        print(f"Error: Manifest {manifest_path} not found.")
        sys.exit(1)
        
    try:
        result = build_review_html(manifest_path, output_root)
        print(f"Successfully generated review artifacts for {result['set_id']}.")
        print(f"Dashboard: {result['dashboard']}")
    except Exception as e:
        print(f"Error building review HTML: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
