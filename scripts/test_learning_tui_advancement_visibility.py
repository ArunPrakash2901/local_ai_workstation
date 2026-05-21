#!/usr/bin/env python3
"""Safety Audit for Learning TUI Advancement Visibility v1."""

import subprocess
import sys
import os
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
APP_PY = ROOT / "tui" / "app.py"

def run_cmd(cmd, env=None):
    if env is None:
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

def test_advancement_helper_robustness():
    print("Testing: TUI advancement planner parsing robustness")
    content = APP_PY.read_text(encoding="utf-8")
    
    # 1. Verify subprocess call pattern
    if "--dry-run" in content and "--json" in content and "learning_advancement_readiness_planner.py" in content:
        if "subprocess.run" in content:
             print("PASS (Helper calls dry-run JSON only)")
        else:
             print("FAIL (Helper does not seem to call the planner via subprocess.run)")
    else:
        print("FAIL (Helper does not seem to include required script and flags)")

def test_hard_guards():
    print("Testing: TUI hard guards for advancement")
    content = APP_PY.read_text(encoding="utf-8")
    blocked_flags = ["--advance", "--confirm-advancement", "--apply", "--confirm-sync"]
    
    if 'blocked_flags = ("--confirm-sync", "--repair-ledger", "--apply", "--confirm-pointer", "--advance", "--confirm-advancement")' in content:
        print("PASS (Hard guard flag list is comprehensive)")
    else:
        print("FAIL (Hard guard flag list is missing advancement flags)")

def test_ui_display_safety_markers():
    print("Testing: TUI displays safety markers and warnings")
    content = APP_PY.read_text(encoding="utf-8")
    markers = [
        "ADVANCEMENT READINESS STATUS (PHASE 10A)",
        "Ready for human review does not mean automatic advancement.",
        "** ADVANCEMENT REMAINS MANUAL (HIGH RISK) **",
        "Advancement apply is not implemented in this phase."
    ]
    
    all_present = True
    for marker in markers:
        if marker in content:
            pass
        else:
            all_present = False
            print(f"FAIL: Missing safety marker: '{marker}'")
            
    if all_present:
        print("PASS (All safety markers present in UI code)")

def main():
    print("Validating Learning TUI Advancement Visibility v1 Safety")
    print("=========================================================")
    test_advancement_helper_robustness()
    test_hard_guards()
    test_ui_display_safety_markers()

if __name__ == "__main__":
    main()
