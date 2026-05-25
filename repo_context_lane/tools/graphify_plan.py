import json
import datetime
from pathlib import Path
from typing import Dict, Any

GRAPHIFY_EXE = r"C:\Users\abi62\AppData\Roaming\Python\Python313\Scripts\graphify.exe"
SAFE_OUTPUT_ROOT = Path(r"D:\graphify-results")

def generate_plan(project_path: Path, output_root: Path, dry_run: bool = True) -> Dict[str, Any]:
    project_path = project_path.resolve()
    project_id = project_path.name
    
    # Validation
    if not project_path.exists() or not project_path.is_dir():
        raise ValueError(f"Project path does not exist or is not a directory: {project_path}")

    # Output path logic
    graphify_out_root = SAFE_OUTPUT_ROOT / project_id
    proposed_output = graphify_out_root / "graphify-out"
    
    if str(proposed_output).startswith(str(project_path)):
        raise ValueError(f"Output path must be outside project root: {proposed_output}")

    # Command generation
    command = f'"{GRAPHIFY_EXE}" build "{project_path}" --output "{proposed_output}"'
    
    plan_data = {
        "project_id": project_id,
        "project_path": str(project_path),
        "proposed_output_path": str(proposed_output),
        "graphify_exe": GRAPHIFY_EXE,
        "proposed_command": command,
        "timestamp": datetime.datetime.now().isoformat(),
        "approval_status": "NOT_APPROVED",
        "safety_checks": [
            "Output path is outside project root",
            "Project path exists",
            "Command uses absolute paths"
        ]
    }
    
    if not dry_run:
        plan_dir = output_root / "graphify_plans"
        plan_dir.mkdir(parents=True, exist_ok=True)
        
        manifest_path = plan_dir / f"{project_id}_plan.json"
        report_path = plan_dir / f"{project_id}_plan.md"
        
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(plan_data, f, indent=2)
            
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Graphify Run Plan: {project_id}\n\n")
            f.write(f"- **Project Path**: `{project_path}`\n")
            f.write(f"- **Proposed Output**: `{proposed_output}`\n")
            f.write(f"- **Approval Status**: `NOT_APPROVED`\n\n")
            f.write("## Proposed Command\n")
            f.write(f"```powershell\n{command}\n```\n\n")
            f.write("## Safety Checks\n")
            for check in plan_data["safety_checks"]:
                f.write(f"- [x] {check}\n")
            f.write("\n")
            f.write("> **Note**: This is a dry-run plan. Graphify will NOT be executed by this lane in v0.1.\n")
            
    return plan_data

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        o = Path("repo_context_lane")
        res = generate_plan(p, o, dry_run=False)
        print(json.dumps(res, indent=2))
