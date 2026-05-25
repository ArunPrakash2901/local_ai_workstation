import json
import datetime
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from .graphify_plan_review import review_plan

DEFAULT_TIMEOUT_SECONDS = 600 # 10 minutes

def run_graphify(plan_path: Path, output_root: Path, confirm: bool = False) -> Tuple[bool, str, Dict[str, Any]]:
    if not confirm:
        return False, "Execution requires --confirm.", {}

    # 1. Load and re-validate plan
    is_valid, issues, plan_data = review_plan(plan_path, output_root)
    if not is_valid:
        return False, f"Execution refused due to plan issues: {', '.join(issues)}", plan_data

    # 2. Check approval status
    status = plan_data.get("approval_status")
    scope = plan_data.get("approval_scope")
    if status != "APPROVED_FOR_GRAPHIFY_EXECUTION":
        return False, f"Plan is not approved for execution (Status: {status})", plan_data
    if scope != "GRAPHIFY_RUN_ONLY":
        return False, f"Plan has invalid approval scope (Scope: {scope})", plan_data

    # 3. Final safety checks (redundant but critical)
    project_path = Path(plan_data["project_path"]).resolve()
    output_path = Path(plan_data["proposed_output_path"]).resolve()
    graphify_exe = Path(plan_data["graphify_exe"]).resolve()

    if not graphify_exe.exists():
        return False, f"Graphify executable not found at: {graphify_exe}", plan_data

    # 4. Prepare command (bounded)
    # We rebuild the command list to avoid any shell injection or unexpected args in plan
    # Canonical: graphify build <project_path> --output <output_path>
    cmd = [
        str(graphify_exe),
        "build",
        str(project_path),
        "--output",
        str(output_path)
    ]

    # 5. Execute (guarded)
    output_path.mkdir(parents=True, exist_ok=True)
    
    started_at = datetime.datetime.now()
    started_at_iso = started_at.isoformat()
    
    manifest = {
        "project_id": plan_data.get("project_id"),
        "plan_path": str(plan_path),
        "plan_approved_at": plan_data.get("approved_at"),
        "graphify_executable": str(graphify_exe),
        "project_path": str(project_path),
        "output_path": str(output_path),
        "command_args": cmd,
        "approval_status": status,
        "approval_scope": scope,
        "started_at": started_at_iso,
        "execution_status": "RUNNING",
        "safety_notes": [
            "Guarded Graphify execution.",
            "Subprocess run with timeout.",
            "No shell used."
        ]
    }

    try:
        # Run with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            check=False
        )
        
        finished_at = datetime.datetime.now()
        duration = (finished_at - started_at).total_seconds()
        
        manifest.update({
            "finished_at": finished_at.isoformat(),
            "duration_seconds": duration,
            "return_code": result.returncode,
            "execution_status": "SUCCEEDED" if result.returncode == 0 else "FAILED",
            "stdout_excerpt": result.stdout[-5000:] if result.stdout else "",
            "stderr_excerpt": result.stderr[-5000:] if result.stderr else "",
            "graph_path": str(output_path / "graph.json") if result.returncode == 0 else None
        })
        
    except subprocess.TimeoutExpired as te:
        manifest.update({
            "finished_at": datetime.datetime.now().isoformat(),
            "execution_status": "TIMED_OUT",
            "stderr_excerpt": f"Execution timed out after {DEFAULT_TIMEOUT_SECONDS} seconds."
        })
    except Exception as e:
        manifest.update({
            "finished_at": datetime.datetime.now().isoformat(),
            "execution_status": "ERROR",
            "stderr_excerpt": str(e)
        })

    # 6. Save run manifest
    run_dir = output_root / "graphify_runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp_str = started_at.strftime("%Y%m%d_%H%M%S")
    run_id = f"{plan_data['project_id']}_{timestamp_str}"
    
    manifest_path = run_dir / f"{run_id}.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        
    # Write review report
    report_dir = output_root / "review_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{run_id}_run.md"
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Graphify Run Report: {run_id}\n\n")
        f.write(f"- **Project**: {manifest['project_id']}\n")
        f.write(f"- **Status**: `{manifest['execution_status']}`\n")
        f.write(f"- **Return Code**: {manifest.get('return_code', 'N/A')}\n")
        f.write(f"- **Duration**: {manifest.get('duration_seconds', 'N/A')}s\n\n")
        f.write("## Command Details\n")
        f.write(f"- **Executable**: `{manifest['graphify_executable']}`\n")
        f.write(f"- **Project Path**: `{manifest['project_path']}`\n")
        f.write(f"- **Output Path**: `{manifest['output_path']}`\n\n")
        if manifest.get("stderr_excerpt"):
            f.write("## Errors / Stderr Excerpt\n")
            f.write(f"```\n{manifest['stderr_excerpt']}\n```\n")

    success = manifest["execution_status"] == "SUCCEEDED"
    message = f"Graphify execution {manifest['execution_status']}."
    if not success:
        message += f" Check {report_path} for details."
        
    return success, message, manifest

def get_run_status(plan_path: Path, output_root: Path) -> Dict[str, Any]:
    run_dir = output_root / "graphify_runs"
    if not run_dir.exists():
        return {"status": "NOT_RUN"}
        
    project_id = plan_path.stem.replace("_plan", "")
    runs = []
    for path in run_dir.glob(f"{project_id}_*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                runs.append({
                    "id": path.stem,
                    "started_at": data.get("started_at"),
                    "status": data.get("execution_status"),
                    "return_code": data.get("return_code")
                })
        except Exception:
            pass
            
    if not runs:
        return {"status": "NOT_RUN"}
        
    latest = sorted(runs, key=lambda x: x["started_at"], reverse=True)[0]
    return {
        "status": latest["status"],
        "last_run": latest
    }
