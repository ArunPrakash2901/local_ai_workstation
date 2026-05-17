# Phase 4.2: Supervised Feature-Run Apply Design

## Executive Summary
Phase 4.1 successfully introduced the supervised `ws feature-run <feature> --dry-run` preflight check, validating local evidence (plans, validations, and handoff reviews) before any execution occurs. However, actual codebase mutation must not occur haphazardly. This document outlines the design for the supervised actual execution lane (`--apply`), answering critical architectural questions to ensure mutations are strictly controlled, fully isolated, and explicitly human-approved. 

Because the current state shows that the existing worktree is `BEHIND_MAIN` and the workstation lacks a mature worktree sync/recreate workflow, **the actual implementation of this apply lane must be deferred until worktree synchronization and lifecycle management are complete.**

## Architectural Questions & Answers

### 1. Should actual feature-run require a reviewed worktree?
**Yes.** The execution must run against a reviewed, isolated worktree. The `main` branch should serve strictly as a read-only base for planning and evidence gathering. Mutating an isolated worktree prevents uncertain agent output from corrupting the core repository.

### 2. Should actual feature-run be blocked until ws worktree-review returns READY?
**Yes.** The feature-run apply lane must enforce that `ws worktree-review` yields a `READY` state. If the worktree is `BEHIND_MAIN` (as observed currently) or otherwise corrupted, the preflight must block execution.

### 3. How should the system handle the current worktree that is behind main?
Currently, worktree `001_20260516_135830` is `BEHIND_MAIN`. Before the feature-run apply logic can be used, the workstation must introduce a workflow to safely **sync** (rebase/merge) or **recreate** the worktree from the latest `main` commit. The `feature-run` command should not attempt to sync it automatically; it should block and advise the operator to perform a worktree sync.

### 4. Should ws feature-run --apply delegate to ws apply-ready and ws agent-run, or create its own apply logic?
**It must delegate.** `ws feature-run` acts as a high-level, feature-aware orchestrator and gatekeeper. Once all gates pass, it should invoke `ws apply-ready` to perform low-level execution checks, followed by `ws agent-run` to handle the bounded execution (Codex/Gemini apply). Duplicating apply logic would violate single-responsibility principles.

### 5. What exact command shape should exist later?
```bash
ws feature-run <feature_id_or_path> --apply --worktree <worktree_path> --from-dry-run <dry_run_report_path>
```
This forces explicit human approval: the operator must acknowledge the dry-run report and explicitly declare the target worktree.

### 6. What inputs should be required?
The execution lane must require a comprehensive set of passing preconditions:
- A recent `FEATURE_RUN_DRY_READY` report explicitly referenced via `--from-dry-run`.
- Feature state is `VALIDATED_LOCAL`.
- Latest handoff review is `REVIEW_ACCEPTED`.
- The target worktree has a clean Git status.
- The target worktree is reviewed (`READY`).
- Explicit allowed files are defined in `state.json`.
- System readiness (`ws ready`) passes.
- System hygiene (`ws agent-hygiene`) passes.
- The bounded check `ws apply-ready` passes on the specified worktree.

### 7. How recent should the dry-run report be?
The dry-run report should be strictly enforced as "fresh." A reasonable threshold is within the last 30 minutes, and critically, the underlying commit hash in the dry-run report must exactly match the current `HEAD` of both the `main` branch and the target worktree.

### 8. Should actual apply run in the worktree or main repo?
**In the worktree only.** The execution script must `cd` into the worktree path before delegating to `ws agent-run`.

### 9. How should run reports link?
The Feature Stronghold remains the central source of truth. The feature's `loop_log.md` must link:
- The `feature-run` invocation timestamp.
- The specific target worktree path.
- The target branch name.
- The generated `agent-run` folder (e.g., `auto_runs/` relative to the worktree or workspace).
- The `apply-ready` validation report.
This ensures a fully auditable chain of custody from planning to execution.

### 10. What terminal states should exist?
- `FEATURE_RUN_APPLY_READY` (Pre-execution validation passed)
- `FEATURE_RUN_APPLY_IN_PROGRESS` (Agent execution running)
- `FEATURE_RUN_APPLY_SUCCESS` (Execution completed successfully)
- `FEATURE_RUN_APPLY_FAILED` (Execution failed or timed out)
- `FEATURE_RUN_BLOCKED` (Preconditions failed)
- `FEATURE_RUN_WORKTREE_NOT_READY` (Worktree is missing or not `READY`)

### 11. What rollback/stop conditions should exist?
- **Stop Conditions:** The run must immediately halt if `agent-run` times out, a test script fails, or syntax/linting rules are violated.
- **Rollback:** Rollback is intrinsically supported by worktree isolation. If a run fails, the worktree can simply be discarded or hard-reset, leaving the `main` repo pristine. No automatic rebasing or amending should happen upon failure.

### 12. How should human approval be represented?
Human approval is explicitly represented by the manual execution of the `--apply` command, passing both the `--worktree` flag and the explicit `--from-dry-run` report path. It represents deliberate operator intent.

### 13. Why actual implementation should still be deferred until worktree sync/review is complete.
The current validation checks reveal that the workstation's isolated worktree (`001_20260516_135830`) is `BEHIND_MAIN`. Without an established procedure to bring a worktree up to date, any applied changes would result in a stale foundation or subsequent merge conflicts. The `ws feature-run --apply` implementation must remain deferred until a `ws worktree-sync` (or equivalent recreate workflow) is designed and implemented.

## Next Steps
1. Design and implement the `ws worktree-sync` or worktree recreation workflow to ensure isolated environments can be reliably brought to a `READY` state.
2. Resolve the existing `BEHIND_MAIN` status for the active worktree.
3. Once worktree lifecycle management is mature, proceed with implementing `ws feature-run --apply` as designed here.