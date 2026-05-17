# Phase 3: Feature Stronghold Design

Date: 2026-05-17  
Status: Design only. No feature commands are implemented in this phase.

## Executive Summary

The workstation now has useful step-level primitives: readiness checks, local planning, apply gates, bounded agent runs, worktree inspection, and handoff packets. What it still lacks is a persistent owner for one feature across many attempts.

A **Feature Stronghold** should be that owner: a durable feature folder plus a state machine that keeps the contract, plans, runs, handoffs, validations, failures, fixes, and final evidence together until the feature ends in `PASSED`, `FAILED`, or `BLOCKED`.

The stronghold should not replace the existing commands. It should coordinate them, preserve their artifacts, and make the next safe action obvious without forcing the operator to rebuild feature context from old prompts, scattered reports, and R-number milestones.

## 1. What Is A Feature Stronghold?

A Feature Stronghold is a persistent control point for one feature or product increment. It is neither a one-off task packet nor a temporary run folder. It is the long-lived record of:

- what the feature is meant to achieve
- what evidence proves completion
- what files may change
- what repository state the loop started from
- which plans were proposed
- which apply attempts ran
- which validations passed or failed
- which handoffs were created
- why the loop stopped

Operationally, it is a feature-scoped folder under the workstation plus a machine-readable state file. Conceptually, it is the feature's case file.

## 2. Why Feature-Level State Is Better

Ad hoc prompts, handoffs, and phase reports are useful artifacts, but they are poor feature owners:

- prompts preserve one question, not the whole objective
- handoffs preserve one exchange, not the whole decision history
- `build_runs/` and `auto_runs/` preserve one attempt, not the feature outcome
- R-number reports describe workstation evolution, not a durable product increment
- operators still have to decide which plan, diff, report, and failure belongs together

Feature-level state is better because it gives every later action one canonical context source. A stronghold can answer:

- what are we trying to finish?
- what has already been tried?
- what evidence is still missing?
- why are we blocked?
- is the next action planning, applying, validating, reasoning, or asking a human?

That reduces the operator's role from "message bus and archivist" to "approver at defined gates."

## 3. Folder Structure

Recommended root:

```text
D:\_ai_brain\features\<project_key>\<feature_id_slug>\
```

Recommended example:

```text
D:\_ai_brain\features\workstation_control_plane\stabilize-ws-command-documentation\
```

Recommended subtree:

```text
feature_contract.md
acceptance_criteria.md
allowed_files.md
validation_plan.md
state.json
loop_log.md
current_plan.md
final_report.md
evidence\
prompts\
responses\
runs\
handoffs\
```

The top level should stay small and canonical. Time-varying artifacts belong in named subfolders, not as random sibling files.

## 4. Files Every Feature Should Own

| Path | Purpose |
| --- | --- |
| `feature_contract.md` | objective, background, non-goals, risk, source task/PRD, operator notes |
| `acceptance_criteria.md` | checklist of verifiable completion conditions |
| `allowed_files.md` | explicit path allowlist and denied-path reminders |
| `validation_plan.md` | syntax checks, tests, review checks, diff limits, evidence requirements |
| `state.json` | current state, attempts, blockers, linked artifacts, timestamps, repo snapshot |
| `loop_log.md` | append-only action journal |
| `current_plan.md` | latest approved or candidate feature plan |
| `final_report.md` | terminal summary once the feature ends |
| `evidence/` | validation outputs, screenshots, diff summaries, criteria evidence |
| `prompts/` | prompts generated for local, CLI, or browser reasoning |
| `responses/` | imported or captured responses |
| `runs/` | links or copied summaries for local plans and agent runs |
| `handoffs/` | feature-scoped handoff records or references to global handoff folders |

Design note: phase-one implementation should prefer **references** to existing global run and handoff artifacts rather than copying large payloads. The stronghold should index evidence, not duplicate everything.

## 5. State Machine

Required states:

| State | Meaning |
| --- | --- |
| `CREATED` | stronghold exists; contract captured; no plan yet |
| `PLANNED` | feature decomposed and validation shape defined |
| `LOCAL_PLAN_READY` | local plan artifact exists and awaits review/use |
| `APPLY_READY` | all pre-apply gates passed |
| `APPLY_RUNNING` | supervised apply attempt is active |
| `VALIDATING` | post-apply checks and evidence collection are active |
| `NEEDS_FIX` | validation or review found repairable defects |
| `NEEDS_REASONING` | more analysis is needed before another attempt |
| `HUMAN_APPROVAL_REQUIRED` | next transition crosses an explicit operator gate |
| `BLOCKED` | progress cannot continue without external change |
| `PASSED` | acceptance criteria and validation evidence satisfied |
| `FAILED` | loop exhausted or terminal failure accepted |

Recommended high-level transitions:

