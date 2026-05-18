# PHASE 8 — TUI OPERATOR COCKPIT DESIGN

**Report type:** Design  
**Status:** DRAFT — Design only. No implementation. No provider invocation.  
**Target path:** `reports/PHASE_8_TUI_OPERATOR_COCKPIT_DESIGN.md`  
**Workstation root:** `D:\_ai_brain`  
**Author lane:** Senior Architect (browser handoff → human review)

---

## Table of Contents

1. [Why a TUI is the Right Next Layer](#1-why-a-tui-is-the-right-next-layer)
2. [Why `ws` Remains the Backend API](#2-why-ws-remains-the-backend-api)
3. [Screen Inventory](#3-screen-inventory)
4. [MVP Scope — What to Build First](#4-mvp-scope--what-to-build-first)
5. [MVP Hard Constraints — What Must Not Be Built](#5-mvp-hard-constraints--what-must-not-be-built)
6. [Artifact Resolution Logic](#6-artifact-resolution-logic)
7. [Learning Runner Flow Guidance](#7-learning-runner-flow-guidance)
8. [Research Runner Flow Guidance](#8-research-runner-flow-guidance)
9. [Graphify Status — Future Lane](#9-graphify-status--future-lane)
10. [Command Execution Logging](#10-command-execution-logging)
11. [Failure Display Model](#11-failure-display-model)
12. [Cloud / Provider Call Prevention](#12-cloud--provider-call-prevention)
13. [Mutation Prevention](#13-mutation-prevention)
14. [Files and Folders the TUI Should Read](#14-files-and-folders-the-tui-should-read)
15. [Files and Folders the TUI Must Never Read by Default](#15-files-and-folders-the-tui-must-never-read-by-default)
16. [Implementation Stack](#16-implementation-stack)
17. [Folder Structure](#17-folder-structure)
18. [Proposed Command](#18-proposed-command)
19. [Phase 8.1 — Read-Only Dashboard](#19-phase-81--read-only-dashboard)
20. [Phase 8.2 — Learning Cockpit](#20-phase-82--learning-cockpit)
21. [Phase 8.3 — Research Cockpit](#21-phase-83--research-cockpit)
22. [Validation Checklist](#22-validation-checklist)

---

## 1. Why a TUI is the Right Next Layer

The workstation backend is functionally mature. `ws` commands are stable, composable, and already encode the operator's safety model. The friction is not in the backend — it is in the human-computer interface at the terminal prompt.

**The current human experience requires:**
- Remembering exact command names across four runner systems
- Manually resolving latest artifact paths (e.g. `ls -t "$LEARNING"/sessions/*_review_session_plan.md | head -1`)
- Composing long Bash one-liners from memory
- No visual confirmation of what is about to run
- No contextual display of system state before choosing an action

A **CLI** (the current state) is the right API surface for scripts, agents, and automation chains. A **TUI** is the right surface for a human operator who needs situational awareness before acting.

The TUI does not replace the CLI. It wraps it. The operator gains:

| Problem (CLI only) | Solution (TUI wraps CLI) |
|---|---|
| Must remember all `ws` subcommands | TUI presents contextually relevant actions only |
| Must resolve artifact paths manually | TUI resolves latest file automatically, shows path |
| No preview before execution | TUI shows command preview screen with risk badge |
| No system state at a glance | TUI home screen shows readiness, strongholds, next action |
| Easy to accidentally run wrong runner | TUI constrains actions to selected stronghold context |

A TUI is specifically appropriate here — rather than a web UI — because:

- The workstation lives in WSL. A TUI is native to that environment.
- The operator works at a terminal. Switching to a browser would break flow.
- Textual renders rich, interactive terminal UIs with keyboard-driven navigation.
- A TUI has zero network surface area, no auth complexity, no deployment overhead.
- It is auditable as plain Python source in the same repo.

---

## 2. Why `ws` Remains the Backend API

The `ws` command dispatcher is the authoritative interface to all workstation logic. The TUI must not replicate, inline, or bypass that logic. The design principle is:

> **The TUI is a human-facing shell around `ws`. Every action the TUI executes must be traceable to an exact `ws` invocation.**

Reasons to preserve `ws` as the backend:

1. **Safety gates already exist in `ws`** — confirmation prompts, dry-run modes, and validation logic live there. Bypassing `ws` would silently remove those gates.
2. **Testability** — `ws` commands can be tested independently in Bash. The TUI does not need to replicate test coverage for backend logic.
3. **Auditability** — every action logged by the TUI is a literal `ws` command string. The operator can reproduce any TUI action at the Bash prompt.
4. **Separation of concerns** — backend logic evolves independently of the UI layer. Adding a new `ws` subcommand does not require TUI changes until the TUI explicitly exposes it.
5. **Agent compatibility** — future agents can call `ws` directly without needing the TUI. The TUI is not a required layer for automation.

The subprocess model is: `subprocess.run(["bash", ws_script_path, *args], capture_output=True, text=True)` — always run through the same `ws` entry point, never calling internal scripts directly.

---

## 3. Screen Inventory

### 3.1 Home / Dashboard

**Purpose:** System at a glance. The operator's first view on launch.

**Content:**
- Workstation readiness summary (from `ws ready` — GREEN or degraded)
- Ollama status: model loaded, context window, last used
- Active strongholds count by type (Learning / Research / Generic)
- Most recently touched stronghold (name, type, last action timestamp)
- Recommended next action (single highlighted call-to-action derived from system state)
- Pending handoffs count (from `ws handoff-status`)
- Git working directory status (untracked, modified file counts)
- Last agent-hygiene run timestamp

**Navigation:** All items are selectable. Selecting a stronghold navigates to its detail screen.

**Risk exposure:** GREEN only. Dashboard reads state, never mutates.

---

### 3.2 Stronghold List

**Purpose:** Browse and select all active strongholds.

**Content:**
- Table view: Name | Type | State | Last Action | Pending Step
- Filterable by type (Learning / Research / Generic)
- Sortable by last-touched timestamp
- Each row shows the single recommended next action label (not the raw command)
- Colour-coded by state: active (green), blocked (yellow), complete (dim)

**Actions available from this screen:**
- Open stronghold detail (navigate to 3.3 or 3.4 depending on type)
- Refresh list (re-runs `ws stronghold-status`)

**Risk exposure:** GREEN only.

---

### 3.3 Learning Stronghold Detail

**Purpose:** Full operator cockpit for a single Learning stronghold.

**Panels:**
- **Header:** Stronghold name, current state, last action timestamp
- **Progress tracker:** Visual step indicator for the full Learning Runner flow (7 steps: Plan → Session → Answers → Assess → Decide → Review → Advance)
- **Latest artifacts panel:** Resolved paths for session plan, tutor session, answer template, assessment, review plan (each shows filename + last-modified timestamp)
- **Recommended action:** The single next step, with human label + command preview + risk badge
- **Available actions list:** All valid actions for this stronghold, grouped by risk colour. ORANGE/RED are shown greyed-out with a lock icon.
- **Log panel:** Last 20 lines of the stronghold's session log

**Actions available:**
- Generate session plan (`ws learning-run <l> --session --dry-run` first, then confirm)
- Generate tutor session (`ws learning-run <l> --session --model hermes3:8b --from-plan <resolved>`)
- Open answer template (opens file in `$EDITOR` or shows in Artifact Viewer)
- Import answers (`ws learning-import-answers <l> --from-file <resolved>`)
- Assess (`ws learning-assess <l> --model hermes3:8b`)
- Decide (`ws learning-decision <l>`)
- Run review session (same flow as session, with `--review-session` flags)
- Import review answers
- Assess review
- Decide review
- Advance (`ws learning-advance <l>`) — requires explicit double-confirmation

**Risk exposure:** All GREEN and BLUE actions enabled. ORANGE/RED locked.

---

### 3.4 Research Stronghold Detail

**Purpose:** Full operator cockpit for a single Research stronghold.

**Panels:**
- **Header:** Stronghold name, current state, source count, last action
- **Source list:** All registered source labels with resolved file paths and timestamps
- **Evidence matrix preview:** Rendered markdown table from latest evidence file (if present)
- **Hypothesis log preview:** Rendered markdown from hypothesis log (if present)
- **Recommended action:** Next step with human label + command preview + risk badge
- **Available actions list:** All valid actions grouped by risk colour

**Actions available:**
- Add source (`ws research-add-source <r> --source-text <file> --label "<label>"`) — requires file picker
- Generate review plan (`ws research-run <r> --review-paper --dry-run` → confirm)
- Run local research notes (`ws research-run <r> --review-paper --model hermes3:8b --source-text <resolved> --from-plan <resolved>`)
- Research decision (`ws research-decision <r>`)
- View evidence matrix (Artifact Viewer)
- View hypothesis log (Artifact Viewer)

**Risk exposure:** GREEN and BLUE enabled. ORANGE/RED locked.

---

### 3.5 Handoff Status

**Purpose:** View all pending and completed handoffs to browser lanes (ChatGPT/Gemini).

**Content:**
- Table: Stronghold | Handoff type | Created timestamp | Status (pending / imported)
- Each row expands to show: handoff file path, prompt summary (first 3 lines), expected response artifact
- Import action: marks handoff as used after operator has manually retrieved browser response

**Note:** The TUI never opens a browser. It only tracks the handoff files and their import state. The YELLOW lane is purely informational here.

**Risk exposure:** GREEN for viewing. YELLOW-labelled import action requires operator confirmation.

---

### 3.6 Readiness / System Health

**Purpose:** Detailed workstation health — a deeper view than the dashboard summary.

**Content:**
- `ws ready` full output (parsed and colour-coded by pass/fail/warn per check)
- `ws agent-hygiene` report (last run output)
- Ollama: model name, server reachable, last inference timestamp
- WSL/Windows bridge status
- Git: current branch, last commit, untracked file count, ignored runtime dirs confirmed
- Runtime folder inventory: strongholds/, handoffs/, features/, auto_runs/ — item counts only, no content

**Actions:**
- Re-run readiness check (`ws ready`)
- Re-run agent hygiene (`ws agent-hygiene`)

**Risk exposure:** GREEN only.

---

### 3.7 Artifact Viewer

**Purpose:** Read and display generated markdown artifacts in-TUI without leaving the cockpit.

**Supported artifact types:**
- Session plans (`*_session_plan.md`)
- Tutor sessions (`*_tutor_session.md`)
- Answer templates (`*_answer_template.md`)
- Assessments (`*_assessment.md`)
- Review plans (`*_review_session_plan.md`)
- Stronghold reports (`*_report.md`)
- Research notes (`*_research_notes.md`)
- Evidence matrices (`*_evidence_matrix.md`)
- Hypothesis logs (`*_hypothesis_log.md`)
- Handoff files (`*_handoff.md`)

**Behaviour:**
- Renders markdown using Textual's Markdown widget
- Shows resolved file path and last-modified timestamp in header
- Scroll with keyboard
- "Open in editor" action passes path to `$EDITOR` (no subprocess risk — operator's own editor)
- Never writes to or modifies the viewed file

**Risk exposure:** GREEN only.

---

### 3.8 Command Preview / Confirmation

**Purpose:** Mandatory gate before any action is executed.

**Content:**
- Human-readable action label (e.g. "Generate tutor session for fine-tuning-small-open-source-models")
- Exact `ws` command string that will be run (monospace, copyable)
- Resolved artifact paths substituted in (operator can verify the right file will be used)
- Risk badge: GREEN / BLUE / YELLOW / ORANGE / RED with plain-language explanation
- Expected output: what file or state change this command will produce
- Estimated duration hint (where known: "~30s Ollama inference" for BLUE actions)
- Two buttons: **Confirm** and **Cancel**
- Keyboard: `Enter` to confirm, `Escape` to cancel

**Behaviour:**
- For BLUE actions: shows a spinner with elapsed time while `ws` runs. Streams stdout to a log panel.
- For GREEN actions: typically fast; shows inline result.
- ORANGE/RED actions: button is disabled. Text reads "Not available in this phase."
- Dry-run option: for any action with a `--dry-run` flag, a secondary button "Preview only (dry-run)" is shown.

**Risk exposure:** This screen is the last safety gate. It never proceeds without `Enter`.

---

## 4. MVP Scope — What to Build First

The MVP is **Phase 8.1: Read-Only Dashboard**. It implements only screens that read state without executing mutations.

### MVP Includes

| Screen | Included in MVP |
|---|---|
| Home / Dashboard | ✅ Full |
| Stronghold List | ✅ Read-only (no action buttons active) |
| Readiness / System Health | ✅ Full |
| Artifact Viewer | ✅ Full (file path passed as arg or selected) |
| Handoff Status | ✅ Read-only |
| Command Preview | ✅ Structure present but only wired to GREEN dry-run actions |
| Learning Stronghold Detail | ✅ Display panels only — no action execution |
| Research Stronghold Detail | ✅ Display panels only — no action execution |

### MVP Green Actions Only

The MVP exposes the following `ws` commands with full execution enabled:

- `ws ready`
- `ws agent-hygiene`
- `ws stronghold-status`
- `ws feature-status`
- `ws handoff-status`
- `ws learning-run <l> --session --dry-run`
- `ws research-run <r> --review-paper --dry-run`

All other commands are displayed with risk badges but execution disabled.

---

## 5. MVP Hard Constraints — What Must Not Be Built

The following must not appear in any MVP milestone:

| Constraint | Rationale |
|---|---|
| No Codex invocation | Phase not reached. ORANGE lane. Disabled. |
| No Gemini CLI invocation | Same as above. |
| No browser automation | Fundamentally outside TUI scope. YELLOW lane is informational only. |
| No trading or capital actions | RED lane. Never implemented in TUI at any phase. |
| No direct script calls (bypassing `ws`) | Breaks audit trail and safety gates. |
| No `.env` or credential file reads | Security boundary. Hard-coded exclusion list in file service. |
| No model file reads | Binary, large, not human-readable. No use case. |
| No mutation of stronghold runtime folders | TUI is a cockpit, not an editor. |
| No automatic execution without preview | Command Preview screen is mandatory for all non-read actions. |
| No network calls from TUI process | TUI itself never calls APIs. Only `ws` subprocess may (and only for known BLUE/ORANGE actions). |

---

## 6. Artifact Resolution Logic

The TUI must resolve "latest artifact" without operator input. The resolution service reads the filesystem deterministically.

### Resolution Rules

For each artifact type, the service uses `glob` + `sorted by mtime descending` + `[0]`.

```
# Pseudocode for resolution service

def resolve_latest(stronghold_path: Path, pattern: str) -> Path | None:
    matches = sorted(
        stronghold_path.glob(pattern),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )
    return matches[0] if matches else None
```

### Artifact Resolution Table

| Artifact | Glob Pattern | Folder |
|---|---|---|
| Latest session plan | `*_session_plan.md` | `sessions/` |
| Latest tutor session | `*_tutor_session.md` | `sessions/` |
| Latest answer template | `*_answer_template.md` | `sessions/` |
| Latest assessment | `*_assessment.md` | `sessions/` |
| Latest review plan | `*_review_session_plan.md` | `sessions/` |
| Latest research source notes | `*_research_notes.md` | `sources/` |
| Latest handoff | `*_handoff.md` | `handoffs/` |
| Latest report | `*_report.md` | `reports/` |
| Latest evidence matrix | `*_evidence_matrix.md` | `evidence/` |
| Latest hypothesis log | `*_hypothesis_log.md` | `.` or `notes/` |

### Resolution Display

In every panel that shows a resolved artifact, the TUI displays:
- Filename (not full path — full path shown on hover or in Artifact Viewer)
- Relative age: "3 hours ago", "yesterday", "5 days ago"
- A warning indicator if the artifact is older than 7 days (may be stale)
- `None found` indicator if no match exists (action requiring this artifact will be disabled)

---

## 7. Learning Runner Flow Guidance

The TUI guides the operator through the full Learning Runner flow as a linear 8-step progress track. The current step is highlighted. Completed steps are checked. Unavailable steps are dimmed.

### Step Track

```
[1] Generate Session Plan   → GREEN (dry-run) → BLUE (execute)
[2] Generate Tutor Session  → BLUE
[3] Open Answer Template    → GREEN (view only)
[4] Import Answers          → BLUE
[5] Assess                  → BLUE
[6] Decide                  → GREEN (reads decision file) → operator confirms
[7] Review (if needed)      → BLUE (repeats steps 1–6 with --review flags)
[8] Advance                 → BLUE (guarded: requires passing decision)
```

### Step State Detection

The TUI infers the current step by checking which artifacts exist:

| Step | Condition to mark complete |
|---|---|
| Plan generated | `*_session_plan.md` exists |
| Tutor session generated | `*_tutor_session.md` exists with mtime > plan mtime |
| Answer template opened | `*_answer_template.md` exists |
| Answers imported | `*_answer_template.md` exists AND a completed answers file is present |
| Assessed | `*_assessment.md` exists with mtime > session mtime |
| Decided | `decision.md` or equivalent decision record exists |
| Review needed | Decision record indicates review required |
| Advanced | `state.md` or stronghold state file shows advanced/complete |

### Action Wiring Per Step

Each step button in the Learning detail screen maps to:

| Step | Human Label | `ws` Command |
|---|---|---|
| 1 (plan) | "Generate session plan" | `ws learning-run <l> --session --model hermes3:8b --from-plan <none>` |
| 1 (dry-run) | "Preview session plan command" | `ws learning-run <l> --session --dry-run` |
| 2 | "Run tutor session" | `ws learning-run <l> --session --model hermes3:8b --from-plan <resolved_plan>` |
| 3 | "View answer template" | Opens Artifact Viewer (GREEN) |
| 4 | "Import answers" | `ws learning-import-answers <l> --from-file <resolved_answers>` |
| 5 | "Run assessment" | `ws learning-assess <l> --model hermes3:8b` |
| 6 | "Record decision" | `ws learning-decision <l>` |
| 7 | "Run review session" | `ws learning-run <l> --review-session --model hermes3:8b --from-plan <resolved_review_plan>` |
| 8 | "Advance learning" | `ws learning-advance <l>` — double-confirm required |

The review sub-flow (step 7) mirrors steps 1–6 with `--review` flags appended where applicable.

---

## 8. Research Runner Flow Guidance

The Research Runner flow is less linear than Learning — sources can be added at any point. The TUI represents it as a two-panel layout: source management (left) and analysis actions (right).

### Source Panel

- Lists all registered sources with label, file path, and timestamp
- "Add source" action: file picker → label input → `ws research-add-source <r> --source-text <file> --label "<label>"`
- No source = all analysis actions disabled (with tooltip: "Add at least one source first")

### Analysis Action Track

```
[1] Generate review plan    → GREEN (dry-run) → BLUE (execute)
[2] Run local research notes → BLUE (per source or across all sources)
[3] Research decision       → GREEN (reads) → operator confirms
[4] View evidence matrix    → GREEN (Artifact Viewer)
[5] View hypothesis log     → GREEN (Artifact Viewer)
```

### Action Wiring

| Step | Human Label | `ws` Command |
|---|---|---|
| 1 (dry-run) | "Preview review plan" | `ws research-run <r> --review-paper --dry-run` |
| 1 (execute) | "Generate review plan" | `ws research-run <r> --review-paper --model hermes3:8b --source-text <resolved> --from-plan <resolved_plan>` |
| 2 | "Run research notes" | `ws research-run <r> --review-paper --model hermes3:8b --source-text <resolved_source> --from-plan <resolved_plan>` |
| 3 | "Record research decision" | `ws research-decision <r>` |
| 4 | "View evidence matrix" | Artifact Viewer → `*_evidence_matrix.md` |
| 5 | "View hypothesis log" | Artifact Viewer → `*_hypothesis_log.md` |

Source selection for step 2 is interactive: if multiple sources exist, the TUI presents a list picker before building the command.

---

## 9. Graphify Status — Future Lane

Graphify is not a stable system at the time of this design. The TUI allocates a reserved panel slot on the Home Dashboard labeled **"Graphify"** that renders as:

```
Graphify         [ Not yet active — Phase 9+ ]
```

When Graphify reaches stable status, this panel will be wired to:
- Graph node count
- Last graph update timestamp
- A "View graph summary" action (GREEN)
- A "Run graph update" action (BLUE, when stable)

The panel placeholder is present in Phase 8.1 so that Phase 9 integration requires only panel content changes, not layout surgery.

---

## 10. Command Execution Logging

Every executed action is logged to a structured append-only log file.

### Log Location

```
tui/logs/tui_execution.log
```

This file is in the `tui/` directory, which is **not** a runtime stronghold folder and **is** tracked by Git (log entries are plain text, not sensitive).

Alternatively, if the workstation already has a centralised log dir: `logs/tui_execution.log`.

### Log Entry Format

Each entry is one JSON line:

```json
{
  "timestamp": "2025-01-15T14:32:01Z",
  "screen": "learning_detail",
  "stronghold": "fine-tuning-small-open-source-models",
  "action": "run_tutor_session",
  "risk": "BLUE",
  "command": "ws learning-run fine-tuning-small-open-source-models --session --model hermes3:8b --from-plan sessions/20250115_session_plan.md",
  "resolved_artifacts": {
    "plan": "sessions/20250115_143000_session_plan.md"
  },
  "exit_code": 0,
  "duration_seconds": 34.2,
  "stdout_lines": 47,
  "stderr_lines": 0
}
```

### Log Display

The TUI Command Log screen (accessible from the navigation bar) shows the last 100 entries in a scrollable table. Each entry is expandable to show full stdout/stderr capture.

---

## 11. Failure Display Model

When a `ws` command returns a non-zero exit code, the TUI shows a **Failure Panel** overlaid on the Command Preview screen.

### Failure Panel Content

- Exit code (prominently displayed)
- Last 20 lines of stderr (monospace, red-tinted)
- Last 20 lines of stdout (monospace, for context)
- The exact command that was run (copyable)
- Suggested recovery action (where known — e.g. "Run `ws ready` to check system state")
- Two options: **Dismiss** and **Copy command to clipboard**

### Failure Does Not Auto-Retry

The TUI never retries a failed command automatically. The operator must explicitly re-run.

### Failure Logging

All failures are written to `tui_execution.log` with `exit_code` non-zero and stderr captured. A separate `tui/logs/tui_failures.log` is maintained with failures only, for easy scanning.

### Common Failure Patterns (and TUI hints)

| Pattern | TUI Hint |
|---|---|
| Ollama not reachable | "Check Ollama is running on the Windows host. Run `ws ready` first." |
| Plan file not found | "No session plan found. Run 'Generate session plan' first." |
| WSL path resolution error | "Check the stronghold path in ws config. Open Readiness screen." |
| Non-zero from dry-run | "Dry-run reported an error. The live command would also fail. Check stderr." |

---

## 12. Cloud / Provider Call Prevention

The TUI enforces a strict **no-cloud-by-default** model.

### Prevention Layers

**Layer 1 — Risk classification at design time**

Every action is classified at definition time in the action registry (`tui/services/action_registry.py`). ORANGE and RED actions are not just hidden — their `execute()` method raises `ActionNotEnabledError` regardless of UI state.

**Layer 2 — Subprocess whitelist**

The subprocess service (`tui/services/runner.py`) maintains an explicit allowlist of permitted `ws` subcommands. Any command not on the list is rejected before execution:

```python
ALLOWED_COMMANDS = {
    "ready", "agent-hygiene", "stronghold-status", "feature-status",
    "handoff-status", "learning-run", "learning-import-answers",
    "learning-assess", "learning-decision", "learning-advance",
    "research-run", "research-decision", "research-add-source",
    "stronghold-report",
    # Phase 8.1 MVP: only dry-run variants of learning-run and research-run
}

PHASE_81_ALLOWED = {
    "ready", "agent-hygiene", "stronghold-status",
    "feature-status", "handoff-status",
    # + dry-run only variants
}
```

**Layer 3 — Codex / Gemini CLI detection**

The runner service checks that the resolved `ws` command does not transitively invoke known cloud CLI tools. If `ws` scripts that call Codex or Gemini are ever run, a warning is surfaced. (This is a belt-and-suspenders check — those commands are not on the allowlist anyway.)

**Layer 4 — No TUI network calls**

The TUI process itself never makes HTTP requests. The `requests` and `httpx` libraries are not imported. Only `subprocess` is used to shell out to `ws`.

---

## 13. Mutation Prevention

### Definition of Mutation

A mutation is any action that:
- Writes to or deletes a file in the strongholds/, handoffs/, features/, or auto_runs/ runtime directories
- Modifies a Git-tracked file
- Appends to a log that affects system state
- Invokes an inference model

GREEN actions are by definition non-mutating. BLUE actions are local-mutating (they write artifacts via Ollama inference). ORANGE/RED actions are external-mutating.

### Prevention Model

1. **All GREEN actions** execute without Command Preview confirmation (they are fast reads — a confirmation would be friction with no benefit). Exception: any GREEN action that writes a file shows preview.

2. **All BLUE actions** require the Command Preview / Confirmation screen. No BLUE action auto-executes.

3. **Advance action** (`ws learning-advance`) requires a **double-confirmation**: the preview screen, and then a second modal: `"This will advance the stronghold state. Are you sure? (Type 'advance' to confirm)"`.

4. **Dry-run first policy**: for any BLUE action that has a `--dry-run` equivalent, the TUI surfaces the dry-run preview button first. The live execution button is secondary.

5. **Read-only file service**: the file reading service (`tui/services/file_reader.py`) opens all files with `open(path, 'r')` — never write mode. The service has no write methods.

---

## 14. Files and Folders the TUI Should Read

The TUI's file service is explicitly scoped to the following paths under `D:\_ai_brain` (mapped as `/mnt/d/_ai_brain` in WSL):

```
_ai_brain/
├── strongholds/              # Runtime stronghold state files and artifacts
│   └── <name>/
│       ├── state.md
│       ├── sessions/         # Learning session artifacts
│       ├── sources/          # Research source files
│       ├── handoffs/         # Handoff tracking files
│       ├── evidence/         # Research evidence artifacts
│       └── reports/          # Stronghold-scoped reports
├── handoffs/                 # Global handoff tracking
├── features/                 # Feature state files
├── reports/                  # Global curated reports (read-only display)
├── logs/                     # Execution logs (read for display)
└── tui/logs/                 # TUI-specific logs (read + append)
```

The TUI reads **metadata and markdown artifacts only**. It does not read binary files, archives, or raw datasets even within the above paths.

---

## 15. Files and Folders the TUI Must Never Read by Default

The following are hard-excluded in the file reader service. Attempts to read these paths raise `ForbiddenPathError` and are logged as security events:

| Path pattern | Reason |
|---|---|
| `**/.env` | Credentials / API keys |
| `**/secrets/**` | Secrets directory |
| `**/credentials/**` | Credential files |
| `**/*.key`, `**/*.pem`, `**/*.cert` | Key material |
| `**/datasets/**` | Raw training data — large, not human-readable in TUI |
| `**/models/**` | Model weight files — binary, multi-GB |
| `**/archives/**` | Compressed archives |
| `**/*.gguf`, `**/*.bin`, `**/*.safetensors` | Model file extensions |
| `**/*.tar`, `**/*.zip`, `**/*.gz` | Archive extensions |
| `**/.git/**` | Git internals |
| `**/node_modules/**` | Not applicable but excluded for safety |
| `**/venv/**`, `**/.venv/**` | Python virtual environments |

The exclusion list is defined in `tui/services/file_reader.py` as a module-level constant and is **not configurable at runtime**.

---

## 16. Implementation Stack

| Layer | Technology | Rationale |
|---|---|---|
| TUI framework | **Textual** (Python) | Native terminal UI, keyboard-driven, composable widgets, Markdown support, active development |
| Language | **Python 3.11+** | Consistent with existing workstation tooling; WSL native |
| Command execution | **`subprocess.run`** | Direct, auditable, no abstraction layer between TUI and `ws` |
| File reading | **Python stdlib** (`pathlib`, `glob`, `open`) | No external dependency needed |
| Markdown rendering | **Textual `Markdown` widget** | Built-in, renders inside TUI without browser |
| State detection | **File system inspection** (mtime, glob) | No database needed; stronghold state is file-system truth |
| Logging | **Python `logging` + JSONL** | Structured, appendable, readable in TUI and externally |
| Configuration | **TOML** (`tui/config.toml`) | Human-readable, no secrets stored |
| Testing | **pytest + Textual test harness** | Unit-testable without launching full TUI |

### Key Textual Widgets Used

- `DataTable` — stronghold list, handoff list, log viewer
- `Markdown` — artifact viewer, report display
- `ProgressBar` / custom step indicator — Learning Runner progress track
- `Log` — live command output streaming
- `Static` — risk badges, status indicators
- `Button` — all actions
- `Input` — label input for research source add
- `DirectoryTree` — file picker (for answer import, source add)
- `Footer` — keyboard shortcut reference

---

## 17. Folder Structure

```
_ai_brain/
└── tui/
    ├── app.py                        # Textual App entry point, routing, global state
    ├── config.toml                   # TUI configuration (paths, phase, enabled risk levels)
    ├── logs/
    │   ├── tui_execution.log         # All executed commands (JSONL)
    │   └── tui_failures.log          # Failed commands only (JSONL)
    ├── screens/
    │   ├── __init__.py
    │   ├── dashboard.py              # Home / Dashboard screen
    │   ├── stronghold_list.py        # Stronghold List screen
    │   ├── learning_detail.py        # Learning Stronghold Detail screen
    │   ├── research_detail.py        # Research Stronghold Detail screen
    │   ├── handoff_status.py         # Handoff Status screen
    │   ├── readiness.py              # Readiness / System Health screen
    │   ├── artifact_viewer.py        # Artifact Viewer screen
    │   ├── command_preview.py        # Command Preview / Confirmation screen
    │   └── command_log.py            # Execution log viewer screen
    ├── services/
    │   ├── __init__.py
    │   ├── runner.py                 # subprocess wrapper around ws; allowlist enforced here
    │   ├── file_reader.py            # Safe file reader with exclusion list
    │   ├── artifact_resolver.py      # Latest-artifact resolution logic
    │   ├── action_registry.py        # All actions with risk classification and command templates
    │   ├── stronghold_scanner.py     # Reads stronghold dirs, returns structured state
    │   └── log_writer.py             # Structured JSONL log writer
    └── widgets/
        ├── __init__.py
        ├── risk_badge.py             # Coloured risk level badge widget
        ├── step_tracker.py           # Linear step progress indicator
        ├── artifact_panel.py         # Resolved artifact display with age
        ├── readiness_panel.py        # System readiness summary widget
        └── stronghold_card.py        # Summary card for a single stronghold
```

### `config.toml` Structure

```toml
[workstation]
root = "/mnt/d/_ai_brain"
ws_script = "/mnt/d/_ai_brain/scripts/ws"

[phase]
current = "8.1"
enabled_risk_levels = ["GREEN"]   # Phase 8.1: GREEN only; 8.2+ adds BLUE

[ui]
theme = "dark"
log_lines_visible = 20
artifact_max_lines = 500

[exclusions]
# Appended to hard-coded exclusion list — operator can add more, never remove
extra_excluded_patterns = []
```

---

## 18. Proposed Command

The TUI is launched via the existing `ws` dispatcher, consistent with the operator's existing muscle memory:

```bash
ws tui
```

This command is added to the `ws` dispatcher as:

```bash
case "$1" in
  tui)
    python3 "$WS_ROOT/tui/app.py" "${@:2}"
    ;;
  ...
esac
```

### Optional Arguments

```bash
ws tui                          # Launch to Home Dashboard
ws tui --stronghold <name>      # Launch directly to stronghold detail
ws tui --screen readiness       # Launch directly to Readiness screen
ws tui --artifact <path>        # Launch directly to Artifact Viewer for given file
```

The TUI process runs in the foreground in the current terminal session. It does not daemonise. `Ctrl+C` or `q` exits cleanly.

---

## 19. Phase 8.1 — Read-Only Dashboard

**Milestone:** TUI read-only dashboard  
**Risk levels enabled:** GREEN only  
**Target:** Operator can launch TUI, navigate all screens, read all system state, and preview (dry-run only) BLUE actions.

### Deliverables

- [ ] `tui/app.py` with Textual App skeleton and screen routing
- [ ] `tui/config.toml` with Phase 8.1 settings
- [ ] `tui/services/file_reader.py` with exclusion list enforced
- [ ] `tui/services/artifact_resolver.py` with all resolution patterns
- [ ] `tui/services/stronghold_scanner.py` reading stronghold dirs
- [ ] `tui/services/runner.py` with Phase 8.1 allowlist (GREEN + dry-run only)
- [ ] `tui/services/action_registry.py` with all actions defined but BLUE/ORANGE/RED disabled
- [ ] `tui/services/log_writer.py`
- [ ] `tui/screens/dashboard.py` — system at a glance
- [ ] `tui/screens/stronghold_list.py` — read-only table
- [ ] `tui/screens/readiness.py` — `ws ready` + `ws agent-hygiene` output display
- [ ] `tui/screens/handoff_status.py` — read-only
- [ ] `tui/screens/artifact_viewer.py` — markdown render
- [ ] `tui/screens/command_preview.py` — dry-run actions only
- [ ] `tui/screens/learning_detail.py` — display panels, no execution
- [ ] `tui/screens/research_detail.py` — display panels, no execution
- [ ] `tui/widgets/` — risk_badge, artifact_panel, readiness_panel, stronghold_card
- [ ] `ws tui` command registered in dispatcher
- [ ] Validation: `ws ready` passes inside TUI display; all screens navigable by keyboard

### Phase 8.1 Does Not Include

- Any BLUE action execution
- Learning or Research runner step buttons active
- Advance action
- Add source action
- Import answers action

---

## 20. Phase 8.2 — Learning Cockpit

**Milestone:** Full Learning Runner flow executable from TUI  
**Risk levels enabled:** GREEN + BLUE  
**Prerequisite:** Phase 8.1 complete and validated.

### Deliverables

- [ ] `tui/services/runner.py` — Phase 8.2 allowlist adds all `learning-*` BLUE commands
- [ ] `tui/screens/command_preview.py` — full confirmation flow with spinner and stdout streaming
- [ ] `tui/screens/command_log.py` — execution log viewer
- [ ] `tui/screens/learning_detail.py` — all step buttons active
- [ ] `tui/widgets/step_tracker.py` — Learning Runner progress indicator
- [ ] Double-confirmation modal for `learning-advance`
- [ ] File picker widget for answer import
- [ ] Failure panel implementation
- [ ] `tui/logs/tui_execution.log` and `tui_failures.log` live logging
- [ ] Dry-run first policy enforced for all BLUE actions
- [ ] Validation: full Learning Runner flow (plan → session → import → assess → decide → advance) navigable and executable end-to-end in TUI

---

## 21. Phase 8.3 — Research Cockpit

**Milestone:** Full Research Runner flow executable from TUI  
**Risk levels enabled:** GREEN + BLUE  
**Prerequisite:** Phase 8.2 complete and validated.

### Deliverables

- [ ] `tui/services/runner.py` — Phase 8.3 allowlist adds all `research-*` BLUE commands
- [ ] `tui/screens/research_detail.py` — all action buttons active
- [ ] Source management panel with file picker and label input
- [ ] Multi-source picker for research notes run (when multiple sources exist)
- [ ] Evidence matrix and hypothesis log rendering in Artifact Viewer
- [ ] `ws research-add-source` wired with file picker → label → command preview
- [ ] Validation: full Research Runner flow (add source → plan → notes → decision → view matrix) navigable and executable end-to-end in TUI

---

## 22. Validation Checklist

Before any phase is considered complete, the following must pass:

```bash
# System readiness
ws ready

# Stronghold state legible
ws stronghold-status

# Handoff tracking readable
ws handoff-status

# No zombie agent artifacts
ws agent-hygiene

# No unintended mutations from TUI session
git status --short       # Should show only tui/ new files and log appends

# No scope creep into tracked files
git diff --stat          # Should show no diffs in scripts/, reports/, or runtime dirs
```

The TUI session itself must produce:
- No mutations to any stronghold runtime folder
- No Git-tracked file modifications
- One or more entries in `tui/logs/tui_execution.log`
- Zero entries in `tui/logs/tui_failures.log` (clean run)

---

*End of design document. No providers invoked. No repos mutated. No strongholds modified. Design only.*
