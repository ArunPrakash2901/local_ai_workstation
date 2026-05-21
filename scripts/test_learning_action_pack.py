#!/usr/bin/env python3
"""Validation for Learning Dry-Run Action Pack v1."""

import subprocess
import sys
import os
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
WS_CMD = SCRIPTS_DIR / "ws"
ACTION_PACK_PY = SCRIPTS_DIR / "learning_action_pack.py"

def run_cmd(cmd):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # Ensure WS_HOME is set
    env["WS_HOME"] = str(ROOT)
    # Add scripts to PATH for the ws script to find them
    env["PATH"] = f"{SCRIPTS_DIR}{os.pathsep}{env.get('PATH', '')}"
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        shell=True if os.name == 'nt' else False
    )
    return result

SAMPLE_SH = "_test_isolation_fixture"

def test_dry_run_only():
    print("Testing: Command refuses execution without --dry-run")
    # Calling the python script directly to avoid shell complexities
    res = run_cmd([sys.executable, str(ACTION_PACK_PY), SAMPLE_SH])
    if res.returncode != 0 and "Error: This tool currently only supports --dry-run mode." in res.stdout:
        print("PASS")
    else:
        print(f"FAIL: {res.stdout} {res.stderr}")

def test_action_pack_generation():
    print("Testing: Action pack generation for sample stronghold")
    res = run_cmd([sys.executable, str(ACTION_PACK_PY), SAMPLE_SH, "--dry-run"])
    if res.returncode == 0:
        if "Learning Dry-Run Action Pack v1 for:" in res.stdout:
            # Check for at least 6 actions
            action_count = res.stdout.count("Action ID:")
            if action_count >= 6:
                print(f"PASS (Found {action_count} actions)")
            else:
                print(f"FAIL: Only found {action_count} actions")
        else:
            print(f"FAIL: Unexpected output: {res.stdout}")
    else:
        print(f"FAIL: {res.stdout} {res.stderr}")

def test_ws_dispatch():
    print("Testing: 'ws' bash dispatch")
    # Convert Windows path to POSIX-style for Git Bash
    ws_posix = str(WS_CMD).replace('\\', '/').replace('D:', '/d').replace('C:', '/c')
    res = run_cmd(f"bash {ws_posix} learning-action-pack {SAMPLE_SH} --dry-run")
    if res.returncode == 0:
        if "Learning Dry-Run Action Pack v1 for:" in res.stdout:
            print("PASS")
        else:
            print(f"FAIL: Unexpected output: {res.stdout}")
    else:
        # If bash is not found, skip but warn
        if "not found" in res.stderr.lower() or "not recognized" in res.stderr.lower():
             print("SKIP: bash not found, cannot test ws dispatcher directly on host.")
        else:
             print(f"FAIL: {res.stdout} {res.stderr}")

def test_ws_ps1_dispatch():
    if os.name != 'nt':
        return
    print("Testing: 'ws.ps1' PowerShell dispatch")
    ws_ps1 = SCRIPTS_DIR / "ws.ps1"
    res = run_cmd(f"powershell.exe -NoProfile -ExecutionPolicy Bypass -File {ws_ps1} learning-action-pack {SAMPLE_SH} --dry-run")
    if res.returncode == 0:
        if "Learning Dry-Run Action Pack v1 for:" in res.stdout:
            print("PASS")
        else:
            print(f"FAIL: Unexpected output: {res.stdout}")
    else:
        print(f"FAIL: {res.stdout} {res.stderr}")

def main():
    print("Validating Learning Dry-Run Action Pack v1")
    print("==========================================")
    test_dry_run_only()
    test_action_pack_generation()
    test_ws_dispatch()
    test_ws_ps1_dispatch()

if __name__ == "__main__":
    main()