1. `CREATED -> PLANNED`
2. `PLANNED -> LOCAL_PLAN_READY`
3. `LOCAL_PLAN_READY -> HUMAN_APPROVAL_REQUIRED`
4. `HUMAN_APPROVAL_REQUIRED -> APPLY_READY`
5. `APPLY_READY -> APPLY_RUNNING`
6. `APPLY_RUNNING -> VALIDATING`
7. `VALIDATING -> PASSED | NEEDS_FIX | NEEDS_REASONING | BLOCKED`
8. `NEEDS_FIX -> PLANNED | LOCAL_PLAN_READY`
9. `NEEDS_REASONING -> HUMAN_APPROVAL_REQUIRED | LOCAL_PLAN_READY`
10. any active state -> `BLOCKED | FAILED`

The system should separate "a technically available next command" from "a permitted next transition." For example, a handoff response may recommend an apply step, but the state must still pass through `HUMAN_APPROVAL_REQUIRED`.

## 6. Command Surface

Recommended long-term commands:

```bash
ws feature-new
ws feature-status
ws feature-plan
ws feature-run --supervised
ws feature-validate
ws feature-handoff
ws feature-import
ws feature-report
```

Suggested responsibilities:

- `feature-new`
  - create the stronghold
  - import a task or authored contract
  - snapshot initial repo state
- `feature-status`
  - show state, blockers, attempts, latest artifacts, next safe action
- `feature-plan`
  - orchestrate local planning and record the resulting plan
- `feature-run --supervised`
  - drive only bounded, foreground apply transitions after gates pass
- `feature-validate`
  - run defined checks and collect evidence
- `feature-handoff`
  - create feature-scoped browser or CLI reasoning packets
- `feature-import`
  - import responses or external evidence into the stronghold
- `feature-report`
  - write/update the final feature report from state and evidence

## 7. Using Existing Primitives

The stronghold should compose current commands rather than reimplement them:

- `ws ready`
  - pre-loop health evidence
  - blocks autonomous progression when local readiness is degraded
- `ws loop-start`
  - local-plan generation lane
  - outputs become entries in `runs/` and feed `current_plan.md`
- `ws apply-ready`
  - final read-only gate before any supervised apply
- `ws agent-run`
  - bounded apply lane once the human gate is passed
- `ws worktree-review`
  - validates any feature worktree before relying on it
- `ws handoff-new`
  - creates browser or CLI reasoning packets when state becomes `NEEDS_REASONING`

Stronghold orchestration should always re-read live primitive outputs. It should not trust stale snapshots when crossing a new gate.

## 8. What Should Be Automated First?

Automate low-risk coordination before execution:

1. feature creation from an existing task file
2. feature status aggregation
3. initial contract extraction
4. allowed-file capture
5. repo snapshot capture
6. validation-plan scaffolding
7. linking of later loop, handoff, and validation artifacts
8. append-only logging

The first valuable automation is not "run models repeatedly." It is "make one feature impossible to lose track of."

## 9. What Must Remain Human-Gated?

Keep these decisions explicit:

- approval of a feature contract
- promotion from local plan to apply
- any branch/worktree mutation until lifecycle tooling is fully proven
- any cloud/browser send
- acceptance of risky diff scope
- merge/keep/abandon decisions
- terminal classification when evidence is ambiguous
- override after repeated failure, quota block, or dirty repo conflict

Even in a later supervised loop, the system should ask for approval at irreversible boundaries rather than merely because a command exists.

## 10. Browser Lane

The browser lane should fit as a reasoning lane, not as the stronghold backbone:

- first mode: manual browser use through feature-linked handoff packets
- later mode: optional experimental browser automation behind an explicit flag
- never: browser automation as the safety-critical path

The stronghold should store:

- which browser target was used
- prompt path
- copy/import timestamps
- imported response
- classification of the response
- whether human approval is still required

If browser automation is ever explored, it should be replaceable without changing feature state semantics.

## 11. Codex CLI And Gemini CLI

CLI providers should become optional reasoning or execution lanes, each with a clear contract:

- `codex-cli`
  - later review/reasoning through feature handoffs
  - separate from bounded mutation in `ws agent-run`
- `gemini-cli`
  - later architecture/reasoning/synthesis lane
- `claude-code`
  - targetable in design, but currently unavailable

Future CLI automation should:

- record exact prompt, stdout, stderr, exit code, and provider state
- refuse unavailable providers
- separate read-only reasoning from mutation-capable apply lanes
- never erase the operator gate before mutation

## 12. Local Ollama And Graphify

Local context should remain the first lane:

- Graphify supplies repo structure and feature-relevant code context
- Ollama supplies local summarization, local planning, and compression when healthy
- the stronghold keeps a compact local context snapshot before asking any cloud/browser lane
- degraded local readiness should be logged, not silently bypassed with an automatic cloud call

Local tools are especially valuable for:

