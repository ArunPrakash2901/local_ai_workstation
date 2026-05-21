#!/usr/bin/env python3
"""Validation for Learning Advancement Readiness Planner v1 Hardening Audit."""

import subprocess
import sys
import os
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
PLANNER_PY = SCRIPTS_DIR / "learning_advancement_readiness_planner.py"
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
    if res.returncode != 0:
        print(f"FAIL: Command failed: {res.stdout} {res.stderr}")
        return
    try:
        # Check for any leakage before or after JSON
        raw = res.stdout.strip()
        data = json.loads(raw)
        if "advancement_plan_id" in data:
            print("PASS")
        else:
            print(f"FAIL: Missing keys in JSON: {data.keys()}")
    except json.JSONDecodeError:
        print(f"FAIL: Invalid JSON or leakage: {res.stdout}")

def test_json_error_purity():
    print("Testing: JSON mode errors are pure JSON")
    res = run_cmd([sys.executable, str(PLANNER_PY), "non_existent_stronghold", "--dry-run", "--json"])
    try:
        data = json.loads(res.stdout)
        if data.get("status") == "FAILED" and "error" in data:
            print("PASS")
        else:
            print(f"FAIL: Unexpected error format: {data}")
    except json.JSONDecodeError:
        print(f"FAIL: Error output not pure JSON: {res.stdout}")

def test_state_non_mutation():
    print("Testing: Planner does NOT mutate state.json")
    state_file = STRONGHOLD_DIR / "state.json"
    mtime_pre = state_file.stat().st_mtime
    content_pre = state_file.read_text(encoding="utf-8")
    
    run_cmd([sys.executable, str(PLANNER_PY), SAMPLE_STRONGHOLD, "--dry-run"])
    
    mtime_post = state_file.stat().st_mtime
    content_post = state_file.read_text(encoding="utf-8")
    
    if mtime_pre == mtime_post and content_pre == content_post:
        print("PASS")
    else:
        print(f"FAIL: state.json mutated! mtime {mtime_pre} -> {mtime_post}")

def test_readiness_boundary():
    print("Testing: Advancement guards (apply_allowed_in_phase_10b=False)")
    res = run_cmd([sys.executable, str(PLANNER_PY), SAMPLE_STRONGHOLD, "--dry-run", "--json"])
    data = json.loads(res.stdout)
    
    if data.get("apply_allowed_in_phase_10b") is False and data.get("can_apply_now") is False:
        print("PASS")
    else:
        print(f"FAIL: Guards not enforced: {data.get('apply_allowed_in_phase_10b')}, {data.get('can_apply_now')}")

def test_readiness_score_bounds():
    print("Testing: Readiness score is between 0 and 100")
    res = run_cmd([sys.executable, str(PLANNER_PY), SAMPLE_STRONGHOLD, "--dry-run", "--json"])
    data = json.loads(res.stdout)
    score = data.get("readiness_score")
    if isinstance(score, (int, float)) and 0 <= score <= 100:
        print("PASS")
    else:
        print(f"FAIL: Score out of bounds or wrong type: {score}")

def test_malformed_ledger_safety():
    print("Testing: Malformed ledger handled safely")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir)
        fixture_dest = tmp_root / "strongholds" / "learning" / "malformed_test"
        fixture_dest.mkdir(parents=True)
        
        state = {"stronghold_id": "malformed_test", "next_learning_task": "Task"}
        (fixture_dest / "state.json").write_text(json.dumps(state))
        
        ledger_file = fixture_dest / "learning_confirmations.jsonl"
        ledger_file.write_text("not json\n{\"valid\": \"json\"}\n", encoding="utf-8")
        
        env = os.environ.copy()
        env["WS_HOME"] = str(tmp_root)
        res = subprocess.run([sys.executable, str(PLANNER_PY), "malformed_test", "--dry-run", "--json"], capture_output=True, text=True, env=env)
        
        data = json.loads(res.stdout)
        # Should have a blocker or warning about malformed ledger
        if any("malformed" in b.lower() for b in data.get("blockers", [])):
             print("PASS")
        else:
             print(f"FAIL: Malformed ledger not flagged in blockers: {data.get('blockers')}")

def test_unsupported_state_warning():
    print("Testing: Unsupported current_state creates warning")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir)
        fixture_dest = tmp_root / "strongholds" / "learning" / "state_test"
        fixture_dest.mkdir(parents=True)
        
        state = {"stronghold_id": "state_test", "current_state": "VERY_NEW_STATE"}
        (fixture_dest / "state.json").write_text(json.dumps(state))
        
        env = os.environ.copy()
        env["WS_HOME"] = str(tmp_root)
        res = subprocess.run([sys.executable, str(PLANNER_PY), "state_test", "--dry-run", "--json"], capture_output=True, text=True, env=env)
        
        data = json.loads(res.stdout)
        if any("not explicitly supported" in w.lower() for w in data.get("warnings", [])):
             print("PASS")
        else:
             print(f"FAIL: Unsupported state warning missing: {data.get('warnings')}")

def main():
    print("Validating Learning Advancement Readiness Planner v1 Hardening")
    print("===============================================================")
    test_dry_run_refusal()
    test_json_purity()
    test_json_error_purity()
    test_state_non_mutation()
    test_readiness_boundary()
    test_readiness_score_bounds()
    test_malformed_ledger_safety()
    test_unsupported_state_warning()

if __name__ == "__main__":
    main()
