#!/usr/bin/env python3
"""Validation for Learning Human Advancement Review Packet v1."""

import subprocess
import sys
import os
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
PACKET_PY = SCRIPTS_DIR / "learning_advancement_review_packet.py"
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
    res = run_cmd([sys.executable, str(PACKET_PY), SAMPLE_STRONGHOLD])
    if res.returncode != 0 and "Error: Must specify either --dry-run or --create-packet" in res.stdout:
        print("PASS (No mode refused)")
    else:
        print(f"FAIL: No mode check: {res.stdout} {res.stderr}")

    # Both modes
    res = run_cmd([sys.executable, str(PACKET_PY), SAMPLE_STRONGHOLD, "--dry-run", "--create-packet"])
    if res.returncode != 0 and "Error: Cannot use both --dry-run and --create-packet" in res.stdout:
        print("PASS (Both modes refused)")
    else:
        print(f"FAIL: Both modes check: {res.stdout} {res.stderr}")

def test_dry_run_non_mutation():
    print("Testing: --dry-run does NOT mutate state.json or write files")
    state_file = STRONGHOLD_DIR / "state.json"
    mtime_pre = state_file.stat().st_mtime
    
    packet_dir = STRONGHOLD_DIR / "review_packets"
    packets_pre = list(packet_dir.glob("*.md")) if packet_dir.is_dir() else []
    
    run_cmd([sys.executable, str(PACKET_PY), SAMPLE_STRONGHOLD, "--dry-run"])
    
    mtime_post = state_file.stat().st_mtime
    packets_post = list(packet_dir.glob("*.md")) if packet_dir.is_dir() else []
    
    if mtime_pre != mtime_post:
        print(f"FAIL: state.json mutated!")
        return
    if len(packets_pre) != len(packets_post):
        print(f"FAIL: File created during dry-run!")
        return
        
    print("PASS (Dry-run safety verified)")

def test_create_packet_with_isolation():
    print("Testing: --create-packet against isolation fixture")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir)
        fixture_dest = tmp_root / "strongholds" / "learning" / SAMPLE_STRONGHOLD
        fixture_dest.mkdir(parents=True)
        
        # Copy fixture contents
        shutil.copytree(STRONGHOLD_DIR, fixture_dest, dirs_exist_ok=True)
        
        # Need to ensure scripts are available in the virtual env or path
        # We'll point WS_HOME to the temp root but use original scripts
        env = os.environ.copy()
        env["WS_HOME"] = str(tmp_root)
        
        # We also need to copy the scripts to the temp root if they call each other via WS_HOME/scripts
        (tmp_root / "scripts").mkdir()
        for script in ["learning_advancement_review_packet.py", 
                      "learning_advancement_readiness_planner.py", 
                      "learning_pointer_update_planner.py"]:
            shutil.copy(SCRIPTS_DIR / script, tmp_root / "scripts" / script)

        res = subprocess.run(
            [sys.executable, str(tmp_root / "scripts" / "learning_advancement_review_packet.py"), SAMPLE_STRONGHOLD, "--create-packet"],
            capture_output=True,
            text=True,
            env=env,
            shell=True if os.name == 'nt' else False
        )
        
        if res.returncode != 0:
            print(f"FAIL: create-packet failed: {res.stdout} {res.stderr}")
            return
            
        print("PASS (Command executed)")
        
        # Verify packet
        packet_dir = fixture_dest / "review_packets"
        packets = list(packet_dir.glob("*.md"))
        if len(packets) == 1:
            print(f"PASS (One packet created: {packets[0].name})")
            content = packets[0].read_text(encoding="utf-8")
            required_sections = [
                "Current State", "Advancement Readiness", "Pointer Status", 
                "State Sync Status", "Confirmation Evidence", "Required Human Checks",
                "Safety Boundary"
            ]
            missing = [s for s in required_sections if s not in content]
            if not missing:
                print("PASS (All sections present in packet)")
            else:
                print(f"FAIL: Missing sections: {missing}")
                
            if "Advancement remains **MANUAL**" in content:
                print("PASS (Safety boundary correct)")
            else:
                print("FAIL (Safety boundary missing or incorrect)")
        else:
            print(f"FAIL: Expected 1 packet, found {len(packets)}")

def main():
    print("Validating Learning Human Advancement Review Packet v1")
    print("=====================================================")
    test_mode_refusal()
    test_dry_run_non_mutation()
    test_create_packet_with_isolation()

if __name__ == "__main__":
    main()
