# R11: Supervised Cloud-Apply Design
**Date:** 2026-05-16
**Status:** Design Only (Implementation Deferred)

This document outlines the architecture for graduating a completed, local-only plan into a supervised cloud apply (code mutation) phase using the existing `ws agent-run` command.

## 1. Pre-Conditions for Graduation
**What conditions must be true before a local plan can graduate to cloud apply?**
1. The `ws loop-start` command must have completed successfully, resulting in a `LOCAL_PLAN_COMPLETED` terminal state.
2. A valid `local_plan.md` artifact must exist in the generated build run folder.
3. The operator must have manually reviewed the plan and approved the boundaries.
4. The cloud canary status must explicitly evaluate to `AGENT_CANARY_PASSED`.

## 2. Operator Review Responsibilities
**What must the operator review in `local_plan.md` and `build_report.md`?**
- **`local_plan.md`:** The operator must verify that the proposed architecture matches the intent of the task, the intended codebase modifications are isolated within the `Allowed Files` boundary, and no sweeping refactors are hallucinated.
- **`build_report.md`:** The operator must verify that local test/lint/compile steps (if configured in the build phase) passed or identify acceptable known issues, ensuring the baseline is stable before cloud mutation.

## 3. Recommended Command Structure
**How should ws loop-start report recommend the next cloud-apply command?**
`ws loop-start` currently accurately outputs the fallback command. It should continue to suggest:
`ws agent-run <project_key> <task_file> --mode detect --branch --max-files <n> --max-minutes <n> --stop-on-fail`

**Should there be a future command such as `ws loop-apply-plan`?**
No, not initially. Introducing `ws loop-apply-plan` creates disjointed state tracking between the read-only planner and the active cloud agent. The operator should continue to use `ws agent-run` directly, which acts as the unified, bounded, and closely monitored cloud-apply entry point. Future unattended loops will orchestrate both steps internally, rather than splitting them into two separate CLI commands.

## 4. Strict Blocking Mechanisms
**How should cloud quota/canary failure block apply?**
`ws agent-run` already references the `agent_canary_status.json`. If the status is `CODEX_FAILED` (or anything other than `AGENT_CANARY_PASSED`), `ws agent-run` in `--mode detect` will gracefully degrade to `handoff` mode, safely refusing to mutate the codebase and advising human intervention.

**How should explicit Allowed Files be rechecked before apply?**
`ws agent-run`'s internal PowerShell logic (`ws_agent_run.ps1`) actively parses the task file for the `Allowed Files:` boundary list. It strictly passes this boundary to the Codex prompt, instructing the agent to only write to these specific paths.

**How should dirty repo state block apply?**
The agent orchestrator script must enforce a `git diff --quiet` and `git diff --cached --quiet` check on the target repository *before* creating the agent branch. If dirty, it must immediately abort with `BLOCKED_DIRTY_REPO`.

**How should the system prevent applying stale plans?**
By forcing the operator to use `ws agent-run <project> <task>`, the cloud agent dynamically re-reads the task file and workspace state at the moment of execution. It does not blindly consume a `local_plan.md` that might be hours old. If the task file changed, the agent acts on the fresh state.

## 5. Terminal States and Post-Execution
**What terminal states should supervised cloud apply produce?**
- `CODEX_COMPLETED`: Agent successfully executed changes and terminated.
- `CODEX_FAILED`: Agent encountered an error (e.g., compile failure, API timeout).
- `CODEX_NOT_STARTED`: Preflight blocked execution.
- `AGENT_TIMEOUT`: Agent exceeded the `--max-minutes` threshold.

**What should happen after `CODEX_COMPLETED`?**
The operator must review the Git diff on the newly created `agent/<project>/...` branch, execute manual testing, and decide whether to merge, abandon, or iterate.

**What should happen after failure states?**
If `CODEX_FAILED`, `CODEX_NOT_STARTED`, or `AGENT_TIMEOUT` occur, the operator must inspect the `final_report.md` in the `auto_runs/` folder via `ws agent-import <run_folder>`. The loop is considered terminated, and a human must unblock the state.

## 6. Deferred Mechanics
**Why cloud apply remains supervised and foreground-only for now:**
Cloud models are inherently unpredictable. Before detaching them into background loops, the system must prove that the strict file boundaries (`Allowed Files`), timeout mechanisms (`--max-minutes`), and terminal state reporting are perfectly reliable in the foreground under real-world mutation scenarios.

**Why worktrees and parallel execution remain out of scope:**
`ws agent-run` currently mutates the primary Git repository directly (by creating a branch and checking it out). Running parallel cloud agents on the same repository without `git worktree` isolation guarantees checkout collisions, locked indexes, and destructive race conditions. This must be solved before unattended concurrency is unlocked.
