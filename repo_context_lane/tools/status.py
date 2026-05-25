import json
import datetime
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

def discover_projects(output_root: Path, target_project_id: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
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
                        # Fallback to filename parsing if possible
                        # e.g. project_id_inventory.json -> project_id
                        if "_inventory" in path.stem:
                            pid = path.stem.replace("_inventory", "")
                        elif "_plan" in path.stem:
                            pid = path.stem.replace("_plan", "")
                        elif "_intake" in path.stem:
                            pid = path.stem.replace("_intake", "")
                        elif "_summary" in path.stem:
                            pid = path.stem.replace("_summary", "")
                        else:
                            pid = path.stem.split("_")[0]
                    
                    if target_project_id and pid != target_project_id:
                        continue
                        
                    if pid not in projects:
                        projects[pid] = {
                            "project_id": pid,
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
                        # Keep latest run based on started_at
                        if not projects[pid]["run"] or data.get("started_at", "") > projects[pid]["run"].get("started_at", ""):
                            projects[pid]["run"] = data
                    else:
                        projects[pid][key] = data
            except Exception as e:
                # Malformed artifact warning
                # Try to find which project this might belong to from filename
                pid_guess = path.stem.split("_")[0]
                if target_project_id and pid_guess != target_project_id:
                    continue
                if pid_guess not in projects:
                    projects[pid_guess] = {
                        "project_id": pid_guess,
                        "inventory": None, "plan": None, "run": None, "intake": None, "summary": None,
                        "packets": [], "handoffs": [], "warnings": []
                    }
                projects[pid_guess]["warnings"].append(f"Malformed artifact {path.name}: {e}")

    return projects

def get_recommendation(pid: str, data: Dict[str, Any]) -> str:
    if not data["inventory"]:
        return f"ws repo-context inventory --project <path_to_{pid}>"
        
    if not data["plan"]:
        return f"ws repo-context graphify-plan --project <path_to_{pid}>"
        
    p_status = data["plan"].get("approval_status")
    if p_status != "APPROVED_FOR_GRAPHIFY_EXECUTION":
        plan_path = data["plan"].get("path") or f"repo_context_lane/graphify_plans/{pid}_plan.json"
        return f"ws repo-context graphify-plan-review --plan {plan_path} OR ws repo-context graphify-plan-approve --plan {plan_path} --confirm"
        
    if not data["run"]:
        plan_path = f"repo_context_lane/graphify_plans/{pid}_plan.json"
        return f"ws repo-context graphify-run --plan {plan_path} --confirm"
        
    r_status = data["run"].get("execution_status")
    if r_status != "SUCCEEDED":
        return f"Fix issue and re-run: ws repo-context graphify-run --plan repo_context_lane/graphify_plans/{pid}_plan.json --confirm"
        
    if not data["intake"]:
        # Find the latest run path
        run_path = f"repo_context_lane/graphify_runs/{pid}_run.json" # Best guess
        return f"ws repo-context graphify-intake --run {run_path}"
        
    if not data["summary"]:
        # Intake should have generated it, but if missing:
        graph_path = data["intake"].get("graph_path", f"graphify-results/{pid}/graphify-out/graph.json")
        return f"ws repo-context summarize --graph {graph_path}"
        
    if not data["packets"]:
        return f"ws repo-context packet --project {pid} --task <task_name>"
        
    # Check if any packet is approved
    approved_packets = [p for p in data["packets"] if p.get("human_approval_status") == "APPROVED_FOR_CONTEXT_USE"]
    if not approved_packets:
        return f"ws repo-context packet-review --packet <packet_path> OR ws repo-context packet-approve --packet <packet_path> --confirm"
        
    # Find approved packets that don't have handoffs yet
    handoff_packets = [h.get("source_packet") for h in data["handoffs"]]
    pending_handoffs = []
    for p in data["packets"]:
        if p.get("human_approval_status") == "APPROVED_FOR_CONTEXT_USE":
            # We don't always have full path in data, but we can try to find it
            # For simplicity, if we have handoffs, we might be ready
            pass

    if not data["handoffs"]:
        # Recommend handoff for the first approved packet
        packet_name = "latest_packet.json"
        return f"ws repo-context handoff --packet <path_to_approved_packet> --target gemini"
        
    return "READY_FOR_OPERATOR_USE (HANDOFF_READY)"

def render_status(projects: Dict[str, Dict[str, Any]]) -> str:
    if not projects:
        return "No Repo Context Lane projects discovered."
        
    lines = ["# Repo Context Lane: Pipeline Status\n"]
    
    for pid in sorted(projects.keys()):
        data = projects[pid]
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
            if data["run"].get("started_at"):
                run += f" (Started: {data['run']['started_at']})"
        lines.append(f"- Latest Run: {run}")
        
        intake = "MISSING"
        if data["intake"]:
            intake = data["intake"].get("intake_status", "EXISTS")
        lines.append(f"- Intake: {intake}")
        
        summ = "MISSING" if not data["summary"] else "READY"
        lines.append(f"- Graph Summary: {summ}")
        
        p_count = len(data["packets"])
        p_approved = len([p for p in data["packets"] if p.get("human_approval_status") == "APPROVED_FOR_CONTEXT_USE"])
        lines.append(f"- Context Packets: {p_count} ({p_approved} approved)")
        
        h_count = len(data["handoffs"])
        # Group handoffs by target if possible
        targets = {}
        for h in data["handoffs"]:
            target = h.get("target", "unknown")
            targets[target] = targets.get(target, 0) + 1
        
        h_str = f"{h_count}"
        if targets:
            h_str += " (" + ", ".join([f"{t}: {c}" for t, c in targets.items()]) + ")"
        lines.append(f"- Handoffs: {h_str}")
        
        if data["warnings"]:
            lines.append("- **Warnings**:")
            for w in data["warnings"]:
                lines.append(f"  - [!] {w}")
        
        lines.append(f"- **Next Recommended Command**: {get_recommendation(pid, data)}")
        lines.append("")
        
    return "\n".join(lines)

def generate_freeze_report(output_root: Path, projects: Dict[str, Dict[str, Any]]) -> str:
    timestamp = datetime.datetime.now().isoformat()
    lines = [f"# Repo Context Lane Freeze Report\n"]
    lines.append(f"- **Generated At**: {timestamp}")
    
    # Lane Commands Summary (v0.1 - v0.8)
    lines.append("\n## Lane Command Surface & Safety")
    lines.append("| Command | Safety Class | Purpose |")
    lines.append("| :--- | :--- | :--- |")
    lines.append("| `inventory` | LOCAL_REPORT_WRITE | Map project structure |")
    lines.append("| `graphify-plan` | LOCAL_REPORT_WRITE | Propose Graphify scope |")
    lines.append("| `graphify-plan-approve` | GUARDED_WRITE | Approve Graphify scope |")
    lines.append("| `graphify-run` | GUARDED_EXECUTION | Execute Graphify |")
    lines.append("| `graphify-intake` | LOCAL_REPORT_WRITE | Process Graphify results |")
    lines.append("| `summarize` | LOCAL_REPORT_WRITE | Generate graph summaries |")
    lines.append("| `packet` | LOCAL_REPORT_WRITE | Create task context |")
    lines.append("| `packet-approve` | GUARDED_WRITE | Approve task context |")
    lines.append("| `handoff` | LOCAL_REPORT_WRITE | Export for downstream agents |")
    lines.append("| `status` | PURE_READ | Pipeline visibility |")
    lines.append("| `freeze-report` | LOCAL_REPORT_WRITE | Readiness assessment |")
    lines.append("| `audit` | PURE_READ | Integrity check |")
    
    lines.append("\n## Artifact Directories")
    artifact_dirs = [
        "project_inventories", "graphify_plans", "graphify_runs", 
        "graphify_intake_reports", "graph_summaries", "context_packets", 
        "review_reports", "handoffs", "handoff_manifests"
    ]
    for d in artifact_dirs:
        exists = "EXISTS" if (output_root / d).exists() else "MISSING"
        lines.append(f"- `{d}/`: {exists}")
    
    lines.append("\n## Current Project States")
    malformed_found = False
    for pid in sorted(projects.keys()):
        data = projects[pid]
        lines.append(f"### Project: {pid}")
        lines.append(f"- Inventory: {'PASS' if data['inventory'] else 'FAIL'}")
        
        plan_status = data['plan'].get('approval_status') if data['plan'] else 'MISSING'
        lines.append(f"- Plan Approval: {plan_status}")
        
        run_status = data['run'].get('execution_status') if data['run'] else 'NOT_RUN'
        lines.append(f"- Latest Run: {run_status}")
        
        lines.append(f"- Summary: {'READY' if data['summary'] else 'MISSING'}")
        
        p_approved = len([p for p in data['packets'] if p.get('human_approval_status') == 'APPROVED_FOR_CONTEXT_USE'])
        lines.append(f"- Packets Approved: {p_approved}")
        
        if data["warnings"]:
            malformed_found = True
            lines.append("- Warnings:")
            for w in data["warnings"]:
                lines.append(f"  - [!] {w}")
    
    lines.append("\n## Readiness Assessment")
    
    # Audit check would be good here, but we don't want to depend on audit_repo_context_lane circularly if possible
    # or we just call it
    from . import audit_repo_context_lane
    audit, counts = audit_repo_context_lane.audit_lane(output_root)
    
    if audit["errors"]:
        lines.append(f"- **Audit Status**: FAIL ({len(audit['errors'])} errors)")
        for e in audit["errors"]:
            lines.append(f"  - [!] {e}")
    else:
        lines.append(f"- **Audit Status**: PASS ({len(audit['warnings'])} warnings)")
        
    is_ready = not audit["errors"] and not malformed_found and projects
    
    if is_ready:
        lines.append("\n**FINAL STATE**: FREEZE_CANDIDATE")
    else:
        lines.append("\n**FINAL STATE**: IN_PROGRESS (Fix errors/warnings before freeze)")
        
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
