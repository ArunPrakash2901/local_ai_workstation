#!/usr/bin/env python3
"""Validation for Learning Confirmation Core v1."""

import subprocess
import sys
import os
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
CONFIRM_PY = SCRIPTS_DIR / "learning_confirmation_core.py"
ACTION_PACK_PY = SCRIPTS_DIR / "learning_action_pack.py"
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

def test_dry_run_preview():
    print("Testing: Dry-run confirmation preview")
    # First get an action pack
    res = run_cmd([sys.executable, str(ACTION_PACK_PY), SAMPLE_STRONGHOLD, "--dry-run", "--json"])
    actions = json.loads(res.stdout)
    
    # Read ledger to find unconfirmed action
    ledger_path = STRONGHOLD_DIR / "learning_confirmations.jsonl"
    confirmed_ids = set()
    if ledger_path.is_file():
        with open(ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if entry.get("confirmation_status") == "CONFIRMED_APPLIED":
                        confirmed_ids.add(entry.get("original_action_id"))
    
    target_action = None
    for a in actions:
        if a["action_id"] not in confirmed_ids:
            target_action = a
            break
            
    if not target_action:
        print("SKIP: No unconfirmed actions available for preview test.")
        return

    action_id = target_action["action_id"]
    res = run_cmd([sys.executable, str(CONFIRM_PY), SAMPLE_STRONGHOLD, "--action-id", action_id, "--dry-run", "--json"])
    if res.returncode == 0:
        data = json.loads(res.stdout)
        if data["status"] == "DRY_RUN_PREVIEW" and "proposed_audit_record" in data:
            print(f"PASS (Previewed {action_id})")
        else:
            print(f"FAIL: Unexpected response: {res.stdout}")
    else:
        print(f"FAIL: {res.stdout} {res.stderr}")

def test_confirmation_apply():
    print("Testing: Confirmation apply (durable write)")
    # Get action pack
    res = run_cmd([sys.executable, str(ACTION_PACK_PY), SAMPLE_STRONGHOLD, "--dry-run", "--json"])
    actions = json.loads(res.stdout)

    # Read ledger
    ledger_path = STRONGHOLD_DIR / "learning_confirmations.jsonl"
    confirmed_ids = set()
    if ledger_path.is_file():
        with open(ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if entry.get("confirmation_status") == "CONFIRMED_APPLIED":
                        confirmed_ids.add(entry.get("original_action_id"))
    
    target_action = None
    for a in actions:
        if a["action_id"] not in confirmed_ids:
            target_action = a
            break
            
    if not target_action:
        print("SKIP: No unconfirmed actions available for apply test.")
        return

    action_id = target_action["action_id"]

    # Run confirm
    res = run_cmd([sys.executable, str(CONFIRM_PY), SAMPLE_STRONGHOLD, "--action-id", action_id, "--confirm", "--json"])
    if res.returncode == 0:
        data = json.loads(res.stdout)
        if data["status"] == "CONFIRMED_APPLIED":
            artifact_path = Path(data["artifact_path"])
            
            if artifact_path.is_file() and ledger_path.is_file():
                # Verify ledger record has artifact_path
                with open(ledger_path, "r", encoding="utf-8") as f:
                    last_line = f.readlines()[-1]
                    entry = json.loads(last_line)
                    if "artifact_path" in entry and entry["artifact_path"] == str(artifact_path):
                        print("PASS (Artifact, ledger, and path record verified)")
                    else:
                        print(f"FAIL: ledger record missing or wrong artifact_path: {entry.get('artifact_path')}")
            else:
                print(f"FAIL: Files not found. Artifact: {artifact_path.exists()}, Ledger: {ledger_path.exists()}")
        else:
            print(f"FAIL: Unexpected response: {res.stdout}")
    else:
        print(f"FAIL: {res.stdout} {res.stderr}")


def test_invalid_action_id():
    print("Testing: Invalid action_id failure")
    res = run_cmd([sys.executable, str(CONFIRM_PY), SAMPLE_STRONGHOLD, "--action-id", "INVALID_ID", "--dry-run", "--json"])
    if res.returncode != 0 or "error" in json.loads(res.stdout):
        print("PASS (Failed as expected)")
    else:
        print(f"FAIL: Should have failed for invalid action_id")

def test_missing_mode():
    print("Testing: Missing --dry-run or --confirm refusal")
    # Using a deterministic ID format for the test
    res = run_cmd([sys.executable, str(CONFIRM_PY), SAMPLE_STRONGHOLD, "--action-id", "LT-12345678"])
    if res.returncode != 0 and "Error: Must specify either --dry-run or --confirm" in res.stdout:
        print("PASS")
    else:
        print(f"FAIL: {res.stdout}")

def main():
    print("Validating Learning Confirmation Core v1")
    print("==========================================")
    test_dry_run_preview()
    test_invalid_action_id()
    test_missing_mode()
    test_confirmation_apply()

if __name__ == "__main__":
    main()
