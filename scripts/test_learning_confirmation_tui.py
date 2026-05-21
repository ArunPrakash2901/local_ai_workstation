#!/usr/bin/env python3
"""Validation for Learning Confirmation TUI Integration v1."""

import json
import sys
import os
import subprocess
from pathlib import Path
from dataclasses import dataclass, field

# Mocking parts of the TUI environment for testing data collection logic
ROOT = Path(__file__).resolve().parents[1]
WS_HOME = ROOT

def test_ledger_read():
    print("Testing: Ledger read integration")
    sample_sh = "fine-tuning-small-open-source-models"
    ledger_path = ROOT / "strongholds" / "learning" / sample_sh / "learning_confirmations.jsonl"
    
    if not ledger_path.is_file():
        print(f"SKIP: Ledger not found at {ledger_path}")
        return

    ledger_v1 = []
    try:
        with open(ledger_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-10:]:
                if line.strip():
                    ledger_v1.append(json.loads(line))
        
        if len(ledger_v1) > 0:
            print(f"PASS (Read {len(ledger_v1)} entries from ledger)")
            for entry in ledger_v1:
                if "confirmation_id" not in entry:
                    print("FAIL: Missing confirmation_id in entry")
                    return
        else:
            print("INFO: Ledger is empty, but read successfully.")
    except Exception as e:
        print(f"FAIL: Error reading ledger: {e}")

def test_artifact_visibility():
    print("Testing: Confirmed artifact visibility")
    sample_sh = "fine-tuning-small-open-source-models"
    confirmed_dir = ROOT / "strongholds" / "learning" / sample_sh / "confirmed_actions"
    
    if not confirmed_dir.is_dir():
        print(f"SKIP: Confirmed actions dir not found at {confirmed_dir}")
        return

    try:
        artifacts = sorted(
            [f for f in confirmed_dir.iterdir() if f.is_file() and f.suffix == ".md"],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        filenames = [f.name for f in artifacts[:5]]
        
        if len(filenames) > 0:
            print(f"PASS (Found {len(filenames)} artifacts)")
        else:
            print("INFO: No artifacts found, but directory exists.")
    except Exception as e:
        print(f"FAIL: Error listing artifacts: {e}")

def test_action_pack_integration():
    print("Testing: Action Pack JSON consumption")
    sample_sh = "fine-tuning-small-open-source-models"
    script_path = ROOT / "scripts" / "learning_action_pack.py"
    
    if not script_path.is_file():
        print(f"FAIL: Action pack script not found at {script_path}")
        return

    try:
        res = subprocess.run(
            [sys.executable, str(script_path), sample_sh, "--dry-run", "--json"],
            capture_output=True,
            text=True,
            env={"WS_HOME": str(WS_HOME), "PYTHONDONTWRITEBYTECODE": "1"}
        )
        if res.returncode == 0:
            actions = json.loads(res.stdout)
            if isinstance(actions, list):
                print(f"PASS (Consumed {len(actions)} actions)")
            else:
                print("FAIL: Action pack output is not a list")
        else:
            print(f"FAIL: Action pack command failed: {res.stderr}")
    except Exception as e:
        print(f"FAIL: Exception during action pack integration test: {e}")

def main():
    print("Validating Learning Confirmation TUI Integration v1")
    print("================================================")
    test_ledger_read()
    test_artifact_visibility()
    test_action_pack_integration()

if __name__ == "__main__":
    main()
