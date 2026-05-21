#!/usr/bin/env python3
"""Learning Advancement Readiness Planner v1."""

import json
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict

# Reuse helpers from state sync planner
def load_json(path: Path):
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def load_ledger(path: Path):
    if not path.is_file():
        return []
    entries = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        entries.append({"error": "malformed_json", "raw": line})
    except Exception:
        return None
    return entries

def normalize_path(path_str, ws_home):
    """Normalize Windows/WSL paths to the current OS."""
    if not path_str:
        return None
    if os.name != 'nt' and (path_str.startswith('D:\\') or path_str.startswith('C:\\')):
        path_str = path_str.replace('D:\\', '/mnt/d/').replace('C:\\', '/mnt/c/').replace('\\', '/')
    elif os.name == 'nt' and path_str.startswith('/mnt/'):
        path_str = path_str.replace('/mnt/d/', 'D:\\').replace('/mnt/c/', 'C:\\').replace('/', '\\')
    return Path(path_str)

def get_pointer_status(stronghold_id, ws_home):
    """Call the pointer update planner in dry-run JSON mode."""
    script_path = ws_home / "scripts" / "learning_pointer_update_planner.py"
    if not script_path.is_file():
        return None
    try:
        res = subprocess.run(
            [sys.executable, str(script_path), stronghold_id, "--dry-run", "--json"],
            capture_output=True,
            text=True,
            env={"WS_HOME": str(ws_home), "PYTHONDONTWRITEBYTECODE": "1"}
        )
        if res.returncode == 0:
            return json.loads(res.stdout)
    except Exception:
        pass
    return None

def generate_advancement_plan(stronghold_dir: Path, state: dict, ledger: list, audit: list):
    ws_home = Path(os.environ.get("WS_HOME", "D:\\_ai_brain" if os.name == 'nt' else "/mnt/d/_ai_brain"))
    timestamp = datetime.now().strftime('%Y%m%dT%H%M%SZ')
    plan_id = f"ADV-PLAN-{timestamp}"
    
    current_state = state.get("current_state", "UNKNOWN")
    session_status = state.get("learning_session_status", "UNKNOWN")
    
    # Supported states for v1 assessment
    SUPPORTED_STATES = {
        "LOCAL_CHECKLIST_READY",
        "READY_FOR_LOCAL_WORK",
        "SESSIONS_IN_PROGRESS",
        "AUDIT_TESTING",
    }
    
    plan = {
        "advancement_plan_id": plan_id,
        "timestamp_utc": timestamp,
        "stronghold_id": stronghold_dir.name,
        "source": "learning_advancement_readiness_planner_v1",
        "mode": "DRY_RUN_ONLY",
        "current_state": current_state,
        "learning_session_status": session_status,
        "current_next_learning_task": state.get("next_learning_task"),
        "pointer_status": "unknown",
        "latest_state_sync_status": "unknown",
        "readiness_status": "insufficient_evidence",
        "proposed_future_state": "MANUAL_REVIEW_REQUIRED",
        "readiness_score": 0,
        "evidence": [],
        "evidence_quality": "insufficient",
        "blockers": [],
        "warnings": [],
        "required_human_checks": [
            "Verify all learning objectives for the current stage are met.",
            "Confirm that the 'next_learning_task' represents a genuine advancement step.",
            "Inspect most recent tutor session and assessment artifacts."
        ],
        "requires_human_review": True,
        "can_apply_now": False,
        "apply_allowed_in_phase_10b": False,
        "risk_level": "HIGH"
    }

    if current_state not in SUPPORTED_STATES:
        plan["warnings"].append(f"current_state '{current_state}' is not explicitly supported by v1 assessment rules.")

    # 1. State Sync Audit Check
    if audit:
        latest_audit = audit[-1]
        plan["latest_state_sync_status"] = latest_audit.get("confirmation_status", "unknown")
        if plan["latest_state_sync_status"] == "STATE_SYNC_APPLIED":
            plan["evidence"].append("Latest state sync successful.")
        else:
            plan["warnings"].append(f"Latest state sync status is {plan['latest_state_sync_status']}.")
    else:
        plan["warnings"].append("No state sync audit records found.")

    # 2. Pointer Status Check
    pointer_plan = get_pointer_status(stronghold_dir.name, ws_home)
    if pointer_plan:
        plan["pointer_status"] = pointer_plan.get("candidate_status", "unknown")
        if plan["pointer_status"] == "already_synchronized":
            plan["evidence"].append("next_learning_task is already synchronized.")
        elif plan["pointer_status"] == "eligible":
            plan["blockers"].append("next_learning_task pointer update is pending. Sync pointer first.")
        elif plan["pointer_status"] == "conflict":
            plan["blockers"].append("Conflicting candidates for next_learning_task.")
    else:
        plan["warnings"].append("Could not determine pointer status.")

    # 3. Ledger Integrity Check
    if ledger is None:
        plan["blockers"].append("Ledger file missing or unreadable.")
        plan["readiness_status"] = "blocked"
        return plan
    
    if not ledger:
        plan["blockers"].append("No confirmed learning actions found.")
    else:
        # Check for malformed entries
        malformed = [e for e in ledger if "error" in e]
        if malformed:
            plan["blockers"].append(f"Found {len(malformed)} malformed entries in ledger.")
        
        # Check for missing artifacts
        missing_artifacts = []
        for entry in ledger:
            if entry.get("confirmation_status") == "CONFIRMED_APPLIED":
                ap = entry.get("artifact_path")
                if not ap:
                    missing_artifacts.append(f"Confirmation {entry.get('confirmation_id')} missing artifact_path.")
                else:
                    path = normalize_path(ap, ws_home)
                    if not path.is_file():
                        missing_artifacts.append(f"Artifact file missing: {ap}")
        
        if missing_artifacts:
            plan["blockers"].extend(missing_artifacts[:3]) # Limit display
            if len(missing_artifacts) > 3:
                plan["blockers"].append(f"... and {len(missing_artifacts) - 3} more missing artifacts.")

    # 4. Readiness Evaluation
    score = 0
    if not plan["blockers"]:
        # Strong evidence baseline
        if plan["pointer_status"] == "already_synchronized" and plan["latest_state_sync_status"] == "STATE_SYNC_APPLIED":
            score += 50
            plan["evidence_quality"] = "strong"
            plan["readiness_status"] = "ready_for_human_review"
        else:
            score += 20
            plan["evidence_quality"] = "partial"
            plan["readiness_status"] = "partially_ready"
    else:
        plan["readiness_status"] = "blocked"
        plan["evidence_quality"] = "insufficient"

    plan["readiness_score"] = score

    # v1 Guards
    plan["warnings"].append("Advancement remains manual in Phase 10A.")
    plan["apply_allowed_in_phase_10b"] = False
    plan["can_apply_now"] = False

    return plan

