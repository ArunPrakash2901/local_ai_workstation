#!/usr/bin/env python3
"""Learning next_learning_task Pointer Update Planner v1."""

import json
import sys
import os
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict

# Reuse helpers from state sync planner if possible, or redefine for independence
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

def extract_candidate_from_evidence(evidence_str):
    """Extract next_learning_task text from common evidence patterns."""
    if not evidence_str:
        return None
    match = re.search(r"next_learning_task:\s*(.*)", evidence_str)
    if match:
        return match.group(1).strip()
    return None

def extract_from_artifact(artifact_path: Path):
    """Safely extract next task candidate from small markdown confirmation artifacts."""
    if not artifact_path.is_file() or artifact_path.stat().st_size > 1024 * 50: # Max 50KB
        return None
    try:
        content = artifact_path.read_text(encoding="utf-8")
        # Look for explicit pointer declarations in the markdown
        match = re.search(r"next_learning_task:\s*(.*)", content)
        if match:
            return match.group(1).strip()
        # Fallback: look for "Confirmed: create a new study session for: <task>"
        match = re.search(r"Confirmed:.*study session for:\s*(.*)", content)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return None

def generate_pointer_plan(stronghold_dir: Path, state: dict, ledger: list):
    ws_home = Path(os.environ.get("WS_HOME", "D:\\_ai_brain" if os.name == 'nt' else "/mnt/d/_ai_brain"))
    timestamp = datetime.now().strftime('%Y%m%dT%H%M%SZ')
    plan_id = f"POINTER-PLAN-{timestamp}"
    
    current_next = state.get("next_learning_task")
    
    plan = {
        "pointer_plan_id": plan_id,
        "timestamp_utc": timestamp,
        "stronghold_id": stronghold_dir.name,
        "source": "learning_pointer_update_planner_v1",
        "mode": "DRY_RUN_ONLY",
        "state_path": str(stronghold_dir / "state.json"),
        "ledger_path": str(stronghold_dir / "learning_confirmations.jsonl"),
        "current_next_learning_task": current_next,
        "candidate_next_learning_task": None,
        "candidate_source": None,
        "candidate_status": "no_candidate",
        "source_confirmation_id": None,
        "source_action_id": None,
        "source_action_type": None,
        "source_artifact_path": None,
        "evidence": None,
        "evidence_quality": "insufficient",
        "risk_level": "MEDIUM",
        "blockers": [],
        "warnings": [],
        "evidence_notes": [],
        "requires_human_review": True,
        "can_apply_now": False,
        "apply_allowed_in_phase_9b": False
    }

    if ledger is None:
        plan["candidate_status"] = "blocked"
        plan["blockers"].append("Ledger file missing or unreadable.")
        return plan

    candidates = []
    
    # Priority rules:
    # 1. PROPOSE_NEXT_LESSON_CONFIRMED
    # 2. CREATE_STUDY_TASK_CONFIRMED
    # 3. MARK_REVIEW_NEEDED_CONFIRMED
    # 4. SUMMARIZE_SESSION_CONFIRMED
    # 5. ASSESS_ADVANCEMENT_READINESS_CONFIRMED
    
    priority_map = {
        "PROPOSE_NEXT_LESSON_CONFIRMED": 1,
        "CREATE_STUDY_TASK_CONFIRMED": 2,
        "MARK_REVIEW_NEEDED_CONFIRMED": 3,
        "SUMMARIZE_SESSION_CONFIRMED": 4,
        "ASSESS_ADVANCEMENT_READINESS_CONFIRMED": 5
    }

    for i, entry in enumerate(ledger):
        if "error" in entry:
            continue
            
        etype = entry.get("confirmed_action_type")
        priority = priority_map.get(etype, 99)
        if priority > 5:
            continue
            
        if entry.get("confirmation_status") != "CONFIRMED_APPLIED":
            continue
            
        candidate_text = extract_candidate_from_evidence(entry.get("evidence"))
        artifact_path_str = entry.get("artifact_path")
        artifact_path = normalize_path(artifact_path_str, ws_home) if artifact_path_str else None
        
        if not candidate_text and artifact_path:
             candidate_text = extract_from_artifact(artifact_path)
             if candidate_text:
                 plan["evidence_notes"].append(f"Extracted candidate from artifact {artifact_path.name}")

        if not candidate_text:
            # Fallback to title only if it's a high priority action
            if priority <= 2:
                title = entry.get("title", "")
                if "Propose Study Task:" in title:
                    candidate_text = title.split("Propose Study Task:")[1].strip()
                    plan["evidence_notes"].append("Inferred candidate from title.")
                elif "Propose Next Lesson:" in title:
                    candidate_text = title.split("Propose Next Lesson:")[1].strip()
                    plan["evidence_notes"].append("Inferred candidate from title.")

        if candidate_text:
            candidates.append({
                "text": candidate_text,
                "entry": entry,
                "priority": priority,
                "index": i,
                "artifact_path": artifact_path
            })

    if not candidates:
        plan["candidate_status"] = "no_candidate"
        plan["blockers"].append("No eligible confirmed actions found to derive next_learning_task.")
        return plan

    # Sort by priority (lower number is higher priority), then by chronological order (index)
    candidates.sort(key=lambda x: (x["priority"], -x["index"]))
    
    # Check for conflicts among top candidates
    best_candidate = candidates[0]
    top_priority = best_candidate["priority"]
    top_candidates = [c for c in candidates if c["priority"] == top_priority]
    
    # If there are multiple candidates at the top priority, and they have different texts, it's a conflict
    unique_texts = set(c["text"] for c in top_candidates)
    if len(unique_texts) > 1:
        plan["candidate_status"] = "conflict"
        plan["blockers"].append(f"MULTIPLE_CONFLICTING_CANDIDATES: Found {len(unique_texts)} different tasks at priority level {top_priority}.")
        return plan
    
    # Unambiguous best candidate
    plan["candidate_next_learning_task"] = best_candidate["text"]
    plan["candidate_source"] = best_candidate["entry"].get("confirmed_action_type")
    plan["source_confirmation_id"] = best_candidate["entry"].get("confirmation_id")
    plan["source_action_id"] = best_candidate["entry"].get("original_action_id")
    plan["source_action_type"] = best_candidate["entry"].get("confirmed_action_type")
    
    artifact_path_str = best_candidate["entry"].get("artifact_path")
    plan["source_artifact_path"] = artifact_path_str
    plan["evidence"] = best_candidate["entry"].get("evidence")
    
    # Validation logic
    artifact_path = best_candidate["artifact_path"]
    
    if not plan["candidate_next_learning_task"]:
        plan["blockers"].append("Extracted candidate is empty.")
        
    if artifact_path_str:
        if not artifact_path or not artifact_path.is_file():
            plan["blockers"].append(f"Source artifact file missing: {artifact_path_str}")
        elif not str(artifact_path.resolve()).startswith(str(stronghold_dir.resolve())):
            plan["blockers"].append(f"Source artifact is outside stronghold: {artifact_path}")
        else:
            if "Inferred" in str(plan["evidence_notes"]):
                plan["evidence_quality"] = "partial"
            else:
                plan["evidence_quality"] = "strong"
    else:
        plan["blockers"].append("Source confirmation is missing artifact_path.")

    # Safety checks
    unsafe_patterns = [r"\brm\s+", r"\bdel\s+", r"\bsudo\b", r"\bchmod\b", r"\bformat\s+[a-zA-Z]:"]
    for pattern in unsafe_patterns:
        if re.search(pattern, plan["candidate_next_learning_task"], re.IGNORECASE):
            plan["blockers"].append(f"Candidate contains potentially unsafe tool commands (matched {pattern}).")
        
    if "advancement" in plan["candidate_next_learning_task"].lower():
        plan["warnings"].append("Candidate mentions advancement; verify it does not skip steps.")

    # Idempotency Classification
    if plan["candidate_next_learning_task"] == current_next:
        plan["candidate_status"] = "already_synchronized"
        plan["warnings"].append("Candidate already matches current next_learning_task.")
    elif plan["blockers"]:
        plan["candidate_status"] = "blocked"
    else:
        plan["candidate_status"] = "eligible"

    if plan["candidate_status"] == "eligible" and plan["evidence_quality"] == "strong":
        plan["apply_allowed_in_phase_9b"] = True
    else:
        plan["apply_allowed_in_phase_9b"] = False

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
    
    plan = generate_pointer_plan(stronghold_dir, state, ledger)
    
    if is_json:
        print(json.dumps(plan, indent=2))
    else:
        print(f"Learning next_learning_task Pointer Update Plan v1 for: {state.get('title', stronghold_id)}")
        print("=" * 70)
        print(f"Plan ID:      {plan['pointer_plan_id']}")
        print(f"Status:       {plan['mode']}")
        print(f"Source:       {plan['source']}")
        print("-" * 70)
        print(f"Current Task:   {plan['current_next_learning_task']}")
        print(f"Candidate Task: {plan['candidate_next_learning_task']}")
        print(f"Derived From:   {plan['candidate_source']} ({plan['source_confirmation_id']})")
        print("-" * 70)
        print(f"Risk Level:       {plan['risk_level']}")
        print(f"Evidence Quality: {plan['evidence_quality']}")
        print(f"Phase 9B Eligible: {plan['apply_allowed_in_phase_9b']}")
        print("-" * 70)
        
        if plan["blockers"]:
            print("BLOCKERS:")
            for b in plan["blockers"]:
                print(f"X {b}")
            print("-" * 70)
            
        if plan["warnings"]:
            print("WARNINGS:")
            for w in plan["warnings"]:
                print(f"! {w}")
            print("-" * 70)

        print("\nDRY-RUN ONLY: next_learning_task was not modified.")
        print("Pointer apply is not implemented in Phase 9A.")

if __name__ == "__main__":
    main()
