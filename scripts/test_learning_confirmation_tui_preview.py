#!/usr/bin/env python3
"""Validation for Learning Confirmation TUI Preview Interactivity v1."""

import json
import sys
import os
import subprocess
from pathlib import Path
from dataclasses import dataclass, field

# Mocking enough of the environment to test run_dry_run_preview safety
ROOT = Path(__file__).resolve().parents[1]
WS_HOME = ROOT

@dataclass
class LearningStronghold:
    id: str
    title: str = "Test Stronghold"

def run_dry_run_preview_internal(sh, action_id):
    # This is a copy of the logic in tui/app.py for testing
    command_args = ["learning-confirm", sh.id, "--action-id", action_id, "--dry-run", "--json"]
    
    # HARD GUARD Validation
    for arg in command_args:
        if "--confirm" in arg:
            return {"error": "CRITICAL: --confirm detected in preview command. Execution blocked.", "status": "BLOCKED"}
    
    # We don't actually run subprocess here in the test to avoid side effects, 
    # but we test the GUARD logic.
    return {"status": "GUARD_PASSED", "args": command_args}

def test_preview_safety_guard():
    print("Testing: TUI preview safety guard against --confirm")
    sh = LearningStronghold(id="test-sh")
    
    # Normal case
    res = run_dry_run_preview_internal(sh, "LT-01")
    if res.get("status") == "GUARD_PASSED":
        print("PASS (Normal preview allowed)")
    else:
        print(f"FAIL: Normal preview blocked: {res}")

    # Malicious case: action_id containing --confirm
    res = run_dry_run_preview_internal(sh, "LT-01 --confirm")
    if res.get("status") == "BLOCKED" and "CRITICAL" in res.get("error"):
        print("PASS (Attempted --confirm injection blocked)")
    else:
        print(f"FAIL: --confirm injection was NOT blocked: {res}")

    # Malicious case: stronghold_id containing --confirm
    sh_bad = LearningStronghold(id="test-sh --confirm")
    res = run_dry_run_preview_internal(sh_bad, "LT-01")
    if res.get("status") == "BLOCKED" and "CRITICAL" in res.get("error"):
        print("PASS (Stronghold ID --confirm injection blocked)")
    else:
        print(f"FAIL: Stronghold ID --confirm injection was NOT blocked: {res}")

def test_actual_preview_call():
    # Only if stronghold exists
    sample_sh = "fine-tuning-small-open-source-models"
    if not (ROOT / "strongholds" / "learning" / sample_sh).is_dir():
        print(f"SKIP: Sample stronghold {sample_sh} not found.")
        return

    print("Testing: Actual preview call for sample stronghold")
    # Get a real action ID
    pack_script = ROOT / "scripts" / "learning_action_pack.py"
    res = subprocess.run([sys.executable, str(pack_script), sample_sh, "--dry-run", "--json"], 
                         capture_output=True, text=True, env={"WS_HOME": str(ROOT)})
    if res.returncode != 0:
        print(f"FAIL: Could not get action pack: {res.stderr}")
        return
    
    actions = json.loads(res.stdout)
    if not actions:
        print("SKIP: No actions in pack.")
        return
    
    action_id = actions[0]["action_id"]
    
    # Run the real preview logic (via subprocess to the core script)
    confirm_script = ROOT / "scripts" / "learning_confirmation_core.py"
    res = subprocess.run([sys.executable, str(confirm_script), sample_sh, "--action-id", action_id, "--dry-run", "--json"],
                         capture_output=True, text=True, env={"WS_HOME": str(ROOT)})
    
    if res.returncode == 0:
        data = json.loads(res.stdout)
        if data.get("status") == "DRY_RUN_PREVIEW":
            print(f"PASS (Successfully previewed {action_id})")
        else:
            print(f"FAIL: Unexpected response status: {data.get('status')}")
    else:
        print(f"FAIL: Preview command failed: {res.stderr}")

def main():
    print("Validating Learning Confirmation TUI Preview Interactivity v1")
    print("===========================================================")
    test_preview_safety_guard()
    test_actual_preview_call()

if __name__ == "__main__":
    main()
