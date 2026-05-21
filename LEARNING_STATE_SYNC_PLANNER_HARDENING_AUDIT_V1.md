# Learning State Sync Planner Hardening Audit v1

## Purpose
This audit and hardening phase ensures that the Learning State Synchronization Planner is safe, schema-aware, and extremely conservative before any actual state mutations are implemented in Phase 7B.

## Schema Allowlist
The planner is now restricted to proposing changes only to an explicit allowlist of `state.json` paths:
- `state.learning_session_status`
- `state.last_reported_at`
- `state.next_learning_task`
- `state.last_learning_decision`
- `state.current_state`

Any proposal for an path outside this list is automatically blocked and flagged as a warning.

## Risk and Evidence Model
Every proposed state change now includes:
- **Risk Level**: `LOW`, `MEDIUM`, `HIGH`, or `BLOCKED`.
- **Evidence Quality**: `strong`, `partial`, or `insufficient`.
- **Apply Eligibility**:
    - `apply_allowed_in_v1`: Always `false`.
    - `apply_allowed_in_phase_7b`: Set based on risk and evidence quality.

## Guard Implementation

### 1. Advancement Guard
- **Action**: `ASSESS_ADVANCEMENT_READINESS_CONFIRMED`
- **Policy**: Proposes setting `current_state` to `READY_FOR_ADVANCEMENT`.
- **Harden**: Always marked as `risk_level: HIGH` and `apply_allowed_in_phase_7b: false`. Advancement remains a manual review task.

### 2. Review Schedule Guard
- **Action**: `MARK_REVIEW_NEEDED_CONFIRMED`
- **Policy**: Proposes setting `last_learning_decision` to `REVIEW_NEEDED`.
- **Harden**: Proposes only if the path is in the allowlist. Does not mutate schedules directly.

### 3. Next Lesson Guard
- **Action**: `PROPOSE_NEXT_LESSON_CONFIRMED`
- **Policy**: Proposes updating `next_learning_task`.
- **Harden**: Requires `strong` evidence extracted from the confirmation record.

### 4. Session Summary Guard
- **Action**: `SUMMARIZE_SESSION_CONFIRMED`
- **Policy**: Proposes updating `last_reported_at`.
- **Harden**: Proposes only the confirmation timestamp to the timestamp field.

### 5. Stale Artifact Guard
- **Action**: `DETECT_STALE_LEARNING_ARTIFACTS_CONFIRMED`
- **Policy**: Informational only.
- **Harden**: Explicitly blocked from state mutation proposals.

## Blockers and Warnings
The planner now robustly detects and blocks:
- Unknown target paths (not in allowlist).
- Insufficient evidence for a change.
- Missing artifact files referenced by the ledger.
- Duplicate confirmations in the ledger.
- Malformed JSONL lines in the ledger.

## Validation Results
- **Schema Awareness**: PASS (Verified all proposed paths are allowlisted).
- **Risk/Evidence Metadata**: PASS (Verified every change has risk and quality ratings).
- **Non-Mutation**: PASS (Verified `state.json` mtime remains unchanged).
- **JSON Purity**: PASS (Verified valid JSON output).

## Remaining Limitations
- **Read-Only**: The planner remains strictly dry-run.
- **Manual Apply**: No mechanism exists yet to ingest these proposals into `state.json`.

## Readiness for Phase 7B
The planner is **READY** for the implementation of the guarded state sync apply layer. The risk and evidence quality models provide the necessary filtering for a safe automated apply process.
