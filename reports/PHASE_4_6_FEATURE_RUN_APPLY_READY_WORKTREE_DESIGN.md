# Phase 4.6: Feature Run Apply Ready Worktree Design

## Executive Summary
With Phase 4.5 complete, the workstation now possesses a safe `worktree-sync` execution lane, enabling drifted, isolated worktrees to be fast-forwarded to a `READY` state. This satisfies the primary blocker for the supervised `feature-run --apply` lane. This document refreshes the feature-run execution design, establishing the explicit preconditions, delegation logic, and safety guardrails required for the final execution flow.

The recommendation is to implement a **Feature-Scoped Apply-Ready Handoff** rather than immediately running a cloud-connected Codex loop. This ensures operator control and allows for inspection of the prepared execution environment before autonomous codebase mutation begins.

## Architectural Questions & Answers

### 1. What exact gates must pass before feature-run --apply?
Execution must be strictly gated by verified evidence. The required gates are:
1. Feature state must be `VALIDATED_LOCAL`.
2. The latest handoff review must be `REVIEW_ACCEPTED`.
3. The main repository must be completely clean.
4. The target worktree must be completely clean and `READY` (meaning it matches the `main` commit).
5. System-level checks (`ws ready`, `ws agent-hygiene`) must be passing.
6. The operator must provide a recent, matching `FEATURE_RUN_DRY_READY` report.

### 2. Should feature-run --apply require explicit flags and clean states?
**Yes.** All listed elements must be strictly required:
- **Recent `FEATURE_RUN_DRY_READY` report:** Prevents stale state execution.
- **`VALIDATED_LOCAL` feature:** Ensures local planning and validation are complete.
- **`REVIEW_ACCEPTED` handoff:** Ensures a human or deterministic process has approved the intended change.
- **Clean main repo & Clean `READY` worktree:** Guarantees isolation and absence of uncommitted work.
- **Explicit worktree path & `--from-dry-run` report:** Requires intentional, manual operator input.
- **`ws ready` & `ws agent-hygiene`:** Verifies the underlying workstation infrastructure is healthy.

### 3. Should feature-run --apply delegate to existing ws apply-ready and ws agent-run, or first generate a feature-scoped apply packet?
It should **first generate a feature-scoped apply packet** and delegate to `ws apply-ready`. `ws feature-run` acts as an orchestrator. It should not contain duplicate apply logic. By stopping at the generation of an apply-ready packet/handoff, the operator can explicitly decide when to invoke `ws agent-run`, maintaining the human-in-the-loop safety design.

### 4. Should actual apply run from the main repo or the READY worktree?
**From the READY worktree.** The `main` repository must remain a pristine, read-only base. All automated mutations must occur strictly inside the isolated worktree to prevent accidental corruption of the canonical codebase.

### 5. How should allowed files be interpreted relative to the worktree path?
Allowed files are defined in the feature stronghold's `state.json` (e.g., `scripts/ws`). When executing an apply operation, these paths must be interpreted **relative to the target worktree root**, not the main repository root. Any mutation outside these specific relative paths within the worktree should be flagged as a violation.

### 6. How should reports link?
The central source of truth is the feature's `loop_log.md`. It should record:
- **Feature Stronghold:** The base context.
- **Worktree path & branch:** Where execution is occurring.
- **Dry-run report:** The explicitly referenced preflight evidence.
- **Apply-ready report:** The output of the subsequent `ws apply-ready` check.
- **Agent-run folder:** The specific output folder inside `auto_runs/` where the cloud execution artifacts are stored.

### 7. What command shape should be used?
```bash
ws feature-run <feature_id_or_path> --apply --worktree <worktree_path> --from-dry-run <feature_run_dry_report_path>
```

### 8. What should happen if Codex/cloud quota fails?
If the underlying `ws agent-run` encounters a provider timeout, quota error, or connection failure, the process must immediately halt and output a `FEATURE_RUN_APPLY_FAILED` or `PROVIDER_ERROR` classification. The worktree will contain whatever partial state existed before the failure, which the operator can manually inspect, reset, or retry.

### 9. What should happen if apply-ready blocks?
If `ws apply-ready` fails (e.g., due to a syntax error or missing prerequisite), `feature-run --apply` must immediately block, log `FEATURE_RUN_APPLY_BLOCKED_BY_READY_CHECK`, and abort before invoking `ws agent-run`.

### 10. What should happen if agent-run completes but diff violates allowed files?
The `agent-run` validation contract must catch this. If the generated diff mutates files not listed in the feature's `allowed_files`, the agent run must be classified as `FAILED`, the changes should remain uncommitted in the worktree, and the feature stronghold state should transition to a blocked or review-required state.

### 11. What terminal states should exist?
- `FEATURE_RUN_APPLY_READY_HANDOFF_CREATED` (Successfully passed all gates and prepared the execution packet)
- `FEATURE_RUN_APPLY_BLOCKED_STALE_REPORT`
- `FEATURE_RUN_APPLY_BLOCKED_DIRTY_MAIN`
- `FEATURE_RUN_APPLY_BLOCKED_WORKTREE_NOT_READY`
- `FEATURE_RUN_APPLY_BLOCKED_BY_READY_CHECK`

### 12. What should be the next implementation: apply-ready integration only, or full agent-run integration?
**Apply-ready integration only.** The immediate next phase should focus solely on orchestrating the transition from a `READY` worktree into a validated `apply-ready` state, effectively creating a safe "handoff" for the agent.

### 13. Why the first implementation should probably stop at generating a feature-scoped apply-ready handoff instead of running Codex automatically.
Stopping at a feature-scoped apply-ready handoff provides a critical final human review gate. Autonomous mutation is inherently risky. By decoupling the strict, deterministic readiness checks (which the workstation can automate flawlessly) from the non-deterministic cloud execution (`agent-run`), the operator retains absolute authority over *when* codebase mutation begins. This also allows for graceful recovery if an operator notices a flaw in the target worktree before the cloud provider consumes tokens or alters files.

## Next Steps
- Implement `ws feature-run --apply` limited to generating the apply-ready handoff.
- Validate that it correctly enforces all preconditions including a clean, `READY` worktree.