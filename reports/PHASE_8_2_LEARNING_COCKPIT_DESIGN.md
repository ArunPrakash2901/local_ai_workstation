# Phase 8.2 Learning Cockpit Design

## Scope

This phase designs the Learning Cockpit layer for the existing TUI only. It does not implement new commands, invoke Ollama, call cloud providers, or mutate runtime state.

## 1. Problem Solved

The Learning Runner backend is already coherent, but the operator still has to remember long commands, inspect `state.json`, resolve the latest plan or assessment path by hand, and decide which variant of the review loop is active. The Learning Cockpit should turn that from a Bash-memory problem into a state-inspection problem:

- show one learning stronghold at a time
- show the current learning task and evidence trail
- resolve current artifacts automatically
- show the next safe action
- preview the exact backend command before any future execution

The cockpit should reduce command composition work without weakening the existing human-in-the-loop learning model.

## 2. Why The TUI Must Wrap `ws`

The TUI should remain a presentation and orchestration layer around the existing `ws learning-*` commands. It must not duplicate runner logic in Python.

Reasons:

- `ws` already owns the safety gates, artifact writes, explicit-link validation, and state transitions.
- The learning lifecycle already has stable command contracts and durable reports.
- Keeping commands visible preserves auditability: every future cockpit action can be shown as one exact `ws` command.
- Duplicating backend logic in the TUI would create drift, especially around remediation and stale-answer protection.
- If cockpit logic becomes too complex later, the right next backend addition is a read-only `ws learning-status --json`, not a second implementation of the runner inside the UI.

The cockpit may read state and derive display labels, but it must rely on backend commands for all authoritative mutations and final validation.

## 3. Learning Cockpit Screen

The Learning Cockpit screen should show:

- learning stronghold list
- selected learning stronghold
- current task
- latest session plan
- latest tutor session
- latest answer template
- latest imported answers
- latest assessment
- latest decision
- review/remediation status
- next recommended action

Recommended layout:

1. **Learning Strongholds**
   - title
   - ID
   - `current_state`
   - `learning_session_status`
   - last activity timestamp

2. **Selected Stronghold Summary**
   - title
   - current task from `state.json.next_learning_task`
   - most recently completed task from `state.json.last_completed_learning_task`
   - current session status
   - last normal decision
   - last review decision

3. **Artifact Timeline**
   - latest session plan
   - tutor session
   - answer template
   - imported answers
   - assessment
   - decision report
   - review plan
   - review tutor session
   - review answer template
   - review answers
   - review assessment
   - review decision

4. **Integrity Panel**
   - current tutor session path
   - linked answers path
   - `last_learning_answers_for_tutor_session_path`
   - `last_learning_answers_import_success`
   - same fields for review answers when the review lane is active
   - explicit warning when answers are missing or linked to a different tutor session

5. **Recommended Next Action**
   - human-readable next action
   - exact backend command preview
   - execution state: preview-only in the first MVP

6. **Artifact Viewer Entry Points**
   - view selected markdown artifact
   - no editing in the cockpit

## 4. First MVP Actions

Recommended Phase 8.3 MVP should remain read-only plus command preview:

- list learning strongholds
- select one learning stronghold
- refresh state
- view current summary and artifact paths
- view markdown artifacts in the TUI
- compute the recommended next action from existing state fields
- show the exact backend command for that action
- show whether the command is read-only, local runtime mutation, or local Ollama
- do not execute any learning command yet

This keeps the first cockpit milestone useful while avoiding premature action wiring.

## 5. Action Classes

### GREEN Read-Only

- list learning strongholds
- select stronghold
- refresh state
- inspect `state.json`
- view artifact paths
- view markdown artifacts
- show current task and remediation status
- compute/display recommended next action
- render exact command preview

### BLUE Local Ollama

These should be visible in the cockpit as future executable actions but disabled in the first MVP:

- `ws learning-run <learning> --session --model hermes3:8b --from-plan <plan>`
- `ws learning-assess <learning> --model hermes3:8b`
- `ws learning-run <learning> --review-session --model hermes3:8b --from-plan <review_plan>`
- `ws learning-assess <learning> --model hermes3:8b --review`

### Disabled In The First MVP

The first MVP should also preview but not execute local runtime-mutating commands:

- `ws learning-run <learning> --session --dry-run`
- `ws learning-import-answers <learning> --from-file <answers_file>`
- `ws learning-decision <learning>`
- `ws learning-review-session <learning> --dry-run`
- `ws learning-import-answers <learning> --from-file <answers_file> --review`
- `ws learning-decision <learning> --review`
- `ws learning-advance <learning>`

Also permanently out of scope for this cockpit:

- provider/cloud execution
- browser automation
- Codex/Gemini/Claude execution
- unattended multi-step loops
- trading actions

The future action model should distinguish:

- read-only
- local runtime mutation without Ollama
- local Ollama
- disabled/external

But Phase 8.3 should only execute the first class.

## 6. Automatic Artifact Resolution

Resolution should prefer authoritative `state.json` pointers first, then deterministic filename fallback only for artifacts that are not recorded directly.

