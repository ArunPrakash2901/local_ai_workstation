# Phase 8.7 TUI Visual Interaction Design System

## Design Principle

The TUI should speak in human actions, not Bash commands.

Example:

- user-facing label: `Generate targeted review session`
- hidden backend command: `ws learning-review-session fine-tuning-small-open-source-models --dry-run`

The `ws` layer remains the authoritative backend. The operator-facing layer should feel like an application.

## 1. Why The Current TUI Is Still Too Command-Shaped

The current TUI is functionally safer than the shell, but it still reads like a formatted CLI transcript:

- state is presented as long text blocks
- actions are expressed as command previews
- logs dominate the visual hierarchy
- there is no persistent navigation model
- artifact paths are listed, but not framed as objects the operator can inspect
- the operator sees implementation detail before intention

This means the TUI reduces typing but has not yet reduced cognitive translation.

## 2. Why Bash Commands Must Become Backend Details

Bash commands should remain exact, visible, and copyable, but they should not be the primary UI vocabulary.

Reasons:

- users decide in terms of intent: `Generate review session`, not `learning-review-session --dry-run`
- implementation can evolve without changing the user-facing task model
- hidden commands preserve auditability while reducing visual noise
- safe action gating is easier to explain through labels, badges, and disabled controls than through shell syntax
- the TUI should teach workflow structure, not require command recall

The right model is:

- **foreground:** human action, state, artifact, safety
- **background:** exact backend command, revealed on demand

## 3. Main TUI Layout

The application shell should have five persistent regions:

### Top Header / Status Bar

- product name: `Local AI Workstation`
- current safety mode badges
- readiness summary
- selected stronghold name when applicable
- clock / last refresh

### Left Navigation / Sidebar

- Home
- Learning
- Research
- Strongholds
- Handoffs
- System Health
- Settings

### Main Content Panel

- screen-specific cards, tabs, tables, and artifact viewers
- one primary recommended action at a time

### Bottom Command / Log / Status Drawer

- collapsed by default
- recent actions
- last result
- expandable stdout/stderr
- optional `Show Backend Command`

### Modal / Dialog Layer

- confirmations
- text input
- file path entry
- artifact detail
- failure summaries

## 4. Global Navigation

Primary sidebar sections:

1. `Home`
2. `Learning`
3. `Research`
4. `Strongholds`
5. `Handoffs`
6. `System Health`
7. `Settings`

Expected behavior:

- sidebar always visible in the main shell
- current route highlighted
- unavailable sections still visible but badged `DISABLED` or `COMING LATER`
- route change never performs work by itself

## 5. Breadcrumbs

Breadcrumbs should show location and depth clearly.

Example:

```text
Home › Learning › Fine-tuning small open-source models › Review Session
```

Rules:

- top of main content panel
- every segment except the current page is navigable
- breadcrumb labels use human names, not IDs, unless ambiguity requires suffixing

## 6. Learning Stronghold Tabs

Inside a Learning stronghold:

1. `Overview`
2. `Session`
3. `Review`
4. `Artifacts`
5. `Assessment`
6. `Logs`

Behavior:

- `Overview` is the default
- tabs show small state indicators when useful, e.g. `Review [STALE]`
- keyboard `tab` rotates among focusable panel groups; left/right may switch tabs later

## 7. Core Cards

### Current Task Card

- current task
- last completed task
- session status
- phase lane: session vs review

### Recommended Action Card

- human-readable action label
- risk badge
- one primary action button
- secondary `Show Backend Command`
- disabled reason if unavailable

### Provenance Card

- current tutor session
- linked answers
- `LINKED` or `STALE`
- contamination warning when needed

### Latest Artifacts Card

- session plan
- tutor session
- answer template
- assessment
- decision
- latest review artifacts
- `View` buttons

### Safety Card

- current safety mode
- enabled action classes
- blocked classes
- stale-decision warnings

### Model / Readiness Card

- readiness
- local model availability summary
- provider lane status
- current model action state, even when disabled

## 8. Buttons And Actions

Buttons should be named by outcome, not implementation:

- `Run Safe Dry-Run`
- `Generate Tutor Session`
- `Import Answers`
- `Assess Answers`
- `Generate Review Session`
- `Advance Task`
- `View Artifact`
- `Copy Command`

Design rules:

- buttons include icon or compact visual marker where practical
- primary action appears once, not repeated across the screen
- disabled buttons remain visible with reason text
- buttons map to backend commands only after confirmation and safety evaluation

## 9. Buttons Enabled Now

Enabled now:

- `Run Safe Dry-Run` when it resolves to:
  - `learning-run --session --dry-run`
  - `learning-review-session --dry-run`
- `View Artifact`
- navigation / refresh controls

## 10. Buttons Disabled Now

Disabled with explicit reasons:

- `Generate Tutor Session`
  - disabled because it is a PURPLE local model call
- `Assess Answers`
  - disabled because assessment execution is not yet enabled
- `Import Answers`
  - disabled until file-input UX exists
- `Advance Task`
  - disabled because progression mutation needs a later stronger gate
