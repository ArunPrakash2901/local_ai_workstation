#!/usr/bin/env python3
"""Learning Human Advancement Review Packet v1."""

import json
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

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

def run_planner(script_name, stronghold_id, ws_home):
    """Run a planner script in dry-run JSON mode."""
    script_path = ws_home / "scripts" / script_name
    if not script_path.is_file():
        return {"error": f"Script {script_name} not found."}
    try:
        res = subprocess.run(
            [sys.executable, str(script_path), stronghold_id, "--dry-run", "--json"],
            capture_output=True,
            text=True,
            env={"WS_HOME": str(ws_home), "PYTHONDONTWRITEBYTECODE": "1"}
        )
        if res.returncode == 0:
            return json.loads(res.stdout)
        else:
            return {"error": f"Planner {script_name} failed.", "details": res.stdout + res.stderr}
    except Exception as e:
        return {"error": str(e)}

def generate_packet_data(stronghold_dir: Path):
    ws_home = Path(os.environ.get("WS_HOME", "D:\\_ai_brain" if os.name == 'nt' else "/mnt/d/_ai_brain"))
    timestamp = datetime.now().strftime('%Y%m%dT%H%M%SZ')
    packet_id = f"ADV-PACKET-{timestamp}"
    
    state = load_json(stronghold_dir / "state.json")
    if not state:
        return {"error": "Could not load state.json"}

    adv_plan = run_planner("learning_advancement_readiness_planner.py", stronghold_dir.name, ws_home)
    ptr_plan = run_planner("learning_pointer_update_planner.py", stronghold_dir.name, ws_home)
    
    audit_file = stronghold_dir / "state_sync_audit.jsonl"
    audit = load_ledger(audit_file)
    latest_sync = audit[-1] if audit else {}

    ledger_file = stronghold_dir / "learning_confirmations.jsonl"
    ledger = load_ledger(ledger_file)
    recent_confirmations = [e.get("confirmed_action_type") for e in ledger[-5:]] if ledger else []

    packet_data = {
        "packet_id": packet_id,
        "timestamp_utc": timestamp,
        "stronghold_id": stronghold_dir.name,
        "source": "learning_advancement_review_packet_v1",
        "mode": "DRY_RUN_ONLY",
        "current_state": state.get("current_state"),
        "learning_session_status": state.get("learning_session_status"),
        "next_learning_task": state.get("next_learning_task"),
        "state_mtime": datetime.fromtimestamp(os.path.getmtime(stronghold_dir / "state.json")).isoformat(),
        "advancement_readiness": adv_plan,
        "pointer_status": ptr_plan,
        "state_sync_status": {
            "latest_sync_id": latest_sync.get("sync_id"),
            "timestamp_utc": latest_sync.get("timestamp_utc"),
            "confirmation_status": latest_sync.get("confirmation_status"),
            "applied_count": len(latest_sync.get("applied_changes", [])),
            "skipped_count": len(latest_sync.get("skipped_changes", [])),
            "blocked_count": len(latest_sync.get("blocked_changes", [])),
            "backup_path": latest_sync.get("backup_path")
        },
        "confirmation_evidence": {
            "total_confirmations": len(ledger) if ledger else 0,
            "recent_types": recent_confirmations,
            "malformed_count": len([e for e in ledger if "error" in e]) if ledger else 0
        },
        "required_human_checks": [
            "Verify the learner has completed the current task.",
            f"Verify the '{state.get('next_learning_task')}' task is actually done.",
            "Verify outputs or artifacts exist.",
            "Verify no unresolved blockers remain.",
            f"Decide whether current_state should remain {state.get('current_state')}.",
            "Decide whether a future advancement phase is appropriate."
        ]
    }
    return packet_data

