#!/usr/bin/env python3
"""Learning State Synchronization Apply v1."""

import json
import sys
import os
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict

# Ensure we can import from the same directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from learning_state_sync_planner import generate_plan, load_json, load_ledger, STATE_PATH_ALLOWLIST, normalize_path
except ImportError:
    print("Error: Could not import learning_state_sync_planner. Ensure it is in the same directory.")
    sys.exit(1)

class LearningStateSyncApply:
    def __init__(self, stronghold_dir: Path, dry_run: bool = True):
        self.stronghold_dir = stronghold_dir
        self.stronghold_id = stronghold_dir.name
        self.dry_run = dry_run
        self.state_file = stronghold_dir / "state.json"
        self.ledger_file = stronghold_dir / "learning_confirmations.jsonl"
        self.audit_file = stronghold_dir / "state_sync_audit.jsonl"
        self.backup_dir = stronghold_dir / "state_backups"
        self.plan = None
        self.eligible_changes = []
        self.skipped_changes = []
        self.blocked_changes = []
        self.warnings = []

    def load_plan(self):
        state = load_json(self.state_file)
        if not state:
            return False, "Could not load state.json"
        
        ledger = load_ledger(self.ledger_file)
        if ledger is None:
            return False, "Could not load ledger"
            
        self.plan = generate_plan(self.stronghold_dir, state, ledger)
        return True, None

    def filter_eligibility(self):
        if not self.plan:
            return
            
        for change in self.plan.get("proposed_state_changes", []):
            # Eligibility rules:
            # - risk_level is LOW
            # - evidence_quality is strong
            # - apply_allowed_in_phase_7b is true
            # - target path is allowlisted
            # - source artifact exists (already checked by planner but we re-verify)
            
            target_path = change.get("target_path")
            risk_level = change.get("risk_level")
            evidence_quality = change.get("evidence_quality")
            apply_allowed = change.get("apply_allowed_in_phase_7b")
            
            reasons = []
            if risk_level != "LOW":
                reasons.append(f"Risk level is {risk_level} (only LOW allowed)")
            if evidence_quality != "strong":
                reasons.append(f"Evidence quality is {evidence_quality} (only strong allowed)")
            if not apply_allowed:
                reasons.append("Not allowed in Phase 7B")
            if target_path not in STATE_PATH_ALLOWLIST:
                reasons.append(f"Target path {target_path} not in allowlist")

            if not reasons:
                # Re-verify artifact existence
                source_confirmation_id = change.get("source_confirmation_id")
                confirmation = next((c for c in self.plan["eligible_confirmations"] if c["confirmation_id"] == source_confirmation_id), None)
                if not confirmation:
                    reasons.append("Source confirmation not found in plan")
                else:
                    ws_home = Path(os.environ.get("WS_HOME", "/mnt/d/_ai_brain"))
                    artifact_path = normalize_path(confirmation.get("artifact_path"), ws_home)
                    if not artifact_path.is_file():
                        reasons.append(f"Artifact file missing: {artifact_path}")
            
            if not reasons:
                self.eligible_changes.append(change)
            else:
                change["block_reasons"] = reasons
                if risk_level == "HIGH" or risk_level == "BLOCKED":
                    self.blocked_changes.append(change)
                else:
                    self.skipped_changes.append(change)

    def apply(self):
        if self.dry_run:
            return {"status": "DRY_RUN", "message": "DRY-RUN ONLY: state.json was not modified."}
            
        if not self.eligible_changes:
            return {"status": "SKIPPED", "message": "No eligible changes to apply."}

        # 1. Create backup
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%dT%H%M%SZ')
            backup_path = self.backup_dir / f"state_{timestamp}_before_sync.json"
            shutil.copy2(self.state_file, backup_path)
        except Exception as e:
            return {"status": "ERROR", "message": f"Failed to create backup: {str(e)}"}
        
        # 2. Load latest state for read-modify-write
        state = load_json(self.state_file)
        if not state:
             return {"status": "ERROR", "message": "Failed to re-load state.json during apply."}
        
        # 3. Apply changes
        applied = []
        for change in self.eligible_changes:
            target_path = change["target_path"]
            # Path is like "state.learning_session_status"
            parts = target_path.split(".")
            if parts[0] != "state":
                continue
            
            key = parts[1]
            
            # Verify current value hasn't changed since plan
            if state.get(key) != change["current_value"]:
                self.warnings.append(f"State mismatch for {target_path}. Skipping.")
                continue
                
            state[key] = change["proposed_value"]
            applied.append(change)

        if not applied:
            return {"status": "SKIPPED", "message": "All eligible changes were skipped due to state drift."}

        # 4. Write state.json atomically-ish
        temp_state_file = self.state_file.with_suffix(".tmp")
        try:
            with open(temp_state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
                f.write("\n")
            os.replace(temp_state_file, self.state_file)
        except Exception as e:
            if temp_state_file.exists():
                try: temp_state_file.unlink()
                except: pass
            return {"status": "ERROR", "message": f"Failed to write state.json: {str(e)}"}
            
        # 5. Verify write
        new_state = load_json(self.state_file)
        if not new_state:
            return {"status": "ERROR", "message": "Verification failed: state.json is unreadable after write."}
            
        for change in applied:
            key = change["target_path"].split(".")[1]
            if new_state.get(key) != change["proposed_value"]:
                return {"status": "ERROR", "message": f"Verification failed for {change['target_path']}"}

        # 6. Audit record
        audit_record = {
            "sync_id": f"SYNC-{timestamp}",
            "timestamp_utc": timestamp,
            "stronghold_id": self.stronghold_id,
            "source": "learning_state_sync_apply_v1",
            "mode": "CONFIRM_SYNC",
            "planner_plan_id": self.plan.get("plan_id"),
            "state_path": str(self.state_file),
            "backup_path": str(backup_path),
            "applied_changes": applied,
            "skipped_changes": self.skipped_changes + [c for c in self.eligible_changes if c not in applied],
            "blocked_changes": self.blocked_changes,
            "warnings": self.warnings,
            "confirmation_status": "STATE_SYNC_APPLIED"
        }
        
        try:
            with open(self.audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_record) + "\n")
        except Exception as e:
            self.warnings.append(f"Failed to write audit record: {str(e)}")
            
        return {
            "status": "SUCCESS",
            "message": "State synchronization applied only to Phase 7B-eligible low-risk changes. Advancement remains manual.",
            "backup_path": str(backup_path),
            "applied_count": len(applied),
            "sync_id": audit_record["sync_id"]
        }

