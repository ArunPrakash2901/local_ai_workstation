#!/usr/bin/env python3
"""Deterministic, metadata-only knowledge inventory helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

ALLOWED_TARGETS = {"matfinog_youtube"}


def knowledge_root(root: str | Path) -> Path:
    return Path(root) / "knowledge"


def target_root(root: str | Path, target: str) -> Path:
    if target not in ALLOWED_TARGETS:
        raise ValueError(f"Target {target!r} not allowed.")
    if ".." in target or "/" in target or "\\" in target:
        raise ValueError(f"Target {target!r} contains path traversal characters.")
    return knowledge_root(root) / target


def raw_root(root: str | Path, target: str) -> Path:
    return target_root(root, target) / "raw"


def validate_knowledge_target(target: str) -> bool:
    return target in ALLOWED_TARGETS


def collect_inventory(root: str | Path, target: str) -> Dict[str, Any]:
    raw_dir = raw_root(root, target)
    if not raw_dir.is_dir():
        return {
            "target": target,
            "raw_path": str(raw_dir),
            "exists": False,
            "files": [],
            "directories": [],
        }

    files: List[Path] = []
    directories: List[Path] = []

    for item in raw_dir.rglob("*"):
        if item.is_file():
            files.append(item)
        elif item.is_dir():
            directories.append(item)

    return {
        "target": target,
        "raw_path": str(raw_dir),
        "exists": True,
        "files": files,
        "directories": directories,
    }


def group_files_by_extension(files: List[Path]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for f in files:
        name = f.name.lower()
        if name.endswith(".info.json"):
            ext = ".info.json"
        else:
            ext = f.suffix.lower() or "(no extension)"
        counts[ext] = counts.get(ext, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))


def compute_size_summary(files: List[Path]) -> Dict[str, Any]:
    total_bytes = sum(f.stat().st_size for f in files)
    
    # Get largest 10 files
    sorted_files = sorted(files, key=lambda x: x.stat().st_size, reverse=True)
    largest = []
    for f in sorted_files[:10]:
        largest.append({
            "path": str(f),
            "size_bytes": f.stat().st_size
        })

    return {
        "total_bytes": total_bytes,
        "total_mb": total_bytes / (1024 * 1024),
        "largest_files": largest,
    }


def detect_git_tracking_status(root: str | Path, files: List[Path]) -> Dict[str, Any]:
    # Placeholder for safe git check. For now, we report as 'untracked' or 'unknown'
    # without running real git commands in the helper to keep it side-effect free.
    # A real implementation would use subprocess.run(['git', 'ls-files', '--error-unmatch', ...])
    return {"status": "unknown", "count": len(files)}


def render_inventory_report(inventory: Dict[str, Any]) -> str:
    target = inventory["target"]
    raw_path = inventory["raw_path"]
    
    if not inventory["exists"]:
        return f"# Knowledge Inventory Dry Run: {target}\n\nRaw directory not found: {raw_path}\n"

    files = inventory["files"]
    dirs = inventory["directories"]
    
    ext_summary = group_files_by_extension(files)
    size_summary = compute_size_summary(files)
    
    lines = [
        f"# Knowledge Inventory Dry Run: {target}",
        "",
        "DRY RUN - no files written.",
        "No raw content parsed.",
        "No metadata files modified.",
        "",
        f"- **Target:** {target}",
        f"- **Raw Path:** `{raw_path}`",
        f"- **Total File Count:** {len(files)}",
        f"- **Total Directory Count:** {len(dirs)}",
        f"- **Total Size:** {size_summary['total_mb']:.2f} MB ({size_summary['total_bytes']:,} bytes)",
        "",
        "## Extension Summary",
        "",
    ]
    
    for ext, count in ext_summary.items():
        lines.append(f"- **{ext}:** {count} files")
        
    lines.extend([
        "",
        "## Largest Files",
        "",
    ])
    
    for f in size_summary["largest_files"]:
        rel_path = os.path.relpath(f["path"], raw_path)
        size_mb = f["size_bytes"] / (1024 * 1024)
        lines.append(f"- `{rel_path}` ({size_mb:.2f} MB)")
        
    lines.extend([
        "",
        "## Policy Recommendation Summary",
        "",
        "- Maintain `.vtt` transcripts in raw storage for auditability.",
        "- Maintain `.info.json` metadata for provenance.",
        "- Do not commit large binary blobs if detected (none shown in extension summary if typical).",
        "- Prepare for future `inventory.json` generation.",
        "",
        "## Next Step",
        "",
        f"- future `ws knowledge-inventory --target {target} --confirm` (not implemented)",
    ])
    
    return "\n".join(lines)