def main():
    if "--dry-run" not in sys.argv:
        print("Error: This tool currently only supports --dry-run mode.")
        sys.exit(1)

    is_json = "--json" in sys.argv
    
    default_ws_home = "D:\\_ai_brain" if os.name == 'nt' else "/mnt/d/_ai_brain"
    ws_home = Path(os.environ.get("WS_HOME", default_ws_home))
    strongholds_dir = ws_home / "strongholds"
    
    stronghold_id = None
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            stronghold_id = arg
            break
            
    if not stronghold_id:
        if is_json:
            print(json.dumps({"error": "No stronghold ID provided.", "status": "FAILED"}))
        else:
            print("Error: No stronghold ID provided.")
        sys.exit(1)
        
    stronghold_dir = strongholds_dir / "learning" / stronghold_id
    if not stronghold_dir.is_dir():
        if is_json:
            print(json.dumps({"error": f"Stronghold not found at {stronghold_dir}", "status": "FAILED"}))
        else:
            print(f"Error: Stronghold not found at {stronghold_dir}")
        sys.exit(1)

    state = load_json(stronghold_dir / "state.json")
    if not state:
        if is_json:
            print(json.dumps({"error": f"Could not load state.json for {stronghold_id}", "status": "FAILED"}))
        else:
            print(f"Error: Could not load state.json for {stronghold_id}")
        sys.exit(1)
        
    ledger = load_ledger(stronghold_dir / "learning_confirmations.jsonl")
    audit = load_ledger(stronghold_dir / "state_sync_audit.jsonl") # Same format
    
    plan = generate_advancement_plan(stronghold_dir, state, ledger, audit)
    
    if is_json:
        print(json.dumps(plan, indent=2))
    else:
        print(f"Learning Advancement Readiness Plan v1 for: {state.get('title', stronghold_id)}")
        print("=" * 75)
        print(f"Plan ID:          {plan['advancement_plan_id']}")
        print(f"Status:           {plan['mode']}")
        print(f"Readiness Status: {plan['readiness_status'].upper()}")
        print(f"Readiness Score:  {plan['readiness_score']}/100")
        print("-" * 75)
        print(f"Current State:    {plan['current_state']}")
        print(f"Session Status:   {plan['learning_session_status']}")
        print(f"Next Task:        {plan['current_next_learning_task']}")
        print(f"Pointer Status:   {plan['pointer_status']}")
        print(f"Latest Sync:      {plan['latest_state_sync_status']}")
        print("-" * 75)
        print(f"Risk Level:       {plan['risk_level']}")
        print(f"Evidence Quality: {plan['evidence_quality']}")
        print(f"Phase 10B Eligible: {plan['apply_allowed_in_phase_10b']}")
        print("-" * 75)
        
        if plan["blockers"]:
            print("BLOCKERS:")
            for b in plan["blockers"]:
                print(f"X {b}")
            print("-" * 75)
            
        if plan["warnings"]:
            print("WARNINGS:")
            for w in plan["warnings"]:
                print(f"! {w}")
            print("-" * 75)

        if plan["required_human_checks"]:
            print("REQUIRED HUMAN CHECKS:")
            for c in plan["required_human_checks"]:
                print(f"? {c}")
            print("-" * 75)

        print(f"Proposed Future State (Advisory): {plan['proposed_future_state']}")
        print("-" * 75)
        print("\nDRY-RUN ONLY: current_state was not modified.")
        print("Advancement remains manual in Phase 10A.")

if __name__ == "__main__":
    main()
