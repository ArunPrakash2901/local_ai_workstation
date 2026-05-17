# Phase 4.7: Feature Apply-Ready Handoff Implementation

## Overview
Phase 4.7 implements the `ws feature-run <feature_id> --apply --worktree <path> --from-dry-run <report_path>` execution lane. In accordance with the Phase 4.6 safety design, this command acts as the final orchestrator gatekeeper. Instead of immediately spawning an autonomous agent that could capriciously mutate the codebase, it halts after verifying absolute readiness, producing a deterministic, feature-scoped "Apply-Ready Handoff" with explicit instructions for the human operator.

## Files Changed
- **`scripts/ws_feature_run.sh`**: Extensive updates to support parsing `--apply`, `--worktree`, and `--from-dry-run`. Added strict logic to ensure mutual exclusivity with `--dry-run`. Implemented the exhaustive preflight sequence checking the validity of the worktree, the recency and match of the dry-run report, the presence of the `WORKTREE_REVIEW_*.md` report with the `READY` classification, and the resolution of the latest handoff review via `metadata.json`. Finally, logic was added to formulate the `feature_apply_ready_<timestamp>.md` handoff artifact and seamlessly append execution context into the feature's internal `loop_log.md`.
- **`WORKSTATION_MANUAL.md`**: Brief documentation update enumerating the `ws feature-run --apply` syntax and its intent.

## Behavior Implemented
The orchestrator performs the following rigorous checks immediately prior to generating a handoff:
1. Validates `--dry-run` and `--apply` are not mixed and that required sub-arguments are explicitly mapped.
2. Extracts and confirms the `FEATURE_RUN_DRY_READY` state from the referenced dry-run report.
3. Ensures the specified worktree path matches exactly and currently exhibits a perfectly clean git tree (`git status --short`).
4. Iterates through recent `WORKTREE_REVIEW_*.md` reports, confirming the target branch possesses an active `Classification**: READY` designation.
5. Scans the local `handoffs/` registry using `metadata.json` to deterministically verify that the feature has secured an approved `REVIEW_ACCEPTED` human/LLM handoff.
6. Writes the final execution handoff containing the exact parameters into the feature's internal `runs/` folder and logs the event in `loop_log.md`.

In the event of success, the terminal output yields `Classification: FEATURE_APPLY_READY_HANDOFF` alongside the explicitly safe instruction: `HANDOFF_ONLY (The current ws agent-run script does not safely support targeting an arbitrary isolated worktree. Do not run an automatic agent.)`

## Validation Run
All implemented behavior was empirically verified against the `stabilize-ws-command-documentation` feature and the `001_20260516_135830` worktree.
- **Dry-run**: Generated successfully via `ws feature-run --dry-run`.
- **Apply Execution**: Ran the full syntax against the freshly minted dry-run. The orchestrator flawlessly performed all the gated verifications and generated the `FEATURE_APPLY_READY_HANDOFF` classification.
- **Workstation Integrity**: Executed `ws ready`, `ws agent-hygiene`, `git status --short`, and `git diff --stat` to certify the `D:\_ai_brain` state remained pristine and completely unaffected by unauthorized mutation.

## Limitations
- **Delegated Agent Execution**: As enforced by the design constraints, this script deliberately omits direct instantiation of the `ws agent-run` flow. If automatic agent integration is desired in the future, the underlying `ws_agent_run.ps1` script must be refactored to securely context-switch into the `worktree` paths rather than indiscriminately operating on the `main` repo.

## Next Steps
This marks the successful integration of the strict, highly supervised `feature-run` execution loop. Future work should transition toward upgrading the existing `ws agent-run` boundaries to safely accept and orchestrate `READY` isolated worktrees.