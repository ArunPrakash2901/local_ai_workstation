import os
import sys
import json
from pathlib import Path

# Add the scripts directory to sys.path to allow imports from quant package
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.append(str(SCRIPTS_DIR))

from quant.paths import REPO_ROOT

def get_report_count(subdir):
    path = REPO_ROOT / "reports" / "quant" / subdir
    if not path.exists():
        return 0
    return len([f for f in path.iterdir() if f.is_file()])

def detect_latest_milestone():
    docs_dir = REPO_ROOT / "docs" / "quant_mvp"
    if not docs_dir.exists():
        return "UNKNOWN"
    
    # Ordered list of milestone reports to check (newest first)
    milestone_reports = [
        ("Q39-Q41", "Q39_Q41_REPORT_BROWSER_LINEAGE_REPORT.md"),
        ("Q36-Q38", "Q36_Q38_OPERATOR_DASHBOARD_REPORT.md"),
        ("Q33-Q35", "Q33_Q35_COMMAND_SURFACE_PROTOTYPE_REPORT.md"),
        ("Q30-Q32", "Q30_Q32_BACKTEST_TRANSITION_DESIGN_REPORT.md"),
        ("Q27-Q29", "Q27_Q29_SYNTHETIC_EXECUTION_REPORT.md"),
        ("Q24-Q26", "Q24_Q26_BACKTEST_EXECUTION_GATE_REPORT.md"),
        ("Q21-Q23", "Q21_Q23_BACKTEST_ELIGIBILITY_REPORT.md"),
        ("Q18-Q20", "Q18_Q20_BACKTEST_GATE_INPUTS_REPORT.md"),
        ("Q15-Q17", "Q15_Q17_BACKTEST_PREPARATION_REPORT.md"),
        ("Q12-Q14", "Q12_Q14_READINESS_REMEDIATION_REPORT.md"),
        ("Q9-Q11", "Q9_Q11_BACKTEST_SKELETON_REPORT.md"),
        ("Q6-Q8", "Q6_Q8_STRATEGY_CANDIDATE_READINESS_REPORT.md"),
        ("Q5", "Q5_RESEARCH_PAPER_REPLICATION_REPORT.md"),
        ("Q4", "Q4_RESEARCH_IDEA_INTAKE_REPORT.md"),
        ("Q3", "Q3_SYNTHESIS_REPORT.md")
    ]
    
    for milestone, filename in milestone_reports:
        if (docs_dir / filename).exists():
            return milestone
            
    return "UNKNOWN"

def quant_status_summary():
    latest_milestone = detect_latest_milestone()
    
    # Heuristic for plumbing validity and lineage
    synthetic_ready = get_report_count("synthetic_result_reviews") > 0
    candidate_ready = get_report_count("candidate_concrete_specs") > 0

    summary = {
        "lane_status": "ACTIVE_RESEARCH",
        "latest_known_milestone": latest_milestone,
        "real_backtest_enabled": False,
        "approval_granted": False,
        "broker_logic_present": False,
        "live_trading_present": False,
        "synthetic_plumbing_valid": synthetic_ready,
        "current_candidate_lineage": "R3_VWAP" if candidate_ready else "UNKNOWN"
    }
    return summary

def list_quant_tools():
    quant_scripts_dir = REPO_ROOT / "scripts" / "quant"
    tools = []
    if quant_scripts_dir.exists():
        for f in quant_scripts_dir.glob("*_cli.py"):
            tools.append({
                "name": f.name,
                "exposure": "standalone_only"
            })
    
    # Identify which are exposed in ws
    ws_exposed = ["status", "list-tools", "synthetic-status", "gates-status", "dashboard", "reports", "artifacts", "lineage", "cheatsheet"]
    
    return {
        "standalone_scripts": tools,
        "ws_exposed_commands": ws_exposed
    }

def synthetic_status_summary():
    run_count = get_report_count("synthetic_execution_runs")
    review_count = get_report_count("synthetic_result_reviews")
    
    return {
        "synthetic_execution_artifact_exists": run_count > 0,
        "synthetic_result_review_exists": review_count > 0,
        "confirm_synthetic_only": True,
        "confirm_not_strategy_evaluation": True,
        "run_count": run_count,
        "review_count": review_count
    }

