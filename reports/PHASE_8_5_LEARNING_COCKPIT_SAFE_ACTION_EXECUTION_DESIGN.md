# Phase 8.5 Learning Cockpit Safe Action Execution Design

## Scope

This phase designs the first safe execution boundary for the Learning Cockpit. It does not implement execution, invoke Ollama, or run any learning command.

## 1. Learning Actions Safe To Execute First

The first executable actions should be limited to deterministic local dry-runs that mutate only learning-stronghold runtime files and already have stable backend contracts:

- `ws learning-run <learning_id> --session --dry-run`
- `ws learning-review-session <learning_id> --dry-run`

Also safe:

- artifact viewing
- refresh/status inspection

These actions are the correct first execution slice because they:

- do not call Ollama
- do not touch project repositories
- do not require external files from the operator
- already produce explicit local artifacts and backend classifications
- are easy to revalidate immediately after execution

## 2. Actions That Must Remain Preview-Only

The following should remain visible as previews but not executable from the TUI in the next milestone:

- `ws learning-run <learning_id> --session --model hermes3:8b --from-plan <plan>`
- `ws learning-run <learning_id> --review-session --model hermes3:8b --from-plan <review_plan>`
- `ws learning-decision <learning_id>`
- `ws learning-decision <learning_id> --review`
- `ws learning-import-answers <learning_id> --from-file <answers_file>`
- `ws learning-import-answers <learning_id> --from-file <answers_file> --review`
- `ws learning-assess <learning_id> --model hermes3:8b`
- `ws learning-assess <learning_id> --model hermes3:8b --review`
- `ws learning-advance <learning_id>`

Reasons:

- several require richer confirmation or input UX
- some depend on answer-file provenance
- some use local model inference
- some change progression state rather than merely preparing evidence

## 3. Actions That Must Remain Manual-Only

Manual-only for now:

- completing answer templates
- choosing/importing answer files until the TUI has an explicit path prompt or file picker
- deciding whether to act on local tutor advice
- browser/manual reasoning lanes
- any cloud/provider/agent execution
- any action outside the learning stronghold runtime boundary

These remain manual because the operator is still an active learner, not just an approver.

## 4. Proposed Risk Classes

| Class | Meaning | Examples |
|---|---|---|
| GREEN | read-only/status/artifact viewing | dashboard refresh, artifact view |
| BLUE | local deterministic stronghold mutation | learning dry-run plan generation |
| PURPLE | local Ollama call | tutor session, assessment |
| YELLOW | manual browser/clipboard | browser handoff, copy/import |
| ORANGE | external agent/provider execution | Codex CLI, Gemini CLI, cloud model calls |
| RED | apply/mutation/trading/high-risk | repo apply, destructive mutation, trading execution |

The colour split matters because existing drafts previously grouped local Ollama and deterministic local mutation too closely. They have different failure modes and should not be unlocked together.

## 5. Phase 8.6 MVP Recommendation

Enable only:

- `learning-review-session --dry-run`
- `learning-run --session --dry-run`
- artifact viewing

In plain mode, add one execution affordance:

- `x`: execute the currently recommended action only if it is allowlisted and classified GREEN or BLUE

The allowlist for Phase 8.6 should contain exactly:

```text
ws learning-run <id> --session --dry-run
ws learning-review-session <id> --dry-run
```

Everything else remains preview-only.

## 6. Why Other Actions Stay Disabled

### `learning-assess`

Do not enable yet because it is a PURPLE local-model action and depends on fresh answer linkage. The backend blocks unsafe inputs, but the cockpit should first prove that deterministic execution, logging, refresh, and failure display are stable before it starts launching inference.

### `learning-advance`

Do not enable yet because it changes the learner's progression state. It should require a stronger confirmation flow than a first MVP and should only be considered after the cockpit has demonstrated correct review-lane freshness handling over multiple cycles.

### Review Assessment

Do not enable yet because it combines PURPLE execution with remediation-state interpretation. It is a second-stage capability after ordinary assessment is safe in the cockpit.

### Answer Import Without Path UX

Do not enable answer import until there is an explicit path prompt or file picker. A placeholder like `<answers_file>` must never become an executable command, and auto-selecting an arbitrary latest markdown file would reintroduce evidence contamination risk.

## 7. Required Confirmation Flow

Before any non-read-only execution, the cockpit must show:

