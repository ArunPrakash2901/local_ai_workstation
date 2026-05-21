#!/usr/bin/env python3
"""Validation for Learning State Synchronization Planner v1."""

import subprocess
import sys
import os
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
PLANNER_PY = SCRIPTS_DIR / "learning_state_sync_planner.py"
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

def test_dry_run_refusal():
    print("Testing: Refuses execution without --dry-run")
    res = run_cmd([sys.executable, str(PLANNER_PY), SAMPLE_STRONGHOLD])
    if res.returncode != 0 and "Error: This tool currently only supports --dry-run mode." in res.stdout:
        print("PASS")
    else:
        print(f"FAIL: {res.stdout} {res.stderr}")

def test_json_purity():
    print("Testing: JSON purity in --json mode")
    res = run_cmd([sys.executable, str(PLANNER_PY), SAMPLE_STRONGHOLD, "--dry-run", "--json"])
    if res.returncode == 0:
        try:
            plan = json.loads(res.stdout)
            if plan.get("source") == "learning_state_sync_planner_v1":
                print("PASS (Valid JSON returned)")
            else:
                print(f"FAIL: Unexpected plan structure: {res.stdout[:100]}")
        except json.JSONDecodeError:
            print(f"FAIL: Output is not valid JSON: {res.stdout[:100]}")
    else:
        print(f"FAIL: {res.stdout} {res.stderr}")

def test_state_non_mutation():
    print("Testing: state.json is NOT mutated")
    state_file = STRONGHOLD_DIR / "state.json"
    mtime_pre = state_file.stat().st_mtime
    
    run_cmd([sys.executable, str(PLANNER_PY), SAMPLE_STRONGHOLD, "--dry-run"])
    
    mtime_post = state_file.stat().st_mtime
    if mtime_pre == mtime_post:
        print("PASS (mtime unchanged)")
    else:
        print(f"FAIL: mtime changed! {mtime_pre} -> {mtime_post}")

def test_plan_contents():
    print("Testing: Plan identifies eligible confirmations and enforces hardening")
    res = run_cmd([sys.executable, str(PLANNER_PY), SAMPLE_STRONGHOLD, "--dry-run", "--json"])
    if res.returncode == 0:
        plan = json.loads(res.stdout)
        eligible = plan.get("eligible_confirmations", [])
        changes = plan.get("proposed_state_changes", [])
        
        if len(eligible) > 0:
             print(f"PASS (Found {len(eligible)} eligible actions)")
        else:
             print("FAIL: No eligible actions found in isolation fixture.")
             
        if plan.get("can_apply_now") is False:
             print("PASS (can_apply_now is False)")
        else:
             print("FAIL: can_apply_now should be False")

        for change in changes:
            # Verify required hardening fields
            if "risk_level" not in change:
                print(f"FAIL: Missing risk_level in change {change.get('target_path')}")
                return
            if "evidence_quality" not in change:
                print(f"FAIL: Missing evidence_quality in change {change.get('target_path')}")
                return
            if "apply_allowed_in_phase_7b" not in change:
                print(f"FAIL: Missing apply_allowed_in_phase_7b in change {change.get('target_path')}")
                return
            
            if change.get("apply_allowed_in_v1") is not False:
                print(f"FAIL: Change {change['target_path']} marks apply_allowed_in_v1=True")
                return
            
            # Verify schema awareness
            target = change.get("target_path")
            allowed = {
                "state.learning_session_status",
                "state.last_reported_at",
                "state.next_learning_task",
                "state.last_learning_decision",
                "state.current_state",
            }
            if target not in allowed:
                print(f"FAIL: target_path {target} is not in allowlist")
                return
                
        print("PASS (Hardening fields and schema awareness verified)")
    else:
        print(f"FAIL: {res.stdout} {res.stderr}")

def main():
    print("Validating Learning State Synchronization Planner v1")
    print("==================================================")
    test_dry_run_refusal()
    test_json_purity()
    test_state_non_mutation()
    test_plan_contents()

if __name__ == "__main__":
    main()