def gate_status_summary():
    gates = {
        "readiness": "PASS" if get_report_count("pre_backtest_readiness") > 0 else "UNKNOWN",
        "eligibility": "PASS" if get_report_count("backtest_eligibility_reports") > 0 else "UNKNOWN",
        "preflight": "PASS" if get_report_count("backtest_execution_preflights") > 0 else "UNKNOWN",
        "approval_validation": "PASS" if get_report_count("backtest_approval_validations") > 0 else "UNKNOWN"
    }
    
    all_pass = all(v == "PASS" for v in gates.values())
    
    return {
        "gates": gates,
        "real_backtest_blocked": not all_pass or True, # Still blocked regardless in this milestone
        "block_reason": "Real backtest execution not yet implemented/authorized" if all_pass else "Gates not fully passed"
    }

def quant_dashboard_summary():
    status = quant_status_summary()
    tools = list_quant_tools()
    gates = gate_status_summary()
    
    dashboard = {
        "latest_completed_milestone": status["latest_known_milestone"],
        "active_ws_quant_commands": tools["ws_exposed_commands"],
        "standalone_tool_count": len(tools["standalone_scripts"]),
        "current_candidate_lineage": status["current_candidate_lineage"],
        "synthetic_plumbing_valid": status["synthetic_plumbing_valid"],
        "master_gate_status": "READY_FOR_HUMAN_APPROVAL" if gates["real_backtest_blocked"] and all(v == "PASS" for v in gates["gates"].values()) else "IN_PROGRESS",
        "real_backtest_enabled": False,
        "approval_granted": False,
        "data_downloaded_by_system": False,
        "broker_live_paper_trading_present": False,
        "resource_posture": "CPU-only, no GPU, low RAM"
    }
    return dashboard

def quant_reports_summary():
    docs_dir = REPO_ROOT / "docs" / "quant_mvp"
    if not docs_dir.exists():
        return {"error": "docs/quant_mvp not found"}
    
    reports = []
    for f in docs_dir.glob("Q*_REPORT.md"):
        reports.append(str(f.relative_to(REPO_ROOT)))
    
    # Simple grouping
    phases = {
        "planning": [r for r in reports if "Q30_Q32" in r or "Q3" in r],
        "intake_idea": [r for r in reports if "Q4" in r],
        "replication_candidate": [r for r in reports if "Q5" in r or "Q6_Q8" in r or "Q10" in r],
        "readiness_gates": [r for r in reports if "Q12" in r or "Q15" in r or "Q18" in r or "Q21" in r or "Q24" in r],
        "synthetic_execution": [r for r in reports if "Q27_Q29" in r],
        "operator_commands": [r for r in reports if "Q33_Q35" in r or "Q36_Q38" in r or "Q39_Q41" in r]
    }
    
    return {
        "latest_report": detect_latest_milestone(),
        "report_phases": phases,
        "all_q_reports": sorted(reports)
    }

def quant_artifacts_summary():
    artifact_dirs = [
        "research_ideas",
        "paper_replications",
        "strategy_candidates",
        "pre_backtest_readiness",
        "backtest_plans",
        "backtest_eligibility_reports",
        "synthetic_execution_runs",
        "synthetic_result_reviews"
    ]
    
    summary = {}
    for d in artifact_dirs:
        summary[d] = {
            "count": get_report_count(d)
        }
        
    summary["real_backtest_enabled"] = False
    summary["approval_granted"] = False
    return summary

