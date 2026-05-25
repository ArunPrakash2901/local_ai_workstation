import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

def discover_projects(output_root: Path) -> Dict[str, Dict[str, Any]]:
    projects = {}
    
    # Folders to scan
    SCAN_CONFIG = [
        ("project_inventories", "*_inventory.json", "inventory"),
        ("graphify_plans", "*_plan.json", "plan"),
        ("graphify_runs", "*.json", "run"),
        ("graphify_intake_reports", "*_intake.json", "intake"),
        ("graph_summaries", "*_summary.json", "summary"),
        ("context_packets", "*.json", "packets"),
        ("handoff_manifests", "*.json", "handoffs")
    ]
    
    for folder, pattern, key in SCAN_CONFIG:
        dir_path = output_root / folder
        if not dir_path.exists():
            continue
            
        for path in dir_path.glob(pattern):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    pid = data.get("project_id")
                    if not pid:
                        # Fallback to filename parsing
                        pid = path.stem.split("_")[0]
                        
                    if pid not in projects:
                        projects[pid] = {
                            "inventory": None,
                            "plan": None,
                            "run": None,
                            "intake": None,
                            "summary": None,
                            "packets": [],
                            "handoffs": [],
                            "warnings": []
                        }
                    
                    if key in ["packets", "handoffs"]:
                        projects[pid][key].append(data)
                    elif key == "run":
                        # Keep latest run
                        if not projects[pid]["run"] or data.get("started_at", "") > projects[pid]["run"].get("started_at", ""):
                            projects[pid]["run"] = data
                    else:
                        projects[pid][key] = data
            except Exception as e:
                # We don't have project_id yet if we fail to read, so we can't easily attribute warning
                # but we can log it
                pass

    return projects

def get_recommendation(pid: str, data: Dict[str, Any]) -> str:
    if not data["inventory"]:
        return f"ws repo-context inventory --project <path_to_{pid}>"
        
    if not data["plan"]:
        return f"ws repo-context graphify-plan --project <path_to_{pid}>"
        
    p_status = data["plan"].get("approval_status")
    if p_status != "APPROVED_FOR_GRAPHIFY_EXECUTION":
        return f"ws repo-context graphify-plan-approve --plan {data['plan'].get('path') or '...'}"
        
    if not data["run"]:
        return f"ws repo-context graphify-run --plan <plan_path> --confirm"
        
    r_status = data["run"].get("execution_status")
    if r_status != "SUCCEEDED":
        return f"Fix issue and re-run: ws repo-context graphify-run"
        
    if not data["intake"]:
        return f"ws repo-context graphify-intake --run <run_path>"
        
    if not data["summary"]:
        # Intake should have generated it, but if missing:
        return f"ws repo-context summarize --graph <graph_path>"
        
    if not data["packets"]:
        return f"ws repo-context packet --project {pid} --task <task_name>"
        
    # Check if any packet is approved
    approved_packets = [p for p in data["packets"] if p.get("human_approval_status") == "APPROVED_FOR_CONTEXT_USE"]
    if not approved_packets:
        return f"ws repo-context packet-approve --packet <packet_path> --confirm"
        
    if not data["handoffs"]:
        return f"ws repo-context handoff --packet <approved_packet_path> --target gemini"
        
    return "READY_FOR_OPERATOR_USE (HANDOFF_READY)"

def render_status(projects: Dict[str, Dict[str, Any]]) -> str:
    if not projects:
        return "No Repo Context Lane projects discovered."
        
    lines = ["# Repo Context Lane: Pipeline Status\n"]
    
    for pid, data in projects.items():
        lines.append(f"## Project: {pid}")
        
        inv = "EXISTS" if data["inventory"] else "MISSING"
        lines.append(f"- Inventory: {inv}")
        
        plan = "MISSING"
        if data["plan"]:
            plan = data["plan"].get("approval_status", "EXISTS")
        lines.append(f"- Graphify Plan: {plan}")
        
        run = "NOT_RUN"
        if data["run"]:
            run = data["run"].get("execution_status", "EXISTS")
        lines.append(f"- Latest Run: {run}")
        
        intake = "MISSING"
        if data["intake"]:
            intake = data.get("intake", {}).get("intake_status", "EXISTS")
        lines.append(f"- Intake: {intake}")
        
        summ = "MISSING" if not data["summary"] else "READY"
        lines.append(f"- Graph Summary: {summ}")
        
        p_count = len(data["packets"])
        p_approved = len([p for p in data["packets"] if p.get("human_approval_status") == "APPROVED_FOR_CONTEXT_USE"])
        lines.append(f"- Context Packets: {p_count} ({p_approved} approved)")
        
        h_count = len(data["handoffs"])
        lines.append(f"- Handoffs: {h_count}")
        
        lines.append(f"- **Next Step**: {get_recommendation(pid, data)}")
        lines.append("")
        
    return "\n".join(lines)

def generate_freeze_report(output_root: Path, projects: Dict[str, Dict[str, Any]]) -> str:
    timestamp = datetime.datetime.now().isoformat()
    lines = [f"# Repo Context Lane Freeze Report\n"]
    lines.append(f"- **Generated At**: {timestamp}")
    
    # Safety Classes (Hardcoded based on registry knowledge)
    lines.append("\n## Lane Command Safety Policy")
    lines.append("- `inventory`: PURE_READ / LOCAL_REPORT_WRITE")
    lines.append("- `graphify-plan`: LOCAL_REPORT_WRITE")
    lines.append("- `graphify-plan-approve`: GUARDED_WRITE")
    lines.append("- `graphify-run`: GUARDED_EXECUTION")
    lines.append("- `graphify-intake`: LOCAL_REPORT_WRITE")
    lines.append("- `summarize`: PURE_READ / LOCAL_REPORT_WRITE")
    lines.append("- `packet`: LOCAL_REPORT_WRITE")
    lines.append("- `packet-approve`: GUARDED_WRITE")
    lines.append("- `handoff`: LOCAL_REPORT_WRITE")
    lines.append("- `status`: PURE_READ")
    
    lines.append("\n## Artifact Summary")
    for pid, data in projects.items():
        lines.append(f"### Project: {pid}")
        lines.append(f"- Inventory: {'PASS' if data['inventory'] else 'FAIL'}")
        lines.append(f"- Plan: {data['plan'].get('approval_status') if data['plan'] else 'MISSING'}")
        lines.append(f"- Run: {data['run'].get('execution_status') if data['run'] else 'NOT_RUN'}")
        lines.append(f"- Summary: {'READY' if data['summary'] else 'MISSING'}")
        lines.append(f"- Packets Approved: {len([p for p in data['packets'] if p.get('human_approval_status') == 'APPROVED_FOR_CONTEXT_USE'])}")
    
    lines.append("\n## Readiness Status")
    all_ready = all(data["summary"] for data in projects.values()) if projects else False
    if all_ready:
        lines.append("**STATUS**: FREEZE_CANDIDATE")
    else:
        lines.append("**STATUS**: IN_PROGRESS (Pipeline incomplete)")
        
    report_content = "\n".join(lines)
    
    report_dir = output_root / "review_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"freeze_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    return str(report_path)

if __name__ == "__main__":
    import sys
    r = Path("repo_context_lane")
    p = discover_projects(r)
    print(render_status(p))
