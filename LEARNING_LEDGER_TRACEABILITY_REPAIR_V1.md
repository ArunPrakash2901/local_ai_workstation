# Learning Ledger Traceability Repair v1

## Purpose
This tool (Phase 7C.5) repairs legacy `learning_confirmations.jsonl` files by adding missing `artifact_path` fields. These fields are required for Phase 7B/C safety verification, ensuring that every confirmed action has a verifiable source artifact on disk.

## Why Repair is Needed
Early versions of the learning confirmation core did not record the `artifact_path` in the ledger. While the artifacts exist in the `confirmed_actions/` directory, the lack of an explicit link prevents the state sync planner from verifying the evidence, blocking automated state synchronization.

## Command Shapes
The repair tool is integrated into the `ws` command.

### Dry-Run (Preview)
```bash
ws learning-ledger-repair <stronghold_id> --dry-run
ws learning-ledger-repair <stronghold_id> --dry-run --json
```

### Actual Repair
```bash
ws learning-ledger-repair <stronghold_id> --repair-ledger
ws learning-ledger-repair <stronghold_id> --repair-ledger --json
```

## Matching Rules
An artifact is matched to a ledger entry only if:
1. It is a markdown file inside the `confirmed_actions/` directory of the same stronghold.
2. The filename contains the `original_action_id`.
3. The filename contains the `confirmed_action_type`.
4. Exactly ONE artifact matches these criteria (unambiguous match).

If zero or multiple artifacts match, the entry is blocked from repair.

## Backup and Audit
- **Backup**: Before any repair, a timestamped backup of the ledger is created in `ledger_backups/`.
- **Audit**: A repair record is appended to `ledger_repair_audit.jsonl`, documenting the repaired entries, blocked entries, and timestamps.

## Validation Results
- **Isolation Fixture**: PASS (Verified that missing paths are added correctly, backups are created, and `state.json` is untouched).
- **Mode Enforcement**: PASS (Refuses execution without mode or with both modes).
- **Dry-Run Safety**: PASS (Verified no writes in dry-run mode).
- **Atomic Write**: PASS (Uses temp file and rename pattern).

## Live Stronghold Result
The tool was run against `fine-tuning-small-open-source-models`.
- **Entries Repaired**: 2
- **Backup Created**: `ledger_backups/learning_confirmations_20260521T123824Z_before_repair.jsonl`
- **Audit Entry**: Appended to `ledger_repair_audit.jsonl`.
- **State.json**: UNCHANGED.

## Next Step
Now that the ledger has been repaired and traceability is restored, the **Phase 7C Preflight** should be repeated to confirm that state synchronization is now "SAFE".