def quant_lineage_lookup(artifact_id):
    # Map ID prefix to folder
    prefix_map = {
        "RI-": "research_ideas",
        "PPR-": "paper_replications",
        "CAN-": "strategy_candidates",
        "SYN-": "synthetic_execution_runs",
        "SRV-": "synthetic_result_reviews"
    }
    
    folder = None
    for prefix, f in prefix_map.items():
        if artifact_id.startswith(prefix):
            folder = f
            break
            
    if not folder:
        return {"artifact_id": artifact_id, "status": "NOT_FOUND", "reason": "Invalid ID prefix"}
        
    # Find file
    base_path = REPO_ROOT / "reports" / "quant" / folder
    file_path = base_path / f"{artifact_id}.json"
    
    if not file_path.exists():
        return {"artifact_id": artifact_id, "status": "NOT_FOUND", "path": str(file_path.relative_to(REPO_ROOT))}
        
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            
        lineage = {
            "artifact_id": artifact_id,
            "artifact_type": folder.rstrip('s'),
            "file_path": str(file_path.relative_to(REPO_ROOT)),
            "status": data.get("candidate_status", data.get("review_status", data.get("run_status", "UNKNOWN"))),
            "safety_flags": {
                "financial_advice": data.get("safety_financial_advice_generated", False),
                "trading_signals": data.get("safety_trading_signal_generated", False)
            },
            "parents": [],
            "children": [] # Inferring children is more expensive, skipping for now unless easy
        }
        
        # Link parents
        parent_keys = ["linked_idea_id", "linked_paper_id", "linked_strategy_candidate_id", "linked_synthetic_run_id"]
        for k in parent_keys:
            if k in data and data[k] != "UNKNOWN":
                lineage["parents"].append(data[k])
                
        return lineage
    except Exception as e:
        return {"artifact_id": artifact_id, "status": "ERROR", "reason": str(e)}

def print_safety_frame():
    print("--------------------------------------------------")
    print("SAFETY NOTICE: Research Only")
    print("- no_financial_advice: true")
    print("- no_trading_signals: true")
    print("- no_broker_logic: true")
    print("- no_live_trading: true")
    print("- no_real_backtest_run: true")
    print("- safety_financial_advice_generated: false")
    print("--------------------------------------------------")

def main():
    if len(sys.argv) < 2:
        print("Usage: ws_quant_summary.py <command> [args]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    print_safety_frame()
    
    if cmd == "status":
        s = quant_status_summary()
        for k, v in s.items():
            print(f"{k}: {v}")
    elif cmd == "list-tools":
        t = list_quant_tools()
        print("Standalone Quant Tools:")
        for tool in t["standalone_scripts"]:
            print(f"  - {tool['name']} ({tool['exposure']})")
        print("\nWS Exposed Commands:")
        for ws_cmd in t["ws_exposed_commands"]:
            print(f"  - ws quant {ws_cmd}")
    elif cmd == "synthetic-status":
        s = synthetic_status_summary()
        for k, v in s.items():
            print(f"{k}: {v}")
    elif cmd == "gates-status":
        g = gate_status_summary()
        print("Gate Statuses:")
        for k, v in g["gates"].items():
            print(f"  {k}: {v}")
        print(f"\nReal Backtest Blocked: {g['real_backtest_blocked']}")
        print(f"Reason: {g['block_reason']}")
    elif cmd == "dashboard":
        d = quant_dashboard_summary()
        for k, v in d.items():
            if isinstance(v, list):
                print(f"{k}: {', '.join(v)}")
            else:
                print(f"{k}: {v}")
    elif cmd == "reports":
        r = quant_reports_summary()
        print(f"Latest Report: {r['latest_report']}\n")
        for phase, reports in r['report_phases'].items():
            if reports:
                print(f"{phase.replace('_', ' ').title()}:")
                for report in reports:
                    print(f"  - {report}")
    elif cmd == "artifacts":
        a = quant_artifacts_summary()
        print("Quant Artifact Counts:")
        for k, v in a.items():
            if isinstance(v, dict):
                print(f"  {k}: {v['count']}")
            else:
                print(f"  {k}: {v}")
    elif cmd == "lineage":
        if len(sys.argv) < 3:
            print("Usage: ws quant lineage <artifact_id>")
            sys.exit(1)
        l = quant_lineage_lookup(sys.argv[2])
        for k, v in l.items():
            print(f"{k}: {v}")
    elif cmd == "cheatsheet":
        cheatsheet_path = REPO_ROOT / "docs" / "quant_mvp" / "QUANT_OPERATOR_CHEATSHEET.md"
        if cheatsheet_path.exists():
            print(f"Operator Cheatsheet Location: {cheatsheet_path.relative_to(REPO_ROOT)}\n")
            with open(cheatsheet_path, "r") as f:
                print(f.read())
        else:
            print("Cheatsheet not found. Use 'ws quant list-tools' for command list.")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