- browser/provider actions
  - disabled because they are YELLOW/ORANGE lanes
- mutation/apply/trading
  - disabled because they are RED/high-risk or outside TUI scope

Disabled controls should explain the reason inline or through help text.

## 11. Command Preview

Backend commands should be collapsed by default.

Recommended pattern:

```text
[ Show Backend Command ]
```

Expanded state:

```text
Backend Command
ws learning-review-session fine-tuning-small-open-source-models --dry-run

[ Copy Command ]
```

Rules:

- never use the command as the primary button label
- never make the command the only visible action description
- show it on demand for trust, auditability, and manual fallback

## 12. Confirmation Dialogs

Confirmation dialog content:

- human action label
- risk class badge
- expected files changed
- backend command hidden by default under `Show Backend Command`
- explicit `y/N` confirmation

Example:

```text
Generate targeted review session
[BLUE] deterministic local runtime update

Expected changes
- sessions/*_review_session_plan.md
- practice_log.md
- loop_log.md
- state.json

[ Show Backend Command ]

Execute? [y/N]
```

The operator should make a human decision from the label and risk, not from parsing shell syntax.

## 13. Text Input And File Picker Flows Needed

Future form flows:

### Answer File Path

- textbox or file picker
- validate existence
- preview selected path
- bind path into `Import Answers`

### Source Text Path

- path picker for research sources
- plain-text validation

### Source Label

- textbox with required value
- show result preview before submission

### Model Selection

- dropdown/select list
- show current default
- show local availability
- later used for PURPLE actions only

These flows are prerequisites before enabling import-heavy or model-backed actions.

## 14. Artifact Viewer

The artifact viewer should support:

- markdown preview
- open latest plan
- open latest tutor session
- open latest answer template
- open latest assessment
- open latest decision

Additional behavior:

- source path in header
- artifact type badge
- timestamp
- safe read-only mode
- previous/next artifact where meaningful

## 15. Status Badges

Required badges:

- `READ_ONLY`
- `SAFE_DRY_RUN`
- `LOCAL_MODEL`
- `MANUAL_REQUIRED`
- `STALE`
- `LINKED`
- `BLOCKED`
- `DISABLED`

Badges should be short and repeatable across cards, tabs, buttons, and dialogs.

## 16. Risk Classes

| Class | Meaning |
|---|---|
| GREEN | read-only |
| BLUE | deterministic local runtime update |
| PURPLE | local Ollama call |
| YELLOW | manual browser/clipboard |
| ORANGE | external agent/provider execution |
| RED | apply/mutation/trading/high-risk |

Risk class must be attached to every action definition, not inferred late from text.

## 17. Keyboard Shortcuts

- `q` quit
- `r` refresh
- `?` help
- `tab` switch panel/tab
- `enter` activate selected button
- `v` view artifact
- `c` copy command
- `x` execute allowed action
- `esc` back/cancel

Shortcut rules:

- visible in footer/help
- context-aware but consistent
- `x` only acts on the current allowlisted action
- `esc` never executes

## 18. Stdlib Plain Mode Before Textual

Plain mode should still feel designed:

- box-drawing layout
- numbered menus and buttons
- line-input dialogs
- read-only artifact viewer
- confirmation prompts
- breadcrumbs rendered in text
- compact cards with headings and badges

Illustrative sketch:

```text
┌ Local AI Workstation ─────────────── [SAFE_DRY_RUN] [READY] ┐
│ Home › Learning › Fine-tuning small open-source models      │
├──────────────┬───────────────────────────────────────────────┤
│ 1 Home       │ Current Task                                  │
│ 2 Learning   │ Format dataset as JSONL                       │
│ 3 Research   │                                               │
│ 4 Stronghold │ Recommended Action                            │
│ 5 Handoffs   │ [1] Generate targeted review session          │
│ 6 Health     │ [2] Show Backend Command                      │
├──────────────┴───────────────────────────────────────────────┤
│ Logs hidden. Press c to open command drawer.                 │
└──────────────────────────────────────────────────────────────┘
```

The stdlib shell should be intentionally simpler than Textual, but not conceptually different.

## 19. What Textual Improves Later

Textual can later provide:

- real widgets
- tabs
- scrollable panes
- modal dialogs
- selectable tables
- rich markdown viewer
- persistent focus model
- mouse support where useful
- richer status bars and badges

The design system should map one-to-one from plain mode concepts to Textual components so the operator does not relearn the application later.

## 20. Phase 8.8 Recommendation

Implement a visual TUI shell/layout in stdlib plain mode first:

- header
- sidebar/menu
- breadcrumbs
- Learning Cockpit as cards
- buttons rendered as selectable numbered actions
- backend command hidden under `Show Backend Command`
- no new backend capabilities
- preserve the existing safe dry-run execution only

This is the right next phase because the backend boundary is already proven. The next weakness is presentation, not capability.

## Summary

The Local AI Workstation TUI should become a real application shell with human actions in the foreground and `ws` commands behind a disclosure boundary. Phase 8.8 should improve layout, navigation, and affordances without broadening the execution envelope.
