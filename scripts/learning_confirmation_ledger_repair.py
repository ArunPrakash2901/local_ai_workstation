#!/usr/bin/env python3
"""Learning Confirmation Ledger Repair Tool v1."""

import json
import sys
import os
import shutil
from pathlib import Path
from datetime import datetime

def load_jsonl(path: Path):
    if not path.is_file():
        return []
    entries = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
    except Exception:
        return None
    return entries

def save_jsonl(path: Path, entries: list):
    temp_path = path.with_suffix(".tmp")
    try:
        with temp_path.open("w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
        os.replace(temp_path, path)
        return True
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        return False

class LearningConfirmationLedgerRepair:
    def __init__(self, stronghold_dir: Path, dry_run: bool = True):
        self.stronghold_dir = stronghold_dir
        self.stronghold_id = stronghold_dir.name
        self.dry_run = dry_run
        self.ledger_path = stronghold_dir / "learning_confirmations.jsonl"
        self.confirmed_dir = stronghold_dir / "confirmed_actions"
        self.backup_dir = stronghold_dir / "ledger_backups"
        self.audit_file = stronghold_dir / "ledger_repair_audit.jsonl"
        self.state_file = stronghold_dir / "state.json"
        
        self.entries = []
        self.repaired_count = 0
        self.blocked_entries = []
        self.warnings = []
        self.repair_details = []

    def get_state_mtime(self):
        if self.state_file.exists():
            return datetime.fromtimestamp(self.state_file.stat().st_mtime).isoformat()
        return None

    def find_artifact(self, original_action_id, confirmed_action_type):
        if not self.confirmed_dir.is_dir():
            return None, "CONFIRMED_ACTIONS_DIR_MISSING"
            
        candidates = []
        for f in self.confirmed_dir.glob("*.md"):
            if original_action_id in f.name and confirmed_action_type in f.name:
                candidates.append(f)
                
        if len(candidates) == 0:
            return None, "MISSING_ARTIFACT_CANDIDATE"
        if len(candidates) > 1:
            return None, "AMBIGUOUS_ARTIFACT_CANDIDATES"
            
        return candidates[0], None

    def repair(self):
        self.entries = load_jsonl(self.ledger_path)
        if self.entries is None:
            return {"status": "ERROR", "message": "Failed to load ledger."}
            
        state_mtime_before = self.get_state_mtime()
        
        repaired_entries = []
        for i, entry in enumerate(self.entries):
            confirmation_id = entry.get("confirmation_id")
            if entry.get("artifact_path"):
                # Already has path
                continue
                
            action_id = entry.get("original_action_id")
            action_type = entry.get("confirmed_action_type")
            
            if not action_id or not action_type:
                self.warnings.append(f"Entry {confirmation_id} missing ID or Type metadata.")
                continue
                
            artifact_path, error = self.find_artifact(action_id, action_type)
            if error:
                self.blocked_entries.append({
                    "confirmation_id": confirmation_id,
                    "error": error
                })
                continue
                
            # Propose repair
            entry["artifact_path"] = str(artifact_path)
            repaired_entries.append({
                "confirmation_id": confirmation_id,
                "repaired_path": str(artifact_path)
            })
            self.repaired_count += 1
            
        if self.repaired_count == 0:
            return {
                "status": "SKIPPED",
                "message": "No repairable entries found.",
                "blocked_entries": self.blocked_entries,
                "warnings": self.warnings
            }

        if self.dry_run:
            return {
                "status": "DRY_RUN",
                "message": "DRY-RUN ONLY: learning_confirmations.jsonl was not modified.",
                "repaired_entries": repaired_entries,
                "blocked_entries": self.blocked_entries,
                "warnings": self.warnings,
                "ledger_path": str(self.ledger_path),
                "would_create_backup_path": str(self.backup_dir / "learning_confirmations_YYYYMMDDTHHMMSSZ_before_repair.jsonl"),
                "state_json_mtime_before": state_mtime_before,
                "no_write": True
            }

        # Actual Repair
        # 1. Backup
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%dT%H%M%SZ')
            backup_path = self.backup_dir / f"learning_confirmations_{timestamp}_before_repair.jsonl"
            shutil.copy2(self.ledger_path, backup_path)
        except Exception as e:
            return {"status": "ERROR", "message": f"Failed to create backup: {str(e)}"}
            
        # 2. Write Repaired Ledger
        if not save_jsonl(self.ledger_path, self.entries):
            return {"status": "ERROR", "message": "Failed to save repaired ledger."}
            
        state_mtime_after = self.get_state_mtime()
        
        # 3. Audit
        audit_record = {
            "repair_id": f"REPAIR-{timestamp}",
            "timestamp_utc": timestamp,
            "stronghold_id": self.stronghold_id,
            "source": "learning_confirmation_ledger_repair_v1",
            "mode": "REPAIR_LEDGER",
            "ledger_path": str(self.ledger_path),
            "backup_path": str(backup_path),
            "repaired_entries": repaired_entries,
            "blocked_entries": self.blocked_entries,
            "warnings": self.warnings,
            "confirmation_status": "LEDGER_REPAIR_APPLIED",
            "state_json_mtime_before": state_mtime_before,
            "state_json_mtime_after": state_mtime_after
        }
        
        try:
            with self.audit_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(audit_record) + "\n")
        except Exception as e:
            self.warnings.append(f"Failed to write audit record: {str(e)}")

        return {
            "status": "SUCCESS",
            "message": "Ledger repair applied. state.json was not modified.",
            "backup_path": str(backup_path),
            "repaired_count": self.repaired_count,
            "audit_path": str(self.audit_file)
        }

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/learning_confirmation_ledger_repair.py <stronghold_id> --dry-run|--repair-ledger [--json]")
        sys.exit(1)
        
    stronghold_id = sys.argv[1]
    is_json = "--json" in sys.argv
    
    mode = None
    if "--dry-run" in sys.argv and "--repair-ledger" in sys.argv:
        if is_json:
            print(json.dumps({"error": "Cannot use both --dry-run and --repair-ledger.", "status": "FAILED"}))
        else:
            print("Error: Cannot use both --dry-run and --repair-ledger.")
        sys.exit(1)
        
    if "--dry-run" in sys.argv:
        mode = "dry-run"
    elif "--repair-ledger" in sys.argv:
        mode = "repair-ledger"
    else:
        if is_json:
            print(json.dumps({"error": "Must specify either --dry-run or --repair-ledger.", "status": "FAILED"}))
        else:
            print("Error: Must specify either --dry-run or --repair-ledger.")
        sys.exit(1)

    default_ws_home = "D:\\_ai_brain" if os.name == 'nt' else "/mnt/d/_ai_brain"
    ws_home = Path(os.environ.get("WS_HOME", default_ws_home))
    stronghold_dir = ws_home / "strongholds" / "learning" / stronghold_id
    
    if not stronghold_dir.is_dir():
        if is_json:
            print(json.dumps({"error": f"Stronghold not found at {stronghold_dir}", "status": "FAILED"}))
        else:
            print(f"Error: Stronghold not found at {stronghold_dir}")
        sys.exit(1)

    repairer = LearningConfirmationLedgerRepair(stronghold_dir, dry_run=(mode == "dry-run"))
    result = repairer.repair()
    
    if is_json:
        print(json.dumps(result, indent=2))
    else:
        if result["status"] == "ERROR":
            print(f"FAILED: {result['message']}")
            sys.exit(1)
            
        print(f"Learning Ledger Repair ({mode}): {stronghold_id}")
        print("=" * 60)
        print(result["message"])
        
        if result.get("repaired_entries"):
            print(f"\nRepaired Entries ({len(result['repaired_entries'])}):")
            for entry in result["repaired_entries"]:
                print(f"- {entry['confirmation_id']} -> {entry['repaired_path']}")
                
        if result.get("blocked_entries"):
            print(f"\nBlocked Entries ({len(result['blocked_entries'])}):")
            for entry in result["blocked_entries"]:
                print(f"- {entry['confirmation_id']}: {entry['error']}")
                
        if result.get("warnings"):
            print("\nWARNINGS:")
            for w in result["warnings"]:
                print(f"! {w}")
                
        if result.get("backup_path"):
            print(f"\nBackup: {result['backup_path']}")
        if result.get("audit_path"):
            print(f"Audit:  {result['audit_path']}")

if __name__ == "__main__":
    main()
