#!/usr/bin/env python3
"""Validation for Learning State Synchronization Apply v1."""

import subprocess
import sys
import os
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
APPLY_PY = SCRIPTS_DIR / "learning_state_sync_apply.py"
SAMPLE_STRONGHOLD = "_test_isolation_fixture"
STRONGHOLD_DIR = ROOT / "strongholds" / "learning" / SAMPLE_STRONGHOLD

def run_cmd(cmd):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["WS_HOME"] = str(ROOT)
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        shell=True if os.name == 'nt' else False
    )
    return result

def test_mode_refusal():
    print("Testing: Refuses execution without mode or with both modes")
    # No mode
    res = run_cmd([sys.executable, str(APPLY_PY), SAMPLE_STRONGHOLD])
    if res.returncode != 0 and "Error: Must specify either --dry-run or --confirm-sync" in res.stdout:
        print("PASS (No mode refused)")
    else:
        print(f"FAIL: No mode check: {res.stdout} {res.stderr}")

    # Both modes
    res = run_cmd([sys.executable, str(APPLY_PY), SAMPLE_STRONGHOLD, "--dry-run", "--confirm-sync"])
    if res.returncode != 0 and "Error: Cannot use both --dry-run and --confirm-sync" in res.stdout:
        print("PASS (Both modes refused)")
    else:
        print(f"FAIL: Both modes check: {res.stdout} {res.stderr}")

def test_dry_run_non_mutation():
    print("Testing: --dry-run does NOT mutate state.json, create backup, or audit")
    state_file = STRONGHOLD_DIR / "state.json"
    mtime_pre = state_file.stat().st_mtime
    
    backup_dir = STRONGHOLD_DIR / "state_backups"
    backups_pre = list(backup_dir.glob("*.json")) if backup_dir.is_dir() else []
    
    audit_file = STRONGHOLD_DIR / "state_sync_audit.jsonl"
    audit_size_pre = audit_file.stat().st_size if audit_file.is_file() else 0
    
    run_cmd([sys.executable, str(APPLY_PY), SAMPLE_STRONGHOLD, "--dry-run"])
    
    mtime_post = state_file.stat().st_mtime
    backups_post = list(backup_dir.glob("*.json")) if backup_dir.is_dir() else []
    audit_size_post = audit_file.stat().st_size if audit_file.is_file() else 0
    
    if mtime_pre != mtime_post:
        print(f"FAIL: state.json mutated! {mtime_pre} -> {mtime_post}")
        return
    if len(backups_pre) != len(backups_post):
        print(f"FAIL: Backup created during dry-run!")
        return
    if audit_size_pre != audit_size_post:
        print(f"FAIL: Audit ledger appended during dry-run!")
        return
        
    print("PASS (Dry-run safety verified)")

