#!/usr/bin/env python3
"""Learning Confirmation Core v1."""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from learning_action_pack import generate_actions, load_state, LearningAction
except ImportError:
    # Fallback if imports fail in certain environments
    print("Error: Could not import learning_action_pack. Ensure it is in the same directory.")
    sys.exit(1)

def confirm_action(stronghold_dir: Path, action_id: str, dry_run: bool = True):
    state = load_state(stronghold_dir)
    if not state:
        return {"error": "Could not load state.json", "status": "FAILED"}
    
    actions = generate_actions(stronghold_dir, state)
    target_action = None
    for a in actions:
        if a.action_id == action_id:
            target_action = a
            break
            
    if not target_action:
        return {"error": f"Action ID {action_id} not found in current action pack.", "status": "FAILED"}
        
    if target_action.status != "DRY_RUN_ONLY" or not target_action.requires_confirmation:
        return {"error": f"Action {action_id} is not in a confirmable state.", "status": "FAILED"}
        
    confirmed_type = target_action.action_type.replace("_DRY_RUN", "_CONFIRMED")
    timestamp = datetime.now().strftime('%Y%m%dT%H%M%SZ')
    confirmation_id = f"CONF-{timestamp}-{action_id}"
    
    confirmed_effect = target_action.proposed_effect.replace("Would ", "Confirmed: ")
    
    artifact_filename = f"{timestamp}_{action_id}_{confirmed_type}.md"
    artifact_path = stronghold_dir / "confirmed_actions" / artifact_filename

    # Audit record
    audit_record = {
        "confirmation_id": confirmation_id,
        "timestamp_utc": timestamp,
        "stronghold_id": stronghold_dir.name,
        "original_action_id": target_action.action_id,
        "original_action_type": target_action.action_type,
        "confirmed_action_type": confirmed_type,
        "title": target_action.title,
        "rationale": target_action.rationale,
        "proposed_effect": target_action.proposed_effect,
        "confirmed_effect": confirmed_effect,
        "safety_class": target_action.safety_class,
        "operator_confirmation_required": True,
        "confirmation_status": "CONFIRMED_APPLIED" if not dry_run else "DRY_RUN_PREVIEW",
        "source": "learning_confirmation_core_v1",
        "evidence": target_action.evidence,
        "warnings": target_action.warnings,
        "artifact_path": str(artifact_path)
    }
    
    # Duplicate check
    ledger_path = stronghold_dir / "learning_confirmations.jsonl"
    if ledger_path.is_file():
        try:
            with ledger_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        if (entry.get("original_action_id") == action_id and 
                            entry.get("confirmation_status") == "CONFIRMED_APPLIED"):
                            return {"error": f"Action {action_id} already confirmed in ledger.", "status": "FAILED"}
        except Exception:
            pass

    if dry_run:
        return {
            "status": "DRY_RUN_PREVIEW",
            "message": f"PREVIEW: Would confirm action {action_id} ({target_action.title})",
            "proposed_audit_record": audit_record,
            "artifact_path": str(artifact_path)
        }
        
    # Actual confirmation
    # 1. Ensure directories exist
    confirmed_dir = stronghold_dir / "confirmed_actions"
    confirmed_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Write artifact
    artifact_content = f"""# {confirmed_type}: {target_action.title}

- Confirmation ID: {confirmation_id}
- Timestamp: {timestamp}
- Original Action ID: {target_action.action_id}
- Safety Class: {target_action.safety_class}

## Rationale
{target_action.rationale}

## Confirmed Effect
{confirmed_effect}

## Evidence
{target_action.evidence}

---
*Confirmed via Learning Confirmation Core v1*
"""
    artifact_path.write_text(artifact_content, encoding="utf-8", newline="\n")
    
    # 3. Append to ledger
    ledger_path = stronghold_dir / "learning_confirmations.jsonl"
    with ledger_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(audit_record) + "\n")
        
    return {
        "status": "CONFIRMED_APPLIED",
        "message": f"Successfully confirmed action {action_id}",
        "audit_record": audit_record,
        "artifact_path": str(artifact_path)
    }

def main():
    args = sys.argv[1:]
    
    stronghold_id = None
    action_id = None
    dry_run = False
    confirm = False
    json_mode = "--json" in args
    
    # Simple argument parsing
    for i, arg in enumerate(args):
        if arg == "--action-id" and i + 1 < len(args):
            action_id = args[i+1]
        elif arg == "--dry-run":
            dry_run = True
        elif arg == "--confirm":
            confirm = True
        elif not arg.startswith("-"):
            if stronghold_id is None:
                stronghold_id = arg
                
    if not stronghold_id or not action_id:
        msg = "Usage: ws learning-confirm <stronghold_id> --action-id <ACTION_ID> [--dry-run | --confirm]"
        if json_mode:
            print(json.dumps({"error": msg}))
        else:
            print(msg)
        sys.exit(1)
        
    if dry_run and confirm:
        msg = "Error: Cannot specify both --dry-run and --confirm"
        if json_mode:
            print(json.dumps({"error": msg}))
        else:
            print(msg)
        sys.exit(1)
        
    if not dry_run and not confirm:
        msg = "Error: Must specify either --dry-run or --confirm"
        if json_mode:
            print(json.dumps({"error": msg}))
        else:
            print(msg)
        sys.exit(1)

    ws_home = Path(os.environ.get("WS_HOME", "/mnt/d/_ai_brain"))
    stronghold_dir = ws_home / "strongholds" / "learning" / stronghold_id
    
    if not stronghold_dir.is_dir():
        msg = f"Error: Stronghold {stronghold_id} not found."
        if json_mode:
            print(json.dumps({"error": msg}))
        else:
            print(msg)
        sys.exit(1)
        
    result = confirm_action(stronghold_dir, action_id, dry_run=dry_run)
    
    if json_mode:
        print(json.dumps(result, indent=2))
    else:
        if "error" in result:
            print(f"FAILED: {result['error']}")
            sys.exit(1)
        else:
            print(result["message"])
            if dry_run:
                print("\nProposed Audit Record:")
                print(json.dumps(result["proposed_audit_record"], indent=2))
                print(f"\nTarget Artifact Path: {result['artifact_path']}")
            else:
                print(f"Artifact created: {result['artifact_path']}")
                print(f"Ledger updated: {stronghold_dir}/learning_confirmations.jsonl")

if __name__ == "__main__":
    main()
