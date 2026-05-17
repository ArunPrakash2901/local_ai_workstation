# Phase 2.1: Handoff-New Implementation

Date: 2026-05-17

## Summary

Phase 2.1 adds the first local-only handoff packet surface:

- `ws handoff-new`
- `ws handoff-status`

`handoff-new` creates a packet folder under `D:\_ai_brain\handoffs` with prompt, context, metadata, response placeholder, transcript, and report artifacts. It records local workstation evidence and current Git state, but it does not invoke ChatGPT, Gemini, Codex, Claude, browser automation, clipboard automation, or any apply path.

## Files Changed

- `.gitignore`
- `scripts/ws`
- `scripts/ws_handoff_new.sh`
- `scripts/ws_handoff_status.sh`
- `WORKSTATION_MANUAL.md`
- `reports/PHASE_2_1_HANDOFF_NEW_IMPLEMENTATION.md`

## Commands Added

```bash
ws handoff-new <project_key> <task_file> --target chatgpt|gemini-browser|codex-cli|gemini-cli|local --purpose <purpose>
ws handoff-status
```

## Behavior Implemented

`ws handoff-new`:

- resolves the project from `registry/projects.yaml`
- validates the task file and explicit `Allowed Files`
- snapshots current branch, commit, Git status, and diff stat from the project repo
- finds the latest readiness, hygiene, and worktree-status reports
- records a local readiness state from the latest readiness report
- creates:
  - `prompt.md`
  - `context_pack.md`
  - `metadata.json`
  - `response.md`
  - `transcript.md`
  - `handoff_report.md`
- sets browser targets to `BROWSER_MANUAL_REQUIRED`
- sets `local`, `codex-cli`, and `gemini-cli` targets to `PROMPT_READY`
- records `provider_invocation: false` and `browser_automation: false`

`ws handoff-status`:

- scans local handoff folders
- reads `metadata.json`
- prints recent timestamp, target, purpose, state, and path rows

`handoffs/` is now ignored by Git because packets may later contain prompts, task excerpts, diffs, and responses.

## Validation Run

Commands run:

```bash
bash -n scripts/ws
bash -n scripts/ws_handoff_new.sh
bash -n scripts/ws_handoff_status.sh
ws handoff-new workstation_control_plane /mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md --target chatgpt --purpose next-step
ws handoff-status
ws ready
ws agent-hygiene
ws worktree-status
git status --short
git diff --stat
```

Observed results:

- all three shell syntax checks passed
- `ws handoff-new` created `D:\_ai_brain\handoffs\20260517_214359_chatgpt_next-step`
- the generated packet state was `BROWSER_MANUAL_REQUIRED`
- generated metadata recorded:
  - `provider_invocation: false`
  - `browser_automation: false`
  - `local_readiness_state: READY`
- `prompt.md` was verified as paste-ready, including the task, allowed files, branch/status, latest report paths, constraints, and requested output format
- `context_pack.md` included project/task summary, allowed files, latest readiness/hygiene/worktree-status reports, current Git state, and the local safety boundary
- `ws handoff-status` listed the recent handoff folders
- `ws ready` passed on the validation rerun and wrote `READINESS_20260517_214409.md`
- `ws agent-hygiene` passed with `0` unresolved `CODEX_RUNNING` folders
- `ws worktree-status` reported `2` active worktrees and `0` stale-looking directories
- `git check-ignore -v` confirmed that generated handoff packets are ignored through `handoffs/`

## Limitations

- no clipboard copy support
- no response import support
- no review/classification command
- no CLI provider execution
- no browser automation
- no Graphify query or local-model summarization inside the packet yet
- the current readiness state is derived from the latest saved readiness report rather than a fresh implicit readiness run

## Next Step

Implement the next local-only convenience layer:

- `ws handoff-copy`
- `ws handoff-import`
- later `ws handoff-review`

Keep browser submission manual and keep direct CLI execution deferred until the packet workflow is stable.
