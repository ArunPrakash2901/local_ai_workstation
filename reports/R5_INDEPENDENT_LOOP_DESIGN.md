# R5: Independent Loop Design
**Date:** 2026-05-16
**Status:** Design Only (Implementation Deferred)

This document outlines the architecture for independent, unattended AI agent loops on the local workstation. It explicitly handles local-first processing, cloud-fallback degradation, and strict workspace isolation.

## 1. Loop Definitions & Independence
**What counts as an independent loop?**
An independent loop is a fully automated, unattended cycle that selects a task from the inbox, sets up an isolated environment, resolves project boundaries, formulates a plan or applies code changes, commits the results to an isolated branch, and generates a final status report without human intervention until a predefined terminal state is reached.

## 2. Capabilities & Constraints
**Which loops can run with local models only?**
- **Plan-only loops:** Formulating architectural strategies, researching code boundaries via Graphify, splitting tasks, and creating structured plans.
- **Handoff-only loops:** Setting up git branches, scaffolding prompt templates, and preparing explicit "Allowed Files" lists for a human developer to manually execute.

**Which loops require cloud availability?**
- **Cloud-apply loops:** Executing codebase mutations via frontier models (e.g., Codex) that require advanced reasoning beyond the reliable scope of local dense models.

## 3. Concurrency & Safety
**Which loops are safe to run concurrently?**
- Plan-only loops across *different* projects.
- Cloud-apply loops across *different* projects (assuming VRAM and network rate limits permit).

**Which loops must never run concurrently?**
- Loops modifying the same branch.
- Loops touching overlapping files within the same repository.
- Multiple heavy Cloud-apply loops that would immediately trigger API rate limits.

**Why same-repo apply loops require `git worktree` isolation:**
If a long-running agent modifies files in a standard clone, it locks the developer out of the working directory and risks colliding with live edits. `git worktree` provides a separate physical directory linked to the same `.git` database. This allows the agent to mutate, compile, and commit code in total isolation, ensuring the developer's primary workspace remains stable.

## 4. Naming Conventions
- **Branches:** `agent/<project>/<task_num>-<timestamp>`
- **Worktrees:** `D:\_ai_brain\worktrees\<project>_<task_num>_<timestamp>`
- **Run Folders:** `D:\_ai_brain\auto_runs\<timestamp>_<project>_<task_slug>_loop`
- **Reports:** `D:\_ai_brain\reports\LOOP_<timestamp>.md`

## 5. Strict Preflight Checks
Before any loop begins, the following must be verified:
1.  **`ws agent-validate`:** Must pass perfectly.
2.  **`ws agent-hygiene`:** The workstation must be clean of stale processes and detached/orphaned loops.
3.  **Local model health:** Ollama reachable, `hermes3:8b` loaded or loadable.
4.  **Cloud canary status:** `AGENT_CANARY_PASSED` (Only checked if a Cloud-apply loop is requested).
5.  **Git Status:** The target repository or worktree must be perfectly clean.
6.  **Explicit Allowed Files:** Bounded boundaries must be declared in the task file.
7.  **Resource Limits:** `max-files` and `max-minutes` must be strictly defined.
8.  **Project Path:** Repository path must exist.
9.  **Locking:** No stale active run lock exists for the same project/task.

## 6. Execution Modes
- `plan-only`: Local model reads repo, generates architectural plan, exits.
- `cloud-apply`: Local model plans, cloud model applies code, commits, exits.
- `handoff-only`: Prepares branches and instructions for a human.
- `blocked-by-quota`: Immediate degradation mode entered if cloud apply is requested but the canary cache indicates `CODEX_FAILED` due to quota.

## 7. Acceptable Terminal States
- `PLAN_ONLY`
- `HANDOFF_READY`
- `CODEX_COMPLETED`
- `CODEX_FAILED`
- `CODEX_NOT_STARTED`
- `AGENT_TIMEOUT`
- `BLOCKED_CLOUD_QUOTA`
- `BLOCKED_VALIDATION_FAILED`

## 8. Operator Responsibilities
After a loop terminates, the operator must inspect:
- The `final_report.md` within the run folder.
- The Git diff and commits generated on the agent branch.
- Any test failures or linters warnings emitted during the loop's validation phase.

## 9. Failure Handling
**Exhausted Cloud Quota:**
If a Cloud-apply loop is requested but quota is exhausted, the loop must immediately degrade to `BLOCKED_CLOUD_QUOTA` or `HANDOFF_READY`, alerting the operator. It must *not* attempt to invoke Codex.

**Timeouts & Stale Processes:**
- **Timeout:** Mark `AGENT_TIMEOUT`, kill child processes gracefully, leave artifacts intact for operator debugging.
- **Fail:** Mark `CODEX_FAILED` or `BLOCKED_VALIDATION_FAILED`, clean up temporary files, exit cleanly.
- **Orphaned `CODEX_RUNNING`:** Caught by `ws agent-hygiene` on the next run, marked as a stale lock, and requires manual operator intervention to clear.

## 10. Minimum Viable Implementation Plan (Future Commands)
- **`ws loop-plan <project> <task>`**: Orchestrates local-only planning and boundary detection.
- **`ws loop-start <project> <task>`**: Validates preflights, creates worktree, checks canary, executes apply (or degrades to handoff), tears down worktree, writes report.
- **`ws loop-status`**: Lists active and recently terminated loops.
- **`ws loop-report <run>`**: Prints the summary of a specific loop.

## 11. The Night Loop Deferral
Night loops operate completely unattended for 8-12 hours. While daytime loops are independent, they are supervised and can be killed quickly if edge cases arise (e.g., infinite retries, runaway VRAM usage, hallucinated file deletions). Unsupervised night loops multiply the damage potential of these edge cases. Independent daytime loops must demonstrate perfect termination reliability, strict boundary adherence, and perfect hygiene cleanup before night loops can be safely enabled.
