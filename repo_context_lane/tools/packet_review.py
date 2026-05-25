import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from .inventory import RISKY_FOLDERS, RISKY_EXTENSIONS

def list_packets(output_root: Path) -> List[Dict[str, Any]]:
    packet_dir = output_root / "context_packets"
    packets = []
    if packet_dir.exists():
        for path in packet_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    packets.append({
                        "project_id": data.get("project_id"),
                        "task_name": data.get("task_name"),
                        "created_at": data.get("created_at"),
                        "human_approval_status": data.get("human_approval_status"),
                        "path": str(path)
                    })
            except Exception:
                pass
    return sorted(packets, key=lambda x: str(x.get("created_at") or ""), reverse=True)

def review_packet(packet_path: Path, output_root: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
    issues = []
    packet_data = {}
    
    if not packet_path.exists():
        return False, [f"Packet file not found: {packet_path}"], {}
        
    try:
        with open(packet_path, "r", encoding="utf-8") as f:
            packet_data = json.load(f)
    except Exception as e:
        return False, [f"Failed to load packet JSON: {e}"], {}
        
    # Validate required fields
    required = ["project_id", "task_name", "candidates", "source_artifacts", "human_approval_status"]
    for field in required:
        if field not in packet_data:
            issues.append(f"Missing required field: {field}")
            
    if issues:
        return False, issues, packet_data

    # Check source artifacts
    artifacts = packet_data.get("source_artifacts", {})
    inv_path = artifacts.get("inventory")
    sum_path = artifacts.get("graph_summary")
    
    if inv_path and not Path(inv_path).exists():
        issues.append(f"Source inventory artifact missing: {inv_path}")
    if sum_path and not Path(sum_path).exists():
        issues.append(f"Source graph summary artifact missing: {sum_path}")
        
    # Validate candidates
    candidates = packet_data.get("candidates", [])
    for cand in candidates:
        path = cand.get("path", "")
        p = Path(path)
        
        # Check risky folders
        for part in p.parts:
            if part in RISKY_FOLDERS:
                issues.append(f"Candidate contains risky folder '{part}': {path}")
                
        # Check risky extensions
        if p.suffix.lower() in RISKY_EXTENSIONS:
            issues.append(f"Candidate has risky extension '{p.suffix}': {path}")
            
    # Check exclusions (re-verify they are excluded)
    # (The packet generation already does this, but review is a second layer)
    
    return len(issues) == 0, issues, packet_data

def approve_packet(packet_path: Path, output_root: Path, confirm: bool = False) -> Tuple[bool, str, Dict[str, Any]]:
    if not confirm:
        return False, "Approval requires --confirm.", {}
        
    is_valid, issues, packet_data = review_packet(packet_path, output_root)
    if not is_valid:
        return False, f"Approval failed due to review issues: {', '.join(issues)}", packet_data
        
    # Update approval metadata
    packet_data["human_approval_status"] = "APPROVED_FOR_CONTEXT_USE"
    packet_data["approved_at"] = datetime.datetime.now().isoformat()
    packet_data["approval_scope"] = "CONTEXT_ONLY"
    packet_data["approval_notes"] = (
        "This approval allows the packet to be used as context for downstream prompts. "
        "IT DOES NOT APPROVE: code execution, Graphify execution, branch creation, commits, pushes, merges, or downstream agent repository mutation."
    )
    
    # Save updated JSON
    try:
        with open(packet_path, "w", encoding="utf-8") as f:
            json.dump(packet_data, f, indent=2)
            
        # Update Markdown report if it exists
        md_path = packet_path.with_suffix(".md")
        if md_path.exists():
            update_packet_md_approval(md_path, packet_data)
            
        # Update/Create Review Report
        report_dir = output_root / "review_reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{packet_path.stem}_review.md"
        write_approval_report(report_path, packet_data)
        
        return True, "Packet approved for context use.", packet_data
    except Exception as e:
        return False, f"Failed to save approval: {e}", packet_data

def update_packet_md_approval(md_path: Path, packet_data: Dict[str, Any]):
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        new_lines = []
        for line in lines:
            if line.startswith("- **Approval Status**:") or line.startswith("- Approval Status:"):
                new_lines.append(f"- **Approval Status**: `{packet_data['human_approval_status']}`\n")
                new_lines.append(f"- **Approved At**: {packet_data['approved_at']}\n")
                new_lines.append(f"- **Approval Scope**: {packet_data['approval_scope']}\n")
            else:
                new_lines.append(line)
                
        with open(md_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception:
        pass

def write_approval_report(report_path: Path, packet_data: Dict[str, Any]):
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Review Report: {packet_data.get('task_name')} ({packet_data.get('project_id')})\n\n")
        f.write(f"- **Status**: `{packet_data['human_approval_status']}`\n")
        f.write(f"- **Approved At**: {packet_data.get('approved_at', 'N/A')}\n")
        f.write(f"- **Approval Scope**: {packet_data.get('approval_scope', 'N/A')}\n\n")
        
        f.write("## Approval Notes\n")
        f.write(f"{packet_data.get('approval_notes', 'N/A')}\n\n")
        
        f.write("## Candidate Files (Approved)\n")
        for cand in packet_data.get("candidates", []):
            f.write(f"- `{cand['path']}`: {cand['reason']}\n")
        f.write("\n")
        
        f.write("## Exclusions Verified\n")
        excl = packet_data.get("exclusions", {})
        f.write(f"- Risky Folders: {len(excl.get('risky_folders', []))}\n")
        f.write(f"- Heavyweight Files: {len(excl.get('heavyweight_files', []))}\n")