- extracting initial feature summaries
- comparing new failures with earlier attempts
- pruning repeated context
- deciding what evidence is worth sending out

## 13. Validation Model

Validation must be feature-specific but standardized in shape.

Each feature should define:

- syntax checks
- lint/compile checks
- unit/integration tests
- allowed-file enforcement
- Git diff size or file-count limits
- acceptance-criteria evidence requirements
- manual review requirements when needed

Recommended evidence types:

- command output files
- diff stat snapshots
- changed-file lists
- test logs
- screenshots when UI criteria matter
- criterion-by-criterion result table

Recommended validation order:

1. syntax/format sanity
2. repo cleanliness and branch/worktree legitimacy
3. changed-file allowlist
4. targeted tests
5. acceptance criteria evidence
6. final diff review

`PASSED` should require explicit evidence for every acceptance criterion, not just a green command.

## 14. Loop Stop Conditions

The stronghold should stop or pause on:

- max attempts reached
- same failure repeated without materially new plan
- dirty repo conflict
- quota blocked
- provider unavailable
- local readiness degraded beyond defined tolerance
- validation failure unresolved
- worktree review not `READY`
- diff exceeds allowed-file or size boundaries
- human approval required
- operator-declared stop

Recommended distinction:

- `BLOCKED`
  - external condition or unresolved precondition
- `FAILED`
  - terminal conclusion after attempts or criteria failure
- `HUMAN_APPROVAL_REQUIRED`
  - valid next action exists, but automation is not authorized to take it

## 15. Preventing Messy Directories

Use a strict storage policy:

- one feature root per feature
- canonical top-level filenames only
- append-only logs instead of ad hoc notes
- timestamped subfolders under `runs/`, `handoffs/`, `prompts/`, `responses/`, and `evidence/`
- no loose scratch files at the feature root
- machine-readable indexes in `state.json`
- feature ids derived from stable slugs, not arbitrary titles
- ignore generated feature runtime artifacts from Git unless a curated report is intentionally promoted
- retention policy later for completed/failed feature folders, but no automatic deletion

The stronghold should organize evidence by lifecycle role, not by whichever command happened to emit it.

## 16. Logging Every Action

Every action should append to `loop_log.md` and update `state.json`.

Minimum log fields:

- timestamp
- actor or lane (`local`, `browser`, `codex-cli`, `gemini-cli`, `agent-run`, `human`)
- prior state
- action
- result
- artifact paths
- validation or blocker summary
- next recommended action

`state.json` should keep normalized pointers for the current canonical artifacts, while `loop_log.md` remains the readable audit trail. Nothing important should depend on shell history.

## 17. First MVP

Recommended first MVP, implemented later:

```bash
ws feature-new <project_key> --title "<title>" --from-task <task_file>
ws feature-status
```

The MVP should:

- create the feature folder
- derive a stable feature slug
- copy or summarize the task into the contract files
- extract allowed files and acceptance criteria
- scaffold the validation plan
- snapshot the initial repo state
- write initial `state.json`
- initialize `loop_log.md`
- show the feature through `feature-status`

The MVP should **not**:

- run apply
- launch agents
- create worktrees
- automate browsers
- invoke cloud providers
- mutate project repos

That is the correct first slice because it proves the stronghold can own feature state before it is trusted to coordinate feature execution.

## Recommended Later Sequencing

1. implement `feature-new`
2. implement `feature-status`
3. add stronghold artifact linking for existing runs and handoffs
4. add `feature-plan`
5. add `feature-validate`
6. add `feature-handoff` and `feature-import`
7. only then design `feature-run --supervised`

## Validation Run

Requested validation performed on 2026-05-17:

- `ws ready`
  - passed
  - Ollama reachable
  - Gemini and Codex detected
  - Claude not found
- `ws agent-hygiene`
  - current branch: `main`
  - agent branches: `12`
  - unresolved `CODEX_RUNNING` folders: `0`
  - reviewed `CODEX_RUNNING` folders: `4`
- `ws worktree-status`
  - active worktrees: `2`
  - stale-looking directories: `0`
- `ws handoff-status`
  - latest browser packet: `COPIED_TO_CLIPBOARD`
  - earlier browser packets: `BROWSER_MANUAL_REQUIRED`
- `git status --short`
  - existing workstation edits present before this design:
    - modified `WORKSTATION_MANUAL.md`
    - modified `scripts/ws`
    - untracked `reports/PHASE_2_2_HANDOFF_COPY_IMPLEMENTATION.md`
    - untracked `scripts/ws_handoff_copy.sh`
- `git diff --stat`
  - existing tracked diff before this design:
    - `WORKSTATION_MANUAL.md | 2 ++`
    - `scripts/ws | 4 ++++`

No feature command was implemented, no provider was invoked, no apply path was run, no browser automation was used, no worktree was created, and no project repository was modified.