def test_confirm_sync_with_isolation():
    print("Testing: --confirm-sync against isolation fixture")
    # We use a temp directory to avoid mutating the actual fixture in the repo
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir)
        fixture_dest = tmp_root / "strongholds" / "learning" / SAMPLE_STRONGHOLD
        fixture_dest.mkdir(parents=True)
        
        # Copy fixture contents
        shutil.copytree(STRONGHOLD_DIR, fixture_dest, dirs_exist_ok=True)
        
        # Need to fix absolute paths in learning_confirmations.jsonl if they exist
        # Wait, they are absolute paths in the fixture. I should fix them to point to the temp dir.
        ledger_file = fixture_dest / "learning_confirmations.jsonl"
        lines = ledger_file.read_text(encoding="utf-8").splitlines()
        new_lines = []
        for line in lines:
            entry = json.loads(line)
            if "artifact_path" in entry:
                # Replace D:\_ai_brain with tmp_root
                old_path = entry["artifact_path"]
                new_path = old_path.replace("D:\\_ai_brain", str(tmp_root))
                entry["artifact_path"] = new_path
            new_lines.append(json.dumps(entry))
        ledger_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

        # Run confirm-sync
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["WS_HOME"] = str(tmp_root)
        
        # We need to ensure SCRIPTS_DIR is still available, so we point WS_HOME but run script from original location
        res = subprocess.run(
            [sys.executable, str(APPLY_PY), SAMPLE_STRONGHOLD, "--confirm-sync"],
            capture_output=True,
            text=True,
            env=env,
            shell=True if os.name == 'nt' else False
        )
        
        if res.returncode != 0:
            print(f"FAIL: confirm-sync failed: {res.stdout} {res.stderr}")
            return
            
        print("PASS (Command executed)")
        
        # Verify state.json
        state = json.loads((fixture_dest / "state.json").read_text(encoding="utf-8"))
        
        # Expected changes based on ledger:
        # CREATE_STUDY_TASK_CONFIRMED -> learning_session_status = study_task_confirmed
        # SUMMARIZE_SESSION_CONFIRMED -> last_reported_at = 20260521T010323Z
        # MARK_REVIEW_NEEDED_CONFIRMED -> last_learning_decision = REVIEW_NEEDED
        
        if state.get("learning_session_status") == "study_task_confirmed":
            print("PASS (learning_session_status updated)")
        else:
            print(f"FAIL: learning_session_status not updated: {state.get('learning_session_status')}")

        if state.get("last_reported_at") == "20260521T010323Z":
            print("PASS (last_reported_at updated)")
        else:
            print(f"FAIL: last_reported_at not updated: {state.get('last_reported_at')}")

        if state.get("last_learning_decision") == "REVIEW_NEEDED":
            print("PASS (last_learning_decision updated)")
        else:
            print(f"FAIL: last_learning_decision not updated: {state.get('last_learning_decision')}")

        # Verify BLOCKED/HIGH risk not applied
        if state.get("current_state") == "AUDIT_TESTING":
            print("PASS (current_state NOT updated - HIGH risk blocked)")
        else:
            print(f"FAIL: current_state updated! {state.get('current_state')}")

        # Verify Backup
        backup_dir = fixture_dest / "state_backups"
        backups = list(backup_dir.glob("*.json"))
        if len(backups) == 1:
            print(f"PASS (One backup created: {backups[0].name})")
        else:
            print(f"FAIL: Expected 1 backup, found {len(backups)}")

        # Verify Audit
        audit_file = fixture_dest / "state_sync_audit.jsonl"
        if audit_file.is_file():
            audit_lines = audit_file.read_text(encoding="utf-8").splitlines()
            if len(audit_lines) == 1:
                audit_entry = json.loads(audit_lines[0])
                if audit_entry.get("confirmation_status") == "STATE_SYNC_APPLIED":
                    print("PASS (Audit record correct)")
                else:
                    print(f"FAIL: Audit entry status mismatch: {audit_entry.get('confirmation_status')}")
            else:
                print(f"FAIL: Expected 1 audit entry, found {len(audit_lines)}")
        else:
            print("FAIL: Audit file missing")

def test_json_error_purity():
    print("Testing: JSON purity on errors in --json mode")
    # Missing stronghold ID
    res = run_cmd([sys.executable, str(APPLY_PY), "--dry-run", "--json"])
    if res.returncode != 0:
        try:
            err = json.loads(res.stdout)
            if "error" in err and err.get("status") == "FAILED":
                print("PASS (JSON error returned for missing ID)")
            else:
                print(f"FAIL: Unexpected JSON structure: {res.stdout}")
        except json.JSONDecodeError:
            print(f"FAIL: Error output is not valid JSON: {res.stdout}")
    else:
        print("FAIL: Command succeeded without stronghold ID")

def test_path_traversal_refusal():
    print("Testing: Refuses path traversal attempts")
    res = run_cmd([sys.executable, str(APPLY_PY), "../../etc/passwd", "--dry-run"])
    if res.returncode != 0 and "Stronghold not found" in res.stdout:
        print("PASS (Path traversal attempt blocked by directory check)")
    else:
        print(f"FAIL: {res.stdout} {res.stderr}")

def main():
    print("Validating Learning State Synchronization Apply v1")
    print("==================================================")
    test_mode_refusal()
    test_json_error_purity()
    test_path_traversal_refusal()
    test_dry_run_non_mutation()
    test_confirm_sync_with_isolation()

if __name__ == "__main__":
    main()
