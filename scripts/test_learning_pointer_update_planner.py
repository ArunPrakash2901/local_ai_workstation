#!/usr/bin/env python3
"""Validation for Learning next_learning_task Pointer Update Planner v1."""

import subprocess
import sys
import os
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
PLANNER_PY = SCRIPTS_DIR / "learning_pointer_update_planner.py"
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
    print("Testing: --json output is valid JSON only")
    res = run_cmd([sys.executable, str(PLANNER_PY), SAMPLE_STRONGHOLD, "--dry-run", "--json"])
    try:
        data = json.loads(res.stdout)
        if "pointer_plan_id" in data:
            print("PASS")
        else:
            print(f"FAIL: Missing keys in JSON: {data.keys()}")
    except json.JSONDecodeError:
        print(f"FAIL: Invalid JSON: {res.stdout}")

def test_state_non_mutation():
    print("Testing: Planner does NOT mutate state.json")
    state_file = STRONGHOLD_DIR / "state.json"
    mtime_pre = state_file.stat().st_mtime
    
    run_cmd([sys.executable, str(PLANNER_PY), SAMPLE_STRONGHOLD, "--dry-run"])
    
    mtime_post = state_file.stat().st_mtime
    if mtime_pre == mtime_post:
        print("PASS")
    else:
        print(f"FAIL: state.json mutated! {mtime_pre} -> {mtime_post}")

def test_conflict_detection():
    print("Testing: Conflict detection for multiple candidates")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir)
        fixture_dest = tmp_root / "strongholds" / "learning" / "conflict_test"
        fixture_dest.mkdir(parents=True)
        
        state = {"stronghold_id": "conflict_test", "next_learning_task": "Old Task"}
        (fixture_dest / "state.json").write_text(json.dumps(state))
        
        # Two conflicting confirmations at same priority
        ledger = [
            {"confirmation_id": "CONF-1", "original_action_id": "A1", "confirmed_action_type": "PROPOSE_NEXT_LESSON_CONFIRMED", "confirmation_status": "CONFIRMED_APPLIED", "evidence": "next_learning_task: New Task 1", "artifact_path": str(fixture_dest / "art1.md")},
            {"confirmation_id": "CONF-2", "original_action_id": "A2", "confirmed_action_type": "PROPOSE_NEXT_LESSON_CONFIRMED", "confirmation_status": "CONFIRMED_APPLIED", "evidence": "next_learning_task: New Task 2", "artifact_path": str(fixture_dest / "art2.md")}
        ]
        ledger_file = fixture_dest / "learning_confirmations.jsonl"
        with ledger_file.open("w") as f:
            for entry in ledger:
                f.write(json.dumps(entry) + "\n")
                
        (fixture_dest / "art1.md").touch()
        (fixture_dest / "art2.md").touch()
        
        env = os.environ.copy()
        env["WS_HOME"] = str(tmp_root)
        res = subprocess.run([sys.executable, str(PLANNER_PY), "conflict_test", "--dry-run", "--json"], capture_output=True, text=True, env=env)
        
        data = json.loads(res.stdout)
        if data.get("candidate_status") == "conflict" and "MULTIPLE_CONFLICTING_CANDIDATES" in str(data.get("blockers")):
             print("PASS (Conflict detected safely)")
        else:
             print(f"FAIL: Unexpected status: {data.get('candidate_status')} - {data.get('blockers')}")

def test_idempotency_classification():
    print("Testing: Idempotency classification")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir)
        fixture_dest = tmp_root / "strongholds" / "learning" / "idempotent_test"
        fixture_dest.mkdir(parents=True)
        
        state = {"stronghold_id": "idempotent_test", "next_learning_task": "Same Task"}
        (fixture_dest / "state.json").write_text(json.dumps(state))
        
        ledger = [
            {"confirmation_id": "CONF-1", "original_action_id": "A1", "confirmed_action_type": "PROPOSE_NEXT_LESSON_CONFIRMED", "confirmation_status": "CONFIRMED_APPLIED", "evidence": "next_learning_task: Same Task", "artifact_path": str(fixture_dest / "art1.md")}
        ]
        ledger_file = fixture_dest / "learning_confirmations.jsonl"
        with ledger_file.open("w") as f:
            for entry in ledger:
                f.write(json.dumps(entry) + "\n")
                
        (fixture_dest / "art1.md").touch()
        
        env = os.environ.copy()
        env["WS_HOME"] = str(tmp_root)
        res = subprocess.run([sys.executable, str(PLANNER_PY), "idempotent_test", "--dry-run", "--json"], capture_output=True, text=True, env=env)
        
        data = json.loads(res.stdout)
        if data.get("candidate_status") == "already_synchronized" and not data.get("apply_allowed_in_phase_9b"):
             print("PASS (Correctly classified as already_synchronized)")
        else:
             print(f"FAIL: Unexpected status: {data.get('candidate_status')}")

def main():
    print("Validating Learning next_learning_task Pointer Update Planner v1")
    print("===============================================================")
    test_dry_run_refusal()
    test_json_purity()
    test_state_non_mutation()
    test_conflict_detection()
    test_idempotency_classification()

if __name__ == "__main__":
    main()
