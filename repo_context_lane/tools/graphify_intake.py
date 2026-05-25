import json
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from .summarize import summarize_graph

def run_intake(run_manifest_path: Path, output_root: Path, dry_run: bool = True) -> Tuple[bool, str, Dict[str, Any]]:
    # 1. Load run manifest
    if not run_manifest_path.exists():
        return False, f"Run manifest not found: {run_manifest_path}", {}

    try:
        with open(run_manifest_path, "r", encoding="utf-8") as f:
            run_data = json.load(f)
    except Exception as e:
        return False, f"Failed to load run manifest JSON: {e}", {}

    # 2. Safety and Status checks
    project_id = run_data.get("project_id", "unknown")
    status = run_data.get("execution_status")
    if status != "SUCCEEDED":
        return False, f"Run execution status is not SUCCEEDED (Status: {status})", run_data

    exe = run_data.get("graphify_executable", "")
    expected_exe = r"C:\Users\abi62\AppData\Roaming\Python\Python313\Scripts\graphify.exe"
    if exe != expected_exe:
        return False, f"Run used non-canonical executable: {exe}", run_data

    project_path = Path(run_data.get("project_path", "")).resolve()
    if not project_path.exists():
        return False, f"Project path missing: {project_path}", run_data
    
    if len(project_path.parts) < 2:
        return False, f"Unsafe project scope detected in run: {project_path}", run_data

    output_path = Path(run_data.get("output_path", "")).resolve()
    if str(output_path).startswith(str(project_path)):
        return False, f"Output path is inside project root: {output_path}", run_data

    # 3. Verify graph.json artifact
    graph_path = output_path / "graph.json"
    if not graph_path.exists():
        return False, f"Graph artifact missing at: {graph_path}", run_data

    # 4. Summarize (Reuse existing logic)
    try:
        summary = summarize_graph(graph_path, output_root, dry_run=dry_run)
    except Exception as e:
        return False, f"Summarization failed during intake: {e}", run_data

    # 5. Create intake report
    intake_report = {
        "project_id": project_id,
        "run_manifest_path": str(run_manifest_path),
        "graph_path": str(graph_path),
        "source_output_path": str(output_path),
        "summary_path": str(output_root / "graph_summaries" / f"{project_id}_summary.json") if not dry_run else None,
        "intake_timestamp": datetime.datetime.now().isoformat(),
        "intake_status": "SUCCESS",
        "downstream_status": "SUMMARY_READY",
        "safety_notes": [
            "Verified SUCCEEDED status.",
            "Verified canonical executable.",
            "Verified output path isolation.",
            "Summarization complete."
        ]
    }

    if not dry_run:
        intake_dir = output_root / "graphify_intake_reports"
        intake_dir.mkdir(parents=True, exist_ok=True)
        
        report_id = f"{project_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_intake"
        report_path = intake_dir / f"{report_id}.json"
        md_report_path = intake_dir / f"{report_id}.md"

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(intake_report, f, indent=2)

        with open(md_report_path, "w", encoding="utf-8") as f:
            f.write(f"# Graphify Intake Report: {project_id}\n\n")
            f.write(f"- **Status**: `{intake_report['intake_status']}`\n")
            f.write(f"- **Downstream Status**: `{intake_report['downstream_status']}`\n")
            f.write(f"- **Timestamp**: {intake_report['intake_timestamp']}\n\n")
            f.write("## Traceability\n")
            f.write(f"- **Run Manifest**: `{intake_report['run_manifest_path']}`\n")
            f.write(f"- **Graph Path**: `{intake_report['graph_path']}`\n")
            if intake_report['summary_path']:
                f.write(f"- **Summary Path**: `{intake_report['summary_path']}`\n")
            f.write("\n")
            f.write("## Safety Verification\n")
            for note in intake_report["safety_notes"]:
                f.write(f"- [x] {note}\n")

        return True, f"Graphify intake SUCCEEDED for {project_id}.", intake_report

    return True, "Graphify intake dry-run successful.", intake_report
