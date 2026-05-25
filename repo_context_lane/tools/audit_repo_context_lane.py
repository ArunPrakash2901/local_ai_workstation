import json
from pathlib import Path
from typing import Dict, List, Any, Tuple

import inventory
from inventory import RISKY_FOLDERS, RISKY_EXTENSIONS

REQUIRED_FOLDERS = [
    "project_inventories",
    "graphify_plans",
    "graph_summaries",
    "context_packets",
    "review_reports",
    "schemas",
    "tools"
]

def audit_lane(root: Path) -> Tuple[Dict[str, List[str]], Dict[str, int]]:
    errors = []
    warnings = []
    counts = {
        "folders_missing": 0,
        "inventories": 0,
        "plans": 0,
        "summaries": 0,
        "packets": 0,
        "reports": 0,
        "invalid_json": 0
    }
    
    # Check folders
    for folder in REQUIRED_FOLDERS:
        if not (root / folder).exists():
            errors.append(f"Missing required folder: {folder}")
            counts["folders_missing"] += 1
            
    # Check project_inventories
    inventory_dir = root / "project_inventories"
    if inventory_dir.exists():
        for path in inventory_dir.glob("*.json"):
            counts["inventories"] += 1
            try:
                with open(path, "r", encoding="utf-8") as f:
                    json.load(f)
            except Exception:
                errors.append(f"Invalid JSON in inventory: {path.name}")
                counts["invalid_json"] += 1
                
    # Check graphify_plans
    plan_dir = root / "graphify_plans"
    if plan_dir.exists():
        for path in plan_dir.glob("*.json"):
            counts["plans"] += 1
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Safety check: ensure no execution artifact recorded
                    if data.get("approval_status") == "APPROVED":
                        warnings.append(f"Plan is APPROVED (but lane v0.1 does not execute): {path.name}")
            except Exception:
                errors.append(f"Invalid JSON in plan: {path.name}")
                counts["invalid_json"] += 1

    # Check graph_summaries
    summary_dir = root / "graph_summaries"
    if summary_dir.exists():
        for path in summary_dir.glob("*.json"):
            counts["summaries"] += 1
            try:
                with open(path, "r", encoding="utf-8") as f:
                    json.load(f)
            except Exception:
                errors.append(f"Invalid JSON in summary: {path.name}")
                counts["invalid_json"] += 1
                
    # Check context_packets
    packet_dir = root / "context_packets"
    if packet_dir.exists():
        for path in packet_dir.glob("*.json"):
            counts["packets"] += 1
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    status = data.get("human_approval_status")
                    
                    if status == "APPROVED":
                        warnings.append(f"Packet uses deprecated 'APPROVED' status: {path.name}")
                    
                    if status == "APPROVED_FOR_CONTEXT_USE":
                        if not data.get("approved_at"):
                            errors.append(f"Approved packet missing 'approved_at': {path.name}")
                        if data.get("approval_scope") != "CONTEXT_ONLY":
                            errors.append(f"Approved packet missing or invalid 'approval_scope': {path.name}")
                            
                        # Check if source artifacts still exist
                        artifacts = data.get("source_artifacts", {})
                        for art_type, art_path in artifacts.items():
                            if art_path and not Path(art_path).exists():
                                errors.append(f"Approved packet source {art_type} missing: {path.name}")
                                
                    elif status not in ["NOT_APPROVED", "APPROVED_FOR_CONTEXT_USE"]:
                        warnings.append(f"Packet has unknown status '{status}': {path.name}")

                    # Deep candidate check
                    candidates = data.get("candidates", [])
                    for cand in candidates:
                        c_path = cand.get("path", "")
                        cp = Path(c_path)
                        for part in cp.parts:
                            if part in RISKY_FOLDERS:
                                errors.append(f"Packet contains risky folder '{part}' in candidates: {path.name}")
                        if cp.suffix.lower() in RISKY_EXTENSIONS:
                            errors.append(f"Packet contains risky extension '{cp.suffix}' in candidates: {path.name}")

            except Exception as e:
                errors.append(f"Invalid JSON in packet: {path.name} ({e})")
                counts["invalid_json"] += 1

    # Check review_reports
    report_dir = root / "review_reports"
    if report_dir.exists():
        for path in report_dir.glob("*.md"):
            counts["reports"] += 1

    return {"errors": errors, "warnings": warnings}, counts

def render_audit(root: Path, audit: Dict[str, List[str]], counts: Dict[str, int]) -> str:
    lines = [f"# Repo Context Lane Audit: {root}\n"]
    
    lines.append("## Counts")
    for key, value in counts.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    
    if audit["errors"]:
        lines.append("## Errors")
        for err in audit["errors"]:
            lines.append(f"- [!] {err}")
        lines.append("")
        
    if audit["warnings"]:
        lines.append("## Warnings")
        for warn in audit["warnings"]:
            lines.append(f"- [?] {warn}")
        lines.append("")
        
    if not audit["errors"] and not audit["warnings"]:
        lines.append("## Status: PASS")
    elif not audit["errors"]:
        lines.append("## Status: PASS (with warnings)")
    else:
        lines.append("## Status: FAIL")
        
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    r = Path("repo_context_lane")
    a, c = audit_lane(r)
    print(render_audit(r, a, c))