- action label
- exact backend command
- risk class
- expected files changed
- current stronghold ID
- current recommendation timestamp/state
- explicit `y/N` confirmation

Example for Phase 8.6:

```text
Action: Generate targeted review session
Risk: BLUE - local deterministic stronghold mutation
Command:
ws learning-review-session fine-tuning-small-open-source-models --dry-run
Expected files changed:
- sessions/*_review_session_plan.md
- practice_log.md
- loop_log.md
- state.json
Execute? [y/N]
```

Default must be **No**.

## 8. Required Execution Logging

Execution should be visible and durable:

- visible TUI log line before execution
- visible TUI result line after execution
- optional append-only local log under `tui/logs/` or `reports/`
- exact command
- timestamp
- risk class
- selected stronghold
- stdout
- stderr
- exit code
- generated artifact path when the backend prints one

For the first implementation, a plain-text or JSONL append-only log is enough. It must stay local and should not be mixed into stronghold evidence unless the backend command itself writes that evidence.

## 9. Required Post-Execution Refresh

After a successful action:

1. rerun dashboard state collection
2. rediscover learning strongholds
3. recompute recommended next action
4. show the backend-generated artifact path
5. show the new command preview

This is important because a successful `--dry-run` changes the next safe command. The cockpit must not leave the operator looking at stale pre-execution guidance.

## 10. Required Failure Handling

Failures must be explicit:

- no silent failures
- show backend classification when available
- preserve full stdout/stderr
- show exit code
- show the command that failed
- do not auto-retry
- do not mutate cockpit-local recommendation state after failure unless a fresh read confirms it

The operator should be able to see whether a failure came from:

- state precondition
- missing artifact
- backend classification
- unexpected shell/process error

## 11. Required Guardrails

- execute only commands from a hardcoded allowlist
- build subprocess arguments as arrays, never shell strings
- no shell interpolation from untrusted fields
- no arbitrary command execution
- no provider/browser/agent commands
- no execution when the recommendation is unknown or ambiguous
- no execution of placeholders such as `<answers_file>`
- no execution of RED, ORANGE, YELLOW, or PURPLE actions in Phase 8.6
- no touching project repositories, worktrees, handoffs, features, or `auto_runs`

The TUI should remain a constrained client of `ws`, not a general shell.

## 12. Avoiding Stale Action Execution

Immediately before execution:

1. refresh stronghold state
2. recompute the recommended action
3. rebuild the exact command preview
4. compare the refreshed preview with the one the operator approved
5. block execution if the recommendation or command changed

Suggested block message:

```text
Recommended action changed during refresh. Execution cancelled; review the updated cockpit state.
```

This is required because a second terminal session or another operator action could update the learning stronghold between preview and confirmation.

## 13. Keeping Plain Mode Usable First

Plain mode is still the baseline interface. Phase 8.6 should work there before Textual exists:

- `l` opens Learning Cockpit
- `x` executes only the current allowlisted GREEN/BLUE recommendation
- plain-text confirmation screen
- stdout/stderr printed in the terminal
- refresh after completion
- return to cockpit summary without requiring mouse or advanced widgets

No Textual dependency should be required for correctness.

## 14. What Textual Can Improve Later

Textual can later improve:

- modal confirmation dialogs
- risk-coloured badges
- split-pane stdout/stderr display
- richer command log
- clickable artifact paths
- better multi-stronghold navigation

These are usability upgrades. The same allowlist, refresh-before-run rule, and confirmation contract must remain unchanged.

## 15. Phase 8.6 Implementation Contents

Recommended Phase 8.6:

- add risk metadata to recommended cockpit actions
- add a hardcoded allowlist for exactly the two BLUE dry-run actions
- add `x` in plain mode for the current recommended action only
- add confirmation screen with exact command and expected writes
- use argument-array subprocess execution
- capture stdout/stderr/exit code
- append a local execution log
- refresh cockpit state after execution
- show generated artifact path from backend output
- refuse execution when:
  - action is not allowlisted
  - action is not GREEN/BLUE
  - recommendation changes after refresh
  - command contains placeholders

Keep disabled:

- all PURPLE local Ollama actions
- answer import
- decision recording
- advancement
- all provider/browser/agent actions

## Summary Recommendation

Phase 8.6 should move the Learning Cockpit from read-only preview to **bounded local dry-run execution only**. That is enough to prove the execution architecture, logging, freshness recheck, and failure display without mixing in model calls, answer ingestion, or progression mutation.