def main():
    is_json = "--json" in sys.argv

    if "--dry-run" in sys.argv and "--confirm-sync" in sys.argv:
        if is_json:
            print(json.dumps({"error": "Cannot use both --dry-run and --confirm-sync.", "status": "FAILED"}))
        else:
            print("Error: Cannot use both --dry-run and --confirm-sync.")
        sys.exit(1)
        
    mode = None
    if "--dry-run" in sys.argv:
        mode = "dry-run"
    elif "--confirm-sync" in sys.argv:
        mode = "confirm-sync"
    else:
        if is_json:
            print(json.dumps({"error": "Must specify either --dry-run or --confirm-sync.", "status": "FAILED"}))
        else:
            print("Error: Must specify either --dry-run or --confirm-sync.")
        sys.exit(1)

    default_ws_home = "D:\\_ai_brain" if os.name == 'nt' else "/mnt/d/_ai_brain"
    ws_home = Path(os.environ.get("WS_HOME", default_ws_home))
    strongholds_dir = ws_home / "strongholds"
    
    stronghold_id = None
    for arg in sys.argv[1:]:
        if not arg.startswith("-"):
            stronghold_id = arg
            break
            
    if not stronghold_id:
        if is_json:
            print(json.dumps({"error": "No stronghold ID provided.", "status": "FAILED"}))
        else:
            print("Error: No stronghold ID provided.")
        sys.exit(1)
        
    stronghold_dir = strongholds_dir / "learning" / stronghold_id
    if not stronghold_dir.is_dir():
        if is_json:
            print(json.dumps({"error": f"Stronghold not found at {stronghold_dir}", "status": "FAILED"}))
        else:
            print(f"Error: Stronghold not found at {stronghold_dir}")
        sys.exit(1)

    applier = LearningStateSyncApply(stronghold_dir, dry_run=(mode == "dry-run"))
    success, err = applier.load_plan()
    if not success:
        if is_json:
            print(json.dumps({"error": err, "status": "FAILED"}))
        else:
            print(f"Error: {err}")
        sys.exit(1)
        
    applier.filter_eligibility()
    
    if mode == "dry-run":
        if is_json:
            result = {
                "plan_id": applier.plan.get("plan_id"),
                "eligible": applier.eligible_changes,
                "skipped": applier.skipped_changes,
                "blocked": applier.blocked_changes,
                "warnings": applier.warnings,
                "backup_path_preview": str(applier.backup_dir / "state_YYYYMMDDTHHMMSSZ_before_sync.json"),
                "audit_path": str(applier.audit_file),
                "status": "DRY_RUN_ONLY"
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"Learning State Sync Apply (Dry-Run) for: {stronghold_id}")
            print("=" * 60)
            print(f"Eligible Changes: {len(applier.eligible_changes)}")
            for c in applier.eligible_changes:
                print(f"- {c['target_path']} -> {c['proposed_value']} ({c['reason']})")
            
            print(f"\nSkipped Changes: {len(applier.skipped_changes)}")
            for c in applier.skipped_changes:
                print(f"- {c['target_path']}: {', '.join(c.get('block_reasons', []))}")

            print(f"\nBlocked Changes: {len(applier.blocked_changes)}")
            for c in applier.blocked_changes:
                print(f"- {c['target_path']}: {', '.join(c.get('block_reasons', []))}")

            if applier.warnings:
                print("\nWARNINGS:")
                for w in applier.warnings:
                    print(f"! {w}")

            print("\nDRY-RUN ONLY: state.json was not modified.")
    else:
        # Confirm Sync
        result = applier.apply()
        if is_json:
            print(json.dumps(result, indent=2))
        else:
            if result["status"] == "SUCCESS":
                print("SUCCESS")
                print(result["message"])
                print(f"Applied: {result['applied_count']} changes")
                print(f"Backup:  {result['backup_path']}")
            else:
                print(f"FAILED: {result['status']}")
                print(result["message"])
                sys.exit(1)

if __name__ == "__main__":
    main()
