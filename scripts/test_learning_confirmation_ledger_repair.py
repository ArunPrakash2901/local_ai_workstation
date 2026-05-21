#!/usr/bin/env python3
"""Validation for Learning Confirmation Ledger Repair Tool v1."""

import subprocess
import sys
import os
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
REPAIR_PY = SCRIPTS_DIR / "learning_confirmation_ledger_repair.py"
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
    res = run_cmd([sys.executable, str(REPAIR_PY), SAMPLE_STRONGHOLD])
    if res.returncode != 0 and "Error: Must specify either --dry-run or --repair-ledger" in res.stdout:
        print("PASS (No mode refused)")
    else:
        print(f"FAIL: No mode check: {res.stdout} {res.stderr}")

    # Both modes
    res = run_cmd([sys.executable, str(REPAIR_PY), SAMPLE_STRONGHOLD, "--dry-run", "--repair-ledger"])
    if res.returncode != 0 and "Error: Cannot use both --dry-run and --repair-ledger" in res.stdout:
        print("PASS (Both modes refused)")
    else:
        print(f"FAIL: Both modes check: {res.stdout} {res.stderr}")

def test_dry_run_non_mutation():
    print("Testing: --dry-run does NOT mutate ledger or state.json")
    ledger_file = STRONGHOLD_DIR / "learning_confirmations.jsonl"
    mtime_pre = ledger_file.stat().st_mtime
    
    state_file = STRONGHOLD_DIR / "state.json"
    state_mtime_pre = state_file.stat().st_mtime
    
    run_cmd([sys.executable, str(REPAIR_PY), SAMPLE_STRONGHOLD, "--dry-run"])
    
    mtime_post = ledger_file.stat().st_mtime
    state_mtime_post = state_file.stat().st_mtime
    
    if mtime_pre != mtime_post:
        print(f"FAIL: ledger mutated! {mtime_pre} -> {mtime_post}")
        return
    if state_mtime_pre != state_mtime_post:
        print(f"FAIL: state.json mutated! {state_mtime_pre} -> {state_mtime_post}")
        return
        
    print("PASS (Dry-run safety verified)")

def test_repair_with_isolation():
    print("Testing: --repair-ledger against isolation fixture")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir)
        fixture_dest = tmp_root / "strongholds" / "learning" / SAMPLE_STRONGHOLD
        fixture_dest.mkdir(parents=True)
        
        # Copy fixture contents
        shutil.copytree(STRONGHOLD_DIR, fixture_dest, dirs_exist_ok=True)
        
        # Manually break an entry in the ledger (remove artifact_path)
        ledger_file = fixture_dest / "learning_confirmations.jsonl"
        lines = ledger_file.read_text(encoding="utf-8").splitlines()
        broken_entries = []
        for line in lines:
            entry = json.loads(line)
            if "artifact_path" in entry:
                entry.pop("artifact_path")
            broken_entries.append(json.dumps(entry))
        ledger_file.write_text("\n".join(broken_entries) + "\n", encoding="utf-8")

        # Run repair
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["WS_HOME"] = str(tmp_root)
        
        res = subprocess.run(
            [sys.executable, str(REPAIR_PY), SAMPLE_STRONGHOLD, "--repair-ledger"],
            capture_output=True,
            text=True,
            env=env,
            shell=True if os.name == 'nt' else False
        )
        
        if res.returncode != 0:
            print(f"FAIL: repair-ledger failed: {res.stdout} {res.stderr}")
            return
            
        print("PASS (Command executed)")
        
        # Verify ledger
        new_lines = ledger_file.read_text(encoding="utf-8").splitlines()
        repaired_all = True
        for line in new_lines:
            entry = json.loads(line)
            if not entry.get("artifact_path"):
                repaired_all = False
                print(f"FAIL: Entry {entry.get('confirmation_id')} still missing artifact_path")
        
        if repaired_all:
            print("PASS (All entries repaired)")
            
        # Verify backup
        backup_dir = fixture_dest / "ledger_backups"
        backups = list(backup_dir.glob("*.jsonl"))
        if len(backups) == 1:
            print(f"PASS (One backup created: {backups[0].name})")
        else:
            print(f"FAIL: Expected 1 backup, found {len(backups)}")
            
        # Verify audit
        audit_file = fixture_dest / "ledger_repair_audit.jsonl"
        if audit_file.is_file():
            audit_lines = audit_file.read_text(encoding="utf-8").splitlines()
            if len(audit_lines) == 1:
                print("PASS (Audit record appended)")
            else:
                print(f"FAIL: Expected 1 audit record, found {len(audit_lines)}")
        else:
            print("FAIL: Audit file missing")
            
        # Verify state.json was NOT modified
        state_file = fixture_dest / "state.json"
        # Since we just copied it, we check if it's still the same content
        original_state = (STRONGHOLD_DIR / "state.json").read_text(encoding="utf-8")
        current_state = state_file.read_text(encoding="utf-8")
        if original_state == current_state:
            print("PASS (state.json content unchanged)")
        else:
            print("FAIL: state.json content changed!")

def main():
    print("Validating Learning Confirmation Ledger Repair v1")
    print("==================================================")
    test_mode_refusal()
    test_dry_run_non_mutation()
    test_repair_with_isolation()

if __name__ == "__main__":
    main()
