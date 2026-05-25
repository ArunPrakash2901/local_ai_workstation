import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

def generate_packet(project_id: str, task_name: str, output_root: Path, dry_run: bool = True) -> Dict[str, Any]:
    inventory_path = output_root / "project_inventories" / f"{project_id}_inventory.json"
    summary_path = output_root / "graph_summaries" / f"{project_id}_summary.json"
    
    inventory_data = {}
    if inventory_path.exists():
        try:
            with open(inventory_path, "r", encoding="utf-8") as f:
                inventory_data = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load inventory for {project_id}: {e}")
            
    summary_data = {}
    if summary_path.exists():
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                summary_data = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load graph summary for {project_id}: {e}")

    # Candidate selection
    candidates = []
    
    # Use suggested entrypoints from graph summary
    entrypoints = summary_data.get("suggested_entrypoints", [])
    for ep in entrypoints:
        candidates.append({
            "path": ep,
            "reason": "Suggested entrypoint from graph summary"
        })
        
    # Use high-degree nodes from graph summary
    high_degree = summary_data.get("high_degree_nodes", [])
    for node in high_degree:
        node_id = node.get("id")
        # Avoid duplicates
        if node_id and not any(c["path"] == node_id for c in candidates):
            candidates.append({
                "path": node_id,
                "reason": f"High-degree node (degree: {node.get('degree')})"
            })
            
    # Exclusions from inventory
    stats = inventory_data.get("stats", {})
    excluded_risky = stats.get("risky_folders_found", [])
    excluded_heavy = [h.get("path") for h in stats.get("heavyweight_files", [])]
    
    confidence = "HIGH"
    uncertainty = []
    
    if not summary_data:
        confidence = "LOW"
        uncertainty.append("No graph summary found for project.")
        
    if not inventory_data:
        confidence = "LOW"
        uncertainty.append("No project inventory found for project.")
        
    if not candidates:
        confidence = "LOW"
        uncertainty.append("No candidate files could be identified from existing artifacts.")

    packet = {
        "project_id": project_id,
        "task_name": task_name,
        "created_at": datetime.datetime.now().isoformat(),
        "human_approval_status": "NOT_APPROVED",
        "confidence": confidence,
        "source_artifacts": {
            "inventory": str(inventory_path) if inventory_path.exists() else None,
            "graph_summary": str(summary_path) if summary_path.exists() else None
        },
        "candidates": candidates,
        "exclusions": {
            "risky_folders": excluded_risky,
            "heavyweight_files": excluded_heavy
        },
        "uncertainty": uncertainty,
        "suggested_prompt_context": f"Focus on {task_name} in project {project_id}. " + 
                                   (f"Key entrypoints: {', '.join(entrypoints[:3])}." if entrypoints else ""),
        "context_budget_estimate": "Unknown (v0.2 dry-run does not count tokens)",
        "safety_notes": [
            "Dry-run packet generation only.",
            "No source file contents were inspected.",
            "Human review required before using this packet for downstream tasks."
        ]
    }
    
    if not dry_run:
        packet_dir = output_root / "context_packets"
        review_dir = output_root / "review_reports"
        packet_dir.mkdir(parents=True, exist_ok=True)
        review_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        packet_id = f"{project_id}_{task_name}_{timestamp_str}"
        
        json_path = packet_dir / f"{packet_id}.json"
        md_path = packet_dir / f"{packet_id}.md"
        report_path = review_dir / f"{packet_id}_review.md"
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(packet, f, indent=2)
            
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Context Packet: {task_name} ({project_id})\n\n")
            f.write(f"- **Created At**: {packet['created_at']}\n")
            f.write(f"- **Confidence**: {packet['confidence']}\n")
            f.write(f"- **Approval Status**: `{packet['human_approval_status']}`\n\n")
            
            f.write("## Candidate Files/Modules\n")
            if candidates:
                for c in candidates:
                    f.write(f"- `{c['path']}`: {c['reason']}\n")
            else:
                f.write("_No candidates identified._\n")
            f.write("\n")
            
            f.write("## Exclusions\n")
            if excluded_risky:
                f.write("### Risky Folders (Skipped)\n")
                for r in excluded_risky[:10]:
                    f.write(f"- `{r}`\n")
                if len(excluded_risky) > 10:
                    f.write(f"- ... and {len(excluded_risky) - 10} more\n")
                f.write("\n")
                
            if excluded_heavy:
                f.write("### Heavyweight Files (>10MB)\n")
                for h in excluded_heavy[:10]:
                    f.write(f"- `{h}`\n")
                if len(excluded_heavy) > 10:
                    f.write(f"- ... and {len(excluded_heavy) - 10} more\n")
                f.write("\n")
                
            if uncertainty:
                f.write("## Uncertainty / Warnings\n")
                for u in uncertainty:
                    f.write(f"- [!] {u}\n")
                f.write("\n")
                
            f.write("## Suggested Prompt Context\n")
            f.write(f"{packet['suggested_prompt_context']}\n\n")
            
            f.write("## Safety Notes\n")
            for note in packet["safety_notes"]:
                f.write(f"- {note}\n")
                
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Review Report: Context Packet {packet_id}\n\n")
            f.write("## Summary\n")
            f.write(f"- **Project**: {project_id}\n")
            f.write(f"- **Task**: {task_name}\n")
            f.write(f"- **Packet MD**: `context_packets/{packet_id}.md`\n")
            f.write(f"- **Packet JSON**: `context_packets/{packet_id}.json`\n")
            f.write(f"- **Status**: {packet['human_approval_status']}\n\n")
            f.write("## Review Checklist\n")
            f.write("- [ ] Candidates are relevant to the task.\n")
            f.write("- [ ] No sensitive or private files are listed in candidates.\n")
            f.write("- [ ] Context budget seems reasonable.\n")
            f.write("- [ ] Exclusions look correct.\n\n")
            f.write("## Approval\n")
            f.write("To approve, manually update the `human_approval_status` to `APPROVED` in the packet JSON and this report.\n")

    return packet

if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--output", default="repo_context_lane")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    
    res = generate_packet(args.project, args.task, Path(args.output), dry_run=not args.confirm)
    if not args.confirm:
        print(json.dumps(res, indent=2))