| Artifact | Preferred Source | Fallback |
|---|---|---|
| latest session plan | `last_learning_session_plan_path` | latest `sessions/*_session_plan.md` |
| latest tutor session | `last_tutor_session_path` | latest `sessions/*_tutor_session.md` |
| latest answer template | derive timestamp from `last_tutor_session_path` | latest `sessions/*_answer_template.md` |
| latest imported answers | `last_learning_answers_path` | latest `sessions/*_human_answers.md` |
| latest assessment | `last_learning_assessment_path` | latest `assessments/assessment_*.md` |
| latest decision report | `last_learning_decision_at` -> `reports/learning_decision_<ts>.md` | latest `reports/learning_decision_*.md` |
| latest review session plan | `last_learning_review_plan_path` | latest `sessions/*_review_session_plan.md` |
| latest review tutor session | `last_review_tutor_session_path` | latest `sessions/*_review_tutor_session.md` |
| latest review answer template | derive timestamp from `last_review_tutor_session_path` | latest `sessions/*_review_answer_template.md` |
| latest review answers | `last_learning_review_answers_path` | latest `sessions/*_human_review_answers.md` |
| latest review assessment | `last_learning_review_assessment_path` | latest `assessments/review_assessment_*.md` |
| latest review decision report | `last_learning_review_decision_at` -> `reports/learning_review_decision_<ts>.md` | latest `reports/learning_review_decision_*.md` |

Rules:

- Display both resolved path and resolution source.
- Treat a missing state pointer plus a fallback file as degraded but inspectable.
- Never infer correctness from newest mtime alone when state carries an explicit relationship.
- Use `state.json` fields as the source of truth for active lane selection and answer linkage.

## 7. Command Preview

Before any future non-read-only execution, the cockpit should show a preview panel containing:

- action label
- exact `ws` command
- selected stronghold path
- resolved artifact paths substituted into the command
- action class: GREEN, local runtime mutation, or BLUE local Ollama
- expected writes
- explicit preconditions
- current disabled/executable status

Examples:

```text
Action: Run tutor session
Class: BLUE local Ollama
Command:
ws learning-run fine-tuning-small-open-source-models --session --model hermes3:8b --from-plan /mnt/d/_ai_brain/strongholds/learning/fine-tuning-small-open-source-models/sessions/20260518_154424_session_plan.md
Expected writes:
- sessions/*_tutor_session.md
- sessions/*_answer_template.md
- responses/*
- evidence/*
- practice_log.md
- loop_log.md
- state.json
Status: Preview only in Phase 8.3
```

For Phase 8.3, preview exists but confirm/execute does not.

## 8. Preventing Stale-Answer Contamination

The cockpit should surface the exact provenance link that the backend already enforces:

- current tutor session path
- latest imported answers path
- tutor session path recorded on those answers
- import success boolean
- same fields for the review lane

The cockpit should show a visible warning when:

- no answers are imported
- `last_learning_answers_import_success` is not `true`
- `last_learning_answers_for_tutor_session_path` does not exactly match `last_tutor_session_path`
- review equivalents do not match in the review lane

Recommended warning text:

> Imported answers are not linked to the current tutor session. Assessment would be unsafe until answers are re-imported.

The cockpit must not try to bypass or weaken the backend hard block. `ws learning-assess` remains the final authority and should continue to reject `LEARNING_ASSESSMENT_REQUIRES_CURRENT_ANSWERS` when linkage is invalid.

## 9. Answer Import Flow

Future execution flow:

1. Operator selects **Import Answers**.
2. TUI asks for an explicit file path.
3. TUI validates only that the path was provided and displays the exact preview command.
4. For the normal lane:
   - `ws learning-import-answers <learning> --from-file <answers_file>`
5. For the review lane:
   - `ws learning-import-answers <learning> --from-file <answers_file> --review`
6. After backend completion, the cockpit refreshes `state.json`, linked-answer fields, and resolved artifacts.

The TUI should not infer answers from clipboard content, auto-select arbitrary files, or silently import the latest local markdown file. The operator must supply the path intentionally.

## 10. Artifact Viewing

Plain mode should support artifact viewing before Textual exists:

- show a numbered artifact list
- allow opening a selected markdown artifact in a read-only viewer
- display path, file type, and content
- provide paging or return-to-menu behavior with stdlib only
- do not edit files

Later enhancements:

- Textual Markdown rendering
- split-pane artifact browser
- search within artifact
- open in external editor only through an explicit operator action

## 11. Plain Mode Before Textual

The cockpit should be fully usable in `--plain` mode before Textual is installed:

- line-based learning stronghold selection
- line-based artifact menu
- one-screen summary
- command preview output
- `r` refresh
- `v` view artifact
- `b` back
- `q` quit

The plain cockpit should use the same data model and resolver functions as any later Textual screen. Textual should improve ergonomics, not correctness.

## 12. What Textual Can Improve Later

Textual can later add:

- side-by-side stronghold list and detail view
- status badges
- keyboard navigation
- live artifact panels
- modal command previews
- Markdown rendering
- explicit confirmation screens
- scrollable command logs

These are presentation upgrades. They should not change the backend command contract or safety model.

## 13. What The Learning Cockpit Must Not Do

- no automatic loop running
- no unattended tutor/assessment chain
- no browser automation
- no Codex/provider execution
- no mutation outside stronghold runtime files
- no project repo mutation
- no silent answer imports
- no assessment when answer linkage is stale or missing
- no dependency installation

## 14. First Implementation Milestone

Recommended Phase 8.3 MVP:

- add Learning Cockpit read-only view to `ws tui --plain`
- list learning strongholds
- select one
- show:
  - current task
  - current session status
  - latest artifacts
  - remediation status
  - answer linkage integrity
  - recommended next action
- show the exact backend command for that next action
- allow read-only markdown viewing
- do not execute the action yet

This is the right next slice because it removes the operator's current path-resolution burden while keeping the cockpit inside the proven read-only boundary established by Phase 8.1 and Phase 8.1.1.
