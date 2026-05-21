#!/usr/bin/env python3
"""Learning State Synchronization Planner v1."""

import json
import sys
import os
import hashlib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict

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
                        # Malformed line handled by warning in plan
                        entries.append({"error": "malformed_json", "raw": line})
    except Exception:
        return None
    return entries

# Schema Allowlist for State Synchronization
STATE_PATH_ALLOWLIST = {
    "state.learning_session_status",
    "state.last_reported_at",
    "state.next_learning_task",
    "state.last_learning_decision",
    "state.current_state",
}

def normalize_path(path_str, ws_home):
    """Normalize Windows/WSL paths to the current OS."""
    if not path_str:
        return None
    
    # If we are on WSL/Linux and the path looks like Windows
    if os.name != 'nt' and (path_str.startswith('D:\\') or path_str.startswith('C:\\')):
        path_str = path_str.replace('D:\\', '/mnt/d/').replace('C:\\', '/mnt/c/').replace('\\', '/')
    # If we are on Windows and the path looks like WSL/Linux
    elif os.name == 'nt' and path_str.startswith('/mnt/'):
        path_str = path_str.replace('/mnt/d/', 'D:\\').replace('/mnt/c/', 'C:\\').replace('/', '\\')
        
    return Path(path_str)

def generate_plan(stronghold_dir: Path, state: dict, ledger: list):
    ws_home = Path(os.environ.get("WS_HOME", "/mnt/d/_ai_brain"))
    # ...
    timestamp = datetime.now().strftime('%Y%m%dT%H%M%SZ')
    plan_id = f"SYNC-PLAN-{timestamp}"
    
    plan = {
        "plan_id": plan_id,
        "timestamp_utc": timestamp,
        "stronghold_id": stronghold_dir.name,
        "source": "learning_state_sync_planner_v1",
        "mode": "DRY_RUN_ONLY",
        "state_path": str(stronghold_dir / "state.json"),
        "ledger_path": str(stronghold_dir / "learning_confirmations.jsonl"),
        "current_state_summary": {
            "current_state": state.get("current_state"),
            "next_learning_task": state.get("next_learning_task"),
            "last_decision": state.get("last_learning_decision")
        },
        "eligible_confirmations": [],
        "informational_confirmations": [],
        "blocked_confirmations": [],
        "proposed_state_changes": [],
        "warnings": [],
        "blockers": [],
        "requires_human_review": True,
        "can_apply_now": False
    }

    if ledger is None:
        plan["blockers"].append("Ledger file missing or unreadable.")
        return plan

    # Track seen action IDs for duplicate detection
    seen_action_ids = {}

    for entry in ledger:
        if "error" in entry:
            plan["warnings"].append(f"Malformed entry in ledger: {entry['raw'][:50]}...")
            continue
            
        action_id = entry.get("original_action_id")
        if not action_id:
            plan["warnings"].append(f"Ledger entry missing original_action_id: {entry.get('confirmation_id')}")
            continue

        if action_id in seen_action_ids:
            plan["warnings"].append(f"Duplicate confirmation for action_id {action_id} detected.")
            plan["blocked_confirmations"].append(entry)
            continue
        
        seen_action_ids[action_id] = entry

        # Safety checks
        artifact_path_str = entry.get("artifact_path")
        if not artifact_path_str:
            plan["warnings"].append(f"Confirmation {entry.get('confirmation_id')} is missing artifact_path.")
            plan["blocked_confirmations"].append(entry)
            continue
            
        artifact_path = normalize_path(artifact_path_str, ws_home)
        try:
            if not artifact_path.is_file():
                plan["warnings"].append(f"Referenced artifact does not exist: {artifact_path_str}")
                plan["blocked_confirmations"].append(entry)
                continue
            
            # Check if artifact is within stronghold
            artifact_path.relative_to(stronghold_dir)
        except (ValueError, Exception):
            plan["warnings"].append(f"Artifact path is outside the stronghold or invalid: {artifact_path_str}")
            plan["blocked_confirmations"].append(entry)
            continue

        status = entry.get("confirmation_status")
        if status != "CONFIRMED_APPLIED":
            plan["informational_confirmations"].append(entry)
            continue

        action_type = entry.get("confirmed_action_type")
        
        # Classification and Change Generation
        change = None
        
        if action_type == "CREATE_STUDY_TASK_CONFIRMED":
            plan["eligible_confirmations"].append(entry)
            change = {
                "target_path": "state.learning_session_status",
                "current_value": state.get("learning_session_status"),
                "proposed_value": "study_task_confirmed",
                "reason": f"Study task confirmed: {entry.get('title')}",
                "source_confirmation_id": entry.get("confirmation_id"),
                "source_action_id": action_id,
                "risk_level": "LOW",
                "evidence_quality": "strong",
                "evidence_notes": f"Verified artifact {artifact_path_str} exists.",
                "apply_allowed_in_v1": False,
                "apply_allowed_in_phase_7b": True
            }
            
        elif action_type == "SUMMARIZE_SESSION_CONFIRMED":
            plan["eligible_confirmations"].append(entry)
            change = {
                "target_path": "state.last_reported_at",
                "current_value": state.get("last_reported_at"),
                "proposed_value": entry.get("timestamp_utc"),
                "reason": "Session summary confirmed.",
                "source_confirmation_id": entry.get("confirmation_id"),
                "source_action_id": action_id,
                "risk_level": "LOW",
                "evidence_quality": "strong",
                "evidence_notes": f"Summary artifact recorded at {artifact_path_str}.",
                "apply_allowed_in_v1": False,
                "apply_allowed_in_phase_7b": True
            }

        elif action_type == "PROPOSE_NEXT_LESSON_CONFIRMED":
            plan["eligible_confirmations"].append(entry)
            proposed_val = entry.get("evidence", "").replace("next_learning_task: ", "")
            quality = "strong" if proposed_val else "insufficient"
            change = {
                "target_path": "state.next_learning_task",
                "current_value": state.get("next_learning_task"),
                "proposed_value": proposed_val,
                "reason": "Next lesson pointer update confirmed.",
                "source_confirmation_id": entry.get("confirmation_id"),
                "source_action_id": action_id,
                "risk_level": "MEDIUM",
                "evidence_quality": quality,
                "evidence_notes": f"Extracted next task from evidence: '{proposed_val}'",
                "apply_allowed_in_v1": False,
                "apply_allowed_in_phase_7b": (quality == "strong")
            }

        elif action_type == "MARK_REVIEW_NEEDED_CONFIRMED":
            plan["eligible_confirmations"].append(entry)
            change = {
                "target_path": "state.last_learning_decision",
                "current_value": state.get("last_learning_decision"),
                "proposed_value": "REVIEW_NEEDED",
                "reason": "Topic review confirmed as needed.",
                "source_confirmation_id": entry.get("confirmation_id"),
                "source_action_id": action_id,
                "risk_level": "LOW",
                "evidence_quality": "strong",
                "evidence_notes": "Review request confirmed by operator.",
                "apply_allowed_in_v1": False,
                "apply_allowed_in_phase_7b": True
            }

        elif action_type == "ASSESS_ADVANCEMENT_READINESS_CONFIRMED":
            plan["eligible_confirmations"].append(entry)
            # Check for assessment evidence in title or evidence field
            has_evidence = "assessment" in entry.get("evidence", "").lower() or "readiness" in entry.get("evidence", "").lower()
            quality = "strong" if has_evidence else "partial"
            change = {
                "target_path": "state.current_state",
                "current_value": state.get("current_state"),
                "proposed_value": "READY_FOR_ADVANCEMENT",
                "reason": "Advancement readiness assessment confirmed. Note: Advancement is not automatic.",
                "source_confirmation_id": entry.get("confirmation_id"),
                "source_action_id": action_id,
                "risk_level": "HIGH",
                "evidence_quality": quality,
                "evidence_notes": "Requires thorough review of assessment artifact.",
                "apply_allowed_in_v1": False,
                "apply_allowed_in_phase_7b": False # Advancement always manual review in Phase 7
            }

        elif action_type == "DETECT_STALE_LEARNING_ARTIFACTS_CONFIRMED":
            plan["informational_confirmations"].append(entry)
            # Informational only, no change

        else:
            plan["warnings"].append(f"Unknown confirmed_action_type: {action_type}")
            plan["blocked_confirmations"].append(entry)

        if change:
            # Schema Guard
            if change["target_path"] not in STATE_PATH_ALLOWLIST:
                plan["warnings"].append(f"Proposed target path '{change['target_path']}' is not in allowlist. Blocking.")
                change["risk_level"] = "BLOCKED"
                change["apply_allowed_in_phase_7b"] = False
                plan["blocked_confirmations"].append(entry)
            
            if change["evidence_quality"] == "insufficient":
                plan["warnings"].append(f"Insufficient evidence for change to {change['target_path']}. Blocking.")
                change["risk_level"] = "BLOCKED"
                change["apply_allowed_in_phase_7b"] = False
                plan["blocked_confirmations"].append(entry)

            plan["proposed_state_changes"].append(change)

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
    
    plan = generate_plan(stronghold_dir, state, ledger)
    
    if "--json" in sys.argv:
        print(json.dumps(plan, indent=2))
        return

    print(f"Learning State Sync Plan v1 for: {state.get('title')}")
    print("=" * 60)
    print(f"Plan ID:      {plan['plan_id']}")
    print(f"Status:       {plan['mode']}")
    print(f"Sync Source:  {plan['source']}")
    print("-" * 60)
    print(f"Eligible Confirmations:    {len(plan['eligible_confirmations'])}")
    print(f"Informational:            {len(plan['informational_confirmations'])}")
    print(f"Blocked/Warned:           {len(plan['blocked_confirmations'])}")
    print("-" * 60)
    
    if plan["proposed_state_changes"]:
        print("PROPOSED STATE CHANGES:")
        for change in plan["proposed_state_changes"]:
            print(f"- {change['target_path']}:")
            print(f"  Current:  {change['current_value']}")
            print(f"  Proposed: {change['proposed_value']}")
            print(f"  Reason:   {change['reason']}")
            print(f"  Source:   {change['source_confirmation_id']}")
            print()
    else:
        print("No state changes proposed.")

    if plan["warnings"]:
        print("WARNINGS:")
        for w in plan["warnings"]:
            print(f"! {w}")
        print("-" * 60)

    if plan["blockers"]:
        print("BLOCKERS:")
        for b in plan["blockers"]:
            print(f"X {b}")
        print("-" * 60)

    print("\nDRY-RUN ONLY: no state.json changes were made.")
    print("State synchronization apply is not implemented.")

if __name__ == "__main__":
    main()
