# Build Loop Status

Date: 2026-05-14

## Scope

Implemented a bounded local-first product-building loop under `ws build`.

The loop is intentionally constrained:

- plan-only by default
- no automatic commits
- no deployments
- no database migrations
- no file deletion
- no Gemini automatic escalation
- no Claude support while CLI is unavailable
- Codex escalation only with explicit `--escalate codex`

## Commands

```bash
ws build <project_key> <task_file> [flags]
ws build-status
ws build-runs
ws open-build <latest|run_id>
```

Important flags:

- `--plan-only`
- `--apply`
- `--branch`
- `--max-tasks N`
- `--max-attempts N`
- `--max-files N`
- `--max-minutes N`
- `--escalate codex`
- `--no-escalate`
- `--stop-on-fail`
- `--tests "<command>"`
- `--dry-run`

## Artifacts

Each task run writes:

- `task.md`
- `project_metadata.md`
- `graph_context.md`
- `context_pack.md`
- `local_plan.md`
- `attempts.md`
- `test_output.md` when tests run
- `codex_packet.md` and `codex_response.md` when escalated
- `final_diff.patch` when files changed
- `build_report.md`
- `status.txt`

## Apply Safety

Apply mode only accepts a machine-checkable unified diff from the local plan. The guard checks changed file count, project containment, denied folders/file types, Allowed Files patterns, and destructive/install/migration text.

If the plan is ambiguous or lacks a safe diff, the run is marked `BLOCKED`.

## Smoke Test

Plan-only smoke test completed:

```bash
ws build portfolio_website D:\_ai_brain\tasks\SMOKE_TEST_TASK.md --plan-only --max-tasks 1
```

Run folder:

- `D:\_ai_brain\build_runs\20260514_015226_portfolio_website_001`

Verified:

- `context_pack.md` exists
- `local_plan.md` exists
- `build_report.md` exists
- status is `PLAN_ONLY`
- no new project git status changes were introduced during the smoke test
