import json
import datetime
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

def list_plans(output_root: Path) -> List[Dict[str, Any]]:
    plan_dir = output_root / "graphify_plans"
    plans = []
    if plan_dir.exists():
        for path in plan_dir.glob("*_plan.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    plans.append({
                        "project_id": data.get("project_id"),
                        "project_path": data.get("project_path"),
                        "proposed_output_path": data.get("proposed_output_path"),
                        "approval_status": data.get("approval_status"),
                        "path": str(path)
                    })
            except Exception:
                pass
    return sorted(plans, key=lambda x: x.get("project_id", ""))

def review_plan(plan_path: Path, output_root: Path) -> Tuple[bool, List[str], Dict[str, Any]]:
    issues = []
    plan_data = {}
    
    if not plan_path.exists():
        return False, [f"Plan file not found: {plan_path}"], {}
        
    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            plan_data = json.load(f)
    except Exception as e:
        return False, [f"Failed to load plan JSON: {e}"], {}
        
    # Validate required fields
    required = ["project_id", "project_path", "proposed_output_path", "graphify_exe", "proposed_command", "approval_status"]
    for field in required:
        if field not in plan_data:
            issues.append(f"Missing required field: {field}")
            
    if issues:
        return False, issues, plan_data

    # Validate project path
    project_path = Path(plan_data["project_path"]).resolve()
    if not project_path.exists():
        issues.append(f"Project path does not exist: {project_path}")
    
    # Reject unsafe scopes
    if project_path.parent == project_path: # Drive root
        issues.append(f"Unsafe project scope: Drive root '{project_path}'")
    
    # Broad parent folders (e.g. C:\Users, D:\)
    # Check if it's too high in the tree
    if len(project_path.parts) <= 2:
        issues.append(f"Unsafe project scope: Too broad '{project_path}'")
        
    # Validate output path
    output_path = Path(plan_data["proposed_output_path"]).resolve()
    if str(output_path).startswith(str(project_path)):
        issues.append(f"Output path is inside project root: {output_path}")
        
    # Verify Graphify executable
    expected_exe = r"C:\Users\abi62\AppData\Roaming\Python\Python313\Scripts\graphify.exe"
    if plan_data["graphify_exe"] != expected_exe:
        issues.append(f"Unexpected Graphify executable path: {plan_data['graphify_exe']}")

    return len(issues) == 0, issues, plan_data

def approve_plan(plan_path: Path, output_root: Path, confirm: bool = False) -> Tuple[bool, str, Dict[str, Any]]:
    if not confirm:
        return False, "Approval requires --confirm.", {}
        
    is_valid, issues, plan_data = review_plan(plan_path, output_root)
    if not is_valid:
        return False, f"Approval failed due to review issues: {', '.join(issues)}", plan_data
        
    # Update approval metadata
    plan_data["approval_status"] = "APPROVED_FOR_GRAPHIFY_EXECUTION"
    plan_data["approved_at"] = datetime.datetime.now().isoformat()
    plan_data["approval_scope"] = "GRAPHIFY_RUN_ONLY"
    plan_data["approval_notes"] = (
        "This approval allows the Graphify execution command to be run. "
        "IT DOES NOT APPROVE: source code modification, app execution, package installation, "
        "downstream agent execution, context packet approval, handoff execution, branch creation, "
        "commits, pushes, merges, or deletes."
    )
    
    # Save updated JSON
    try:
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(plan_data, f, indent=2)
            
        # Update Markdown report if it exists
        md_path = plan_path.with_suffix(".md")
        if md_path.exists():
            update_plan_md_approval(md_path, plan_data)
            
        # Update/Create Review Report
        report_dir = output_root / "review_reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{plan_path.stem}_review.md"
        write_approval_report(report_path, plan_data)
        
        return True, "Plan approved for Graphify execution.", plan_data
    except Exception as e:
        return False, f"Failed to save approval: {e}", plan_data

def update_plan_md_approval(md_path: Path, plan_data: Dict[str, Any]):
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        new_lines = []
        for line in lines:
            if line.startswith("- **Approval Status**:") or line.startswith("- Approval Status:"):
                new_lines.append(f"- **Approval Status**: `{plan_data['approval_status']}`\n")
                new_lines.append(f"- **Approved At**: {plan_data['approved_at']}\n")
                new_lines.append(f"- **Approval Scope**: {plan_data['approval_scope']}\n")
            else:
                new_lines.append(line)
                
        with open(md_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception:
        pass

def write_approval_report(report_path: Path, plan_data: Dict[str, Any]):
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Review Report: Graphify Plan {plan_data.get('project_id')}\n\n")
        f.write(f"- **Status**: `{plan_data['approval_status']}`\n")
        f.write(f"- **Approved At**: {plan_data.get('approved_at', 'N/A')}\n")
        f.write(f"- **Approval Scope**: {plan_data.get('approval_scope', 'N/A')}\n\n")
        
        f.write("## Approval Notes\n")
        f.write(f"{plan_data.get('approval_notes', 'N/A')}\n\n")
        
        f.write("## Plan Details\n")
        f.write(f"- Project: `{plan_data.get('project_path')}`\n")
        f.write(f"- Output: `{plan_data.get('proposed_output_path')}`\n")
        f.write(f"- Command: `{plan_data.get('proposed_command')}`\n")
