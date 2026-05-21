# Learning Pointer Update Planner Hardening Audit v1

## Purpose
This document (Phase 9A.5) details the hardening audit of the Learning `next_learning_task` Pointer Update Planner. The objective is to ensure that candidate pointer updates are based on robust, traceable evidence and that conflicts and idempotency are handled gracefully and safely.

## Evidence Source Hardening
The planner was hardened to safely extract candidates from multiple sources:
1.  **Ledger Metadata**: The `evidence` field in `learning_confirmations.jsonl`.
2.  **Artifact Content**: If ledger evidence is weak or missing, the planner safely reads small (<50KB) markdown artifacts in `confirmed_actions/` to extract the `next_learning_task` or the `Confirmed:` effect string.
3.  **Inference**: As a last resort for high-priority actions, it infers the task from the confirmation `title`. This results in `partial` evidence quality.

## Candidate Extraction Rules
- The artifact must exist within the stronghold bounds.
- If inferred from the title, evidence quality is downgraded to `partial`.
- The candidate must not contain unsafe patterns (`rm`, `sudo`, `format C:`, etc.).
- Candidates containing "advancement" trigger a manual review warning.

## Idempotency Classification
If the strongest candidate matches the current `next_learning_task` in `state.json`:
- The candidate status is marked as `already_synchronized`.
- It does *not* trigger a hard blocker.
- `apply_allowed_in_phase_9b` is correctly set to `false`.
- A warning is emitted: "Candidate already matches current next_learning_task."

## Conflict Handling
The planner now rigorously handles conflicting priorities:
- It selects the highest priority candidate (`PROPOSE_NEXT_LESSON_CONFIRMED` > `CREATE_STUDY_TASK_CONFIRMED`).
- If multiple candidates exist at the *same* highest priority with *different* textual tasks, the planner **blocks** the plan with a `MULTIPLE_CONFLICTING_CANDIDATES` error. It refuses to choose silently.

## Source Priority
1. `PROPOSE_NEXT_LESSON_CONFIRMED`
2. `CREATE_STUDY_TASK_CONFIRMED`
3. `MARK_REVIEW_NEEDED_CONFIRMED`
4. `SUMMARIZE_SESSION_CONFIRMED`
5. `ASSESS_ADVANCEMENT_READINESS_CONFIRMED`

## Risk and Evidence Model
- **Risk Level**: Always `MEDIUM`.
- **Evidence Quality**:
    - `strong`: Exact extraction from ledger evidence or artifact file.
    - `partial`: Inferred from title or secondary data.
    - `insufficient`: Missing artifact or missing data.

## Phase 9B Eligibility Rules
`apply_allowed_in_phase_9b` is set to `true` strictly when:
- `candidate_status` == "eligible"
- `evidence_quality` == "strong"
- No blockers exist.
- Artifact is verified on disk.

## Live Stronghold Pointer Plan Summary
Ran against `fine-tuning-small-open-source-models`:
- **Current Task**: `**Intern**: Format dataset as JSONL.`
- **Candidate Task**: `**Intern**: Format dataset as JSONL.`
- **Status**: `DRY_RUN_ONLY`
- **Candidate Status**: `already_synchronized`
- **Blockers**: None.
- **Warnings**: Candidate already matches current next_learning_task.
- **Phase 9B Eligible**: `False` (due to idempotency).

## Validation Results
- **Conflict Detection**: PASS (Blocks when multiple candidates conflict at the same priority).
- **Idempotency Classification**: PASS (Classifies matching candidates as `already_synchronized` instead of `blocked`).
- **Live No-Write Verification**: PASS (Confirmed `state.json` was not mutated during tests).

## Remaining Limitations
- Content extraction is limited to regex matching of specific patterns; it does not fully parse markdown AST.
- Only dry-run functionality is available.

## Readiness Recommendation
The Pointer Update Planner is **STABLE** and **HARDENED**. The candidate extraction, conflict resolution, and idempotency logic meet safety requirements. The repository is ready for **Phase 9B: TUI Pointer Update Apply**.