def format_markdown(data):
    md = f"""# Advancement Review Packet: {data['stronghold_id']}

- Packet ID: {data['packet_id']}
- Timestamp UTC: {data['timestamp_utc']}
- Source: {data['source']}
- Mode: {data['mode']}

## 1. Current State
- **State**: {data['current_state']}
- **Session Status**: {data['learning_session_status']}
- **Next Task**: {data['next_learning_task']}
- **State.json Mtime**: {data['state_mtime']}

## 2. Advancement Readiness
- **Status**: {data['advancement_readiness'].get('readiness_status', 'N/A')}
- **Score**: {data['advancement_readiness'].get('readiness_score', 'N/A')}/100
- **Evidence Quality**: {data['advancement_readiness'].get('evidence_quality', 'N/A')}
- **Proposed Future State**: {data['advancement_readiness'].get('proposed_future_state', 'N/A')} (ADVISORY)
- **Risk Level**: {data['advancement_readiness'].get('risk_level', 'HIGH')}
- **Apply Allowed (v1)**: {data['advancement_readiness'].get('apply_allowed_in_phase_10b', False)}

## 3. Pointer Status
- **Current Pointer**: {data['pointer_status'].get('current_next_learning_task', 'N/A')}
- **Candidate Pointer**: {data['pointer_status'].get('candidate_next_learning_task', 'N/A')}
- **Status**: {data['pointer_status'].get('candidate_status', 'N/A')}
- **Eligible 9B**: {data['pointer_status'].get('apply_allowed_in_phase_9b', False)}

## 4. State Sync Status
- **Latest Sync ID**: {data['state_sync_status']['latest_sync_id']}
- **Timestamp**: {data['state_sync_status']['timestamp_utc']}
- **Status**: {data['state_sync_status']['confirmation_status']}
- **Changes**: {data['state_sync_status']['applied_count']} applied, {data['state_sync_status']['skipped_count']} skipped, {data['state_sync_status']['blocked_count']} blocked
- **Backup**: {data['state_sync_status']['backup_path']}

## 5. Confirmation Evidence
- **Total Confirmations**: {data['confirmation_evidence']['total_confirmations']}
- **Recent Types**: {', '.join(data['confirmation_evidence']['recent_types'])}
- **Malformed Ledger Entries**: {data['confirmation_evidence']['malformed_count']}

## 6. Required Human Checks
"""
    for check in data['required_human_checks']:
        md += f"- [ ] {check}\n"

    md += """
## 7. Safety Boundary
- This packet is **ADVISORY**.
- Advancement remains **MANUAL**.
- `current_state` was **NOT** modified.
- `next_learning_task` was **NOT** modified.
- No state synchronization was run.
- No advancement apply exists in this phase.
"""
    return md

def main():
    if "--dry-run" not in sys.argv and "--create-packet" not in sys.argv:
        print("Error: Must specify either --dry-run or --create-packet.")
        sys.exit(1)
    
    if "--dry-run" in sys.argv and "--create-packet" in sys.argv:
        print("Error: Cannot use both --dry-run and --create-packet.")
        sys.exit(1)

    is_json = "--json" in sys.argv
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

    default_ws_home = "D:\\_ai_brain" if os.name == 'nt' else "/mnt/d/_ai_brain"
    ws_home = Path(os.environ.get("WS_HOME", default_ws_home))
    stronghold_dir = ws_home / "strongholds" / "learning" / stronghold_id
    
    if not stronghold_dir.is_dir():
        if is_json:
            print(json.dumps({"error": f"Stronghold not found at {stronghold_dir}", "status": "FAILED"}))
        else:
            print(f"Error: Stronghold not found at {stronghold_dir}")
        sys.exit(1)

    data = generate_packet_data(stronghold_dir)
    if "error" in data:
        if is_json:
            print(json.dumps(data))
        else:
            print(f"Error: {data['error']}")
        sys.exit(1)

    if "--create-packet" in sys.argv:
        data["mode"] = "CREATE_PACKET"
        packet_dir = stronghold_dir / "review_packets"
        packet_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{data['timestamp_utc']}_advancement_review_packet.md"
        packet_path = packet_dir / filename
        
        md_content = format_markdown(data)
        packet_path.write_text(md_content, encoding="utf-8")
        
        if is_json:
            print(json.dumps({"status": "SUCCESS", "packet_path": str(packet_path), "packet_id": data['packet_id']}))
        else:
            print(f"Advancement review packet created: {packet_path}")
    else:
        # Dry run
        if is_json:
            print(json.dumps(data, indent=2))
        else:
            print(format_markdown(data))
            print("\nDRY-RUN ONLY: No files were written. current_state was not modified.")

if __name__ == "__main__":
    main()
