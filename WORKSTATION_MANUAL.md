# Global AI Workstation Manual

This is your central control plane for local AI development across all projects.

## Overview
The workstation uses **Graphify** for codebase intelligence and **Ollama (Hermes 3 8B)** for local inference. Strategic planning is human-gated via high-reasoning browser models (ChatGPT/Gemini). Execution is performed by bounded agents (Codex/Gemini CLI) targeting isolated Git worktrees.

## Command Invocation
On Windows PowerShell, `ws` may not be globally on `PATH`.
Use repo-local invocation from `D:\_ai_brain`:

- `.\scripts\ws ...` (if shell association is configured)
- `wsl bash -lc "cd /mnt/d/_ai_brain && ./scripts/ws ..."` (portable fallback)

## Daily Workflow
1. `ws ready`: Verify system health (Ollama, GPU, WSL, Registry).
2. `ws agent-hygiene`: Audit and cleanup transient agent artifacts.
3. `ws stronghold-status`: Check active cognitive workspaces.
4. `ws task-status`: Review pending implementation tasks.
5. `ws tui`: Open the read-only operator dashboard when you want a terminal summary view.

---

## Safe Checks

Use the no-write local safety check before committing changes to the command safety manifest, TUI visibility policy, or related safety metadata. It validates the safety registry and syntax without running workstation workflows.

PowerShell:

```powershell
$env:PYTHONDONTWRITEBYTECODE="1"
python scripts\check_local_safety.py
```

Bash/WSL:

```bash
PYTHONDONTWRITEBYTECODE=1 python scripts/check_local_safety.py
```

`scripts/check_local_safety.py` validates `registry/ws_command_safety.yaml`, command safety schema, safety invariants, known command classifications, TUI visibility helper behavior when importable, and no-write AST syntax checks. It does not execute `ws` commands, run agents, run models, call providers, launch browser automation, run apply/write workflows, write reports/caches/artifacts, or inspect secrets or large data.

`ws ready` is different. It is an operational readiness/status workflow and may write local readiness/status reports. Use it when you want workstation readiness information and accept local report writes. Do not treat `ws ready` as strict no-write; in `READ_ONLY_STRICT` contexts, prefer `scripts/check_local_safety.py`.

| Check | Writes files? | Runs ws? | Runs agents/models/providers? | Purpose |
|---|---:|---:|---:|---|
| `check_local_safety.py` | No | No | No | No-write validation of safety manifest and syntax |
| `ws ready` | Yes, local readiness/status reports | Yes | No unless implementation changes | Operational readiness/status check |

## Product Development Lane (v0.2.1)

Product Development Lane consumes approved Discovery Lane execution queue manifests and converts them into non-executing planning artifacts.

Current support:
- Building product packets, PRDs, wireframe briefs, UI/UX briefs, feature specs, and implementation plans from READY Discovery queues.
- Generating static HTML human-review surfaces for generated artifacts.
- Auditing Product Development Lane structure and review artifacts.

### Commands (WSL preferred)

Build product packet and artifacts (LOCAL_REPORT_WRITE):
```bash
./scripts/ws product-dev build-packet --queue discovery_lane/execution_queues/<queue_id>.json
```

Generate HTML review surfaces (LOCAL_REPORT_WRITE):
```bash
./scripts/ws product-dev review-html --manifest product_development_lane/manifests/<manifest_id>.json
```

Audit review artifacts (PURE_READ):
```bash
./scripts/ws product-dev review-audit
```

Audit lane structure (PURE_READ):
```bash
./scripts/ws product-dev audit
```

### Safety Notes
- `ws product-dev build-packet` writes multiple planning artifacts but does not modify Discovery Lane or project source code.
- `ws product-dev review-html` writes static HTML files under `product_development_lane/review_artifacts/`. HTML surfaces are read-only and do not write decisions back to canonical source.
- `ws product-dev review-audit` is a pure-read audit of generated review artifacts.
- No commands in this lane execute worker prompts, create branches, or call external models/providers.

---

## Product Lane Phase 0 + Phase 1 Slice 5 + Phase 2 Slice 4 + Scope Revision Slice 2

Current Product Lane supports:
- Creating a durable product registry record under `products/<product_id>/product.yaml`
- Listing product records
- Viewing a single product record/status
- Previewing static intake questions (`ws product-questions --dry-run`)
- Previewing intake start (`ws product-intake --dry-run`)
- Starting intake with guarded writes (`ws product-intake --product <id> --confirm`)
- Importing operator-provided intake answers with guarded writes (`ws product-answer-import --product <id> --file <answers_file> --confirm`)
- Previewing deterministic scope draft (`ws product-scope --product <id> --dry-run`)
- Previewing deterministic scope change impact from an operator change file (`ws product-scope-change --product <id> --file <change_file> --dry-run`)
- Recording a scope change decision without revising scope yet (`ws product-scope-change --product <id> --file <change_file> --confirm`)
- Previewing deterministic revised scope from confirmed scope changes (`ws product-scope-revision --product <id> --dry-run`)
- Writing a versioned revised scope lock while preserving the original lock (`ws product-scope-revision --product <id> --confirm`)
- Locking scope with guarded write (`ws product-lock-scope --product <id> --confirm`)
- Previewing deterministic PRD from locked scope (`ws product-prd --product <id> --dry-run`)
- Writing deterministic PRD draft from locked scope (`ws product-prd --product <id> --confirm`)
- Previewing deterministic PRD review (`ws product-prd-review --product <id> --dry-run`)
- Approving deterministic PRD metadata (`ws product-prd-approve --product <id> --confirm`)
- Reading PRD artifact maturity (`ws product-prd-status --product <id>`)
- Previewing deterministic text/ASCII wireframes (`ws product-wireframe --product <id> --dry-run`)
- Previewing Open Design adapter input/sandbox run (`ws product-design-adapter-preview --product <id> --tool open-design --dry-run`)
- Previewing Open Design render schema/sandbox run (`ws product-design-render --product <id> --tool open-design --dry-run`)
- Preparing Open Design sandbox packet files only (`ws product-design-run-prepare --product <id> --tool open-design --confirm`)
- Reading Open Design sandbox packet status (`ws product-design-run-status --product <id> --tool open-design`)
- Previewing Open Design run review artifacts (`ws product-design-run-review --product <id> --tool open-design --dry-run`)
- Writing Open Design run review artifacts (`ws product-design-run-review --product <id> --tool open-design --confirm`)
- Probing Open Design runtime visibility without execution (`ws product-design-runtime-probe --tool open-design --dry-run`)
- Previewing Open Design manual install/evaluation checklist (`ws product-design-install-checklist --tool open-design --dry-run`)
- Showing Open Design runtime visibility report (`ws product-design-runtime-report --tool open-design --dry-run`)

See `products/README.md` for the on-disk registry layout.

Not supported yet:
- write-mode wireframes
- Technical planning
- Build planning
- Cloud handoffs
- Local model calls
- Agent execution

### Commands (WSL preferred)

List products (PURE_READ):

```bash
./scripts/ws product-list
```

Show one product (PURE_READ):

```bash
./scripts/ws product-status <product_id>
```

Preview product creation (no writes, requires `--dry-run`):

```bash
./scripts/ws product-new --type website --title "Portfolio Website Redesign" --dry-run
```

Create product record (GUARDED_WRITE, requires explicit confirmation):

```bash
./scripts/ws product-new --type website --title "Portfolio Website Redesign" --confirm
```

Preview static intake questions (no writes):

```bash
./scripts/ws product-questions --type website --dry-run
```

Preview intake start for an existing product (no writes):

```bash
./scripts/ws product-intake --product <product_id> --dry-run
```

Start intake for an existing product (GUARDED_WRITE):

```bash
./scripts/ws product-intake --product <product_id> --confirm
```

Import operator-provided intake answers (GUARDED_WRITE):

```bash
./scripts/ws product-answer-import --product <product_id> --file <answers_file> --confirm
```

Preview deterministic scope draft (DRY_RUN_ONLY):

```bash
./scripts/ws product-scope --product <product_id> --dry-run
```

Lock immutable scope artifact (GUARDED_WRITE):

```bash
./scripts/ws product-lock-scope --product <product_id> --confirm
```

PowerShell (wrapper around WSL `ws`):

```powershell
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-list'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-status <product_id>'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-new --type website --title "Portfolio Website Redesign" --dry-run'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-new --type website --title "Portfolio Website Redesign" --confirm'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-questions --type website --dry-run'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-intake --product <product_id> --dry-run'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-intake --product <product_id> --confirm'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-answer-import --product <product_id> --file <answers_file> --confirm'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-scope --product <product_id> --dry-run'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-scope-change --product <product_id> --file <change_file> --dry-run'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-scope-change --product <product_id> --file <change_file> --confirm'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-scope-revision --product <product_id> --dry-run'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-scope-revision --product <product_id> --confirm'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-prd --product <product_id> --confirm'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-lock-scope --product <product_id> --confirm'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-prd --product <product_id> --dry-run'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-wireframe --product <product_id> --dry-run'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-design-adapter-preview --product <product_id> --tool open-design --dry-run'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-design-render --product <product_id> --tool open-design --dry-run'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-design-run-prepare --product <product_id> --tool open-design --confirm'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-design-run-status --product <product_id> --tool open-design'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-design-run-review --product <product_id> --tool open-design --dry-run'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-design-run-review --product <product_id> --tool open-design --confirm'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-design-runtime-probe --tool open-design --dry-run'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-design-install-checklist --tool open-design --dry-run'
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-design-runtime-report --tool open-design --dry-run'
```

### Safety Notes
- `ws product-list` is `PURE_READ` (no writes).
- `ws product-status` is `PURE_READ` (no writes).
- `ws product-new` is `GUARDED_WRITE` and creates durable files under `products/<product_id>/`.
- `ws product-questions --dry-run` is `DRY_RUN_ONLY` and writes no files.
- `ws product-intake --dry-run` is `DRY_RUN_ONLY` and writes no files.
- `ws product-intake --confirm` is `GUARDED_WRITE` and writes `intake.md`, `questions.md`, and updates `product.yaml` under `products/<product_id>/`.
- `ws product-answer-import` is `GUARDED_WRITE` and writes `answers.md`, then updates `product.yaml` classification to `SCOPE_READY` or `CLARIFICATION_NEEDED` under `products/<product_id>/`.
- `ws product-scope --dry-run` is `DRY_RUN_ONLY`, requires `SCOPE_READY`, and writes no files.
- `ws product-scope-change --dry-run` is `DRY_RUN_ONLY`, previews impact of a proposed scope correction, writes no files, and does not update product metadata.
- `ws product-scope-change --confirm` is `GUARDED_WRITE`, records a scope change decision under `products/<product_id>/decisions/`, updates revision metadata in `product.yaml`, and marks downstream artifacts stale/needs-revision without editing `scope_lock.md`, `prd.md`, or `answers.md`.
- `ws product-scope-revision --dry-run` is `DRY_RUN_ONLY`, previews revised scope text from confirmed scope change decisions, writes no files, and does not regenerate PRD artifacts.
- `ws product-scope-revision --confirm` is `GUARDED_WRITE`, writes a versioned revised scope lock under `products/<product_id>/scope_locks/`, updates active scope metadata, preserves original `scope_lock.md`, and keeps PRD stale/`NEEDS_REVISION` until a future regeneration flow runs.
- `ws product-lock-scope` is `GUARDED_WRITE`, requires `SCOPE_READY`, writes immutable `scope_lock.md`, and updates `product.yaml` (`state=SCOPE_LOCKED`, `scope_locked_at`, `scope_lock_hash`).
- `ws product-prd --dry-run` is `DRY_RUN_ONLY`, requires `SCOPE_LOCKED`, and writes no files.
- `ws product-prd --confirm` is `GUARDED_WRITE`, requires `SCOPE_LOCKED`, writes immutable `prd.md`, and updates `product.yaml` metadata (`updated_at`, `last_action`, `prd_created_at`).
- `ws product-prd-status` is `PURE_READ` and reports PRD readiness metadata without writing files.
- `ws product-wireframe --dry-run` is `DRY_RUN_ONLY`, requires `SCOPE_LOCKED`, `prd_status=APPROVED`, `scope_lock.md`, `scope_lock_hash`, and `prd.md`, writes no files, and does not create `wireframes.md`.
- `ws product-design-adapter-preview --dry-run` is `DRY_RUN_ONLY`, validates active scope/PRD/wireframe hashes and deterministic wireframe review `PASS`, writes no files, does not create `design_runs/`, and does not execute or install Open Design.
- `ws product-design-render --dry-run` is `DRY_RUN_ONLY`, validates active scope/PRD/wireframe hashes and deterministic wireframe review `PASS`, previews design run schema paths/files, writes no files, does not create `design_runs/`, and does not execute or install Open Design.
- `ws product-design-run-prepare` is `GUARDED_WRITE`, requires explicit `--confirm`, writes only sandbox packet files under `products/<id>/design_runs/open_design/open-design-render-v1/`, and does not execute or install Open Design.
- `ws product-design-run-status` is `PURE_READ`, reports prepared sandbox packet state only, and does not execute or install Open Design.
- `ws product-design-run-review --dry-run` is `DRY_RUN_ONLY`, validates prepared run packet safety fields, previews static review artifact paths, writes no files, and does not execute or install Open Design.
- `ws product-design-run-review --confirm` is `LOCAL_REPORT_WRITE`, writes only static review artifacts under `products/<id>/design_runs/open_design/open-design-render-v1/review/`, does not update `product.yaml`, and does not execute or install Open Design.
- `ws product-design-runtime-probe --dry-run` is `DRY_RUN_ONLY`, reports local runtime PATH/prerequisite visibility only, writes no files, does not execute Open Design, does not execute agent CLIs, and does not install tools.
- `ws product-design-install-checklist --dry-run` is `DRY_RUN_ONLY`, previews manual install/evaluation steps and stop conditions only, writes no files, does not install Open Design, and does not execute package managers.
- `ws product-design-runtime-report --dry-run` is `DRY_RUN_ONLY`, reports operator-friendly runtime visibility only, writes no files, does not execute Open Design, and does not execute package managers.
- Human shortcut for this preview is `/design`; canonical machine command is `ws product-design-adapter-preview --product <id> --tool open-design --dry-run`.
- Planned human subaction is `/design render`; canonical machine command is `ws product-design-render --product <id> --tool open-design --dry-run`.
- Planned human subactions include `/design prepare`, `/design status`, `/design review`, `/design probe`, `/design install-check`, and `/design runtime` mapped to canonical `ws product-design-run-prepare`, `ws product-design-run-status`, `ws product-design-run-review`, `ws product-design-runtime-probe`, `ws product-design-install-checklist`, and `ws product-design-runtime-report`.
- `ws product-new` requires `--confirm` for actual creation; use `--dry-run` first to preview paths and the record.
- `ws product-intake --confirm` requires `--product <product_id>`; use `--dry-run` first.
- `ws product-answer-import --confirm` requires both `--product <product_id>` and `--file <answers_file>`.
- `ws product-scope --dry-run` requires `--product <product_id>` and current state `SCOPE_READY`.
- `ws product-lock-scope --confirm` requires `--product <product_id>`, current state `SCOPE_READY`, and refuses overwrite when `scope_lock.md` or lock metadata already exists.
- `ws product-prd --dry-run` requires `--product <product_id>` and current state `SCOPE_LOCKED`; it previews a deterministic PRD and does not write files.
- `ws product-new` must not be treated as read-only. It does not call agents, models, providers, or browser automation.
- `ws product-intake --confirm` starts intake only; it does not complete intake and does not call agents, models, providers, or browser automation.
- `ws product-answer-import --confirm` imports operator-provided answers only. It does not call agents, models, providers, or browser automation.
- `ws product-scope --dry-run` previews deterministic scope content only. It does not call agents, models, providers, or browser automation and does not update `product.yaml`.
- `ws product-lock-scope --confirm` performs deterministic scope lock only. It does not call agents, models, providers, or browser automation.

### Supported Product Types (Phase 0)
- `website`
- `webapp`
- `dashboard`
- `automation`
- `job-pack`
- `cover-letter`
- `interview-prep`
- `video-script`

### Privacy Note
- `job-pack`, `cover-letter`, and `interview-prep` default to `private: true` in Phase 0.
- No cloud handoff exists in Phase 0.

### Safe Validation

Run the no-write local safety check after changing Product Lane registry code/tests or safety metadata:

```powershell
$env:PYTHONDONTWRITEBYTECODE="1"
python scripts\check_local_safety.py
```

This validates product registry tests and safety invariants without executing `ws` commands, creating real products, or running agents/models/providers.

## Intelligence Commands

### Local Context & Reasoning
`ws ask <project_key> "<question>"`: Answer technical questions about a specific project using local Graphify context.
`ws global "<question>"`: Ask broad questions across all registered projects.
`ws graph <project_key|global> --query "<q>"`: Query the knowledge graph directly for relationships and dependencies.
`ws audit <project_key>`: Generate a technical health report for a codebase.

### Task Management
`ws task-new`: Create a canonical task artifact.
`ws task-split <prd_path> --project <key>`: Decompose a PRD into multiple implementation tasks.
`ws task-status`: Show a summary of task lifecycle counts.
`ws task-next`: Identify and display the next highest-priority task.

---

## Operator TUI

`ws tui` launches the current operator dashboard. Phase 8.1 remains read-only only: it shows readiness, strongholds, handoffs, feature strongholds, and agent hygiene, but it does not invoke providers, run learning or research flows, or perform mutation/apply actions.

```bash
ws tui
ws tui --snapshot
ws tui --plain
ws tui --textual
```

`ws tui --snapshot` prints the dashboard and exits. `ws tui --plain` opens the dependency-free terminal-native cockpit with one-line readiness signal, prioritized learning next-action focus, compact command drawer, persistent safety footer, and a paged artifact browser for full-path/details-on-demand viewing. The layout adapts to wide, medium, and narrow terminals. Backend `ws` commands are hidden by default and can be revealed on demand. `WS_TUI_ICONS=ascii|unicode|auto` controls icon style. `ws tui --textual` requires Textual explicitly. Current policy: Textual is optional, no dependency is installed automatically, and plain/snapshot mode must always remain available.

---

## Generic Strongholds (Phase 5)

A Stronghold is a structured cognitive workspace for a single objective. `ws stronghold-new` initializes a new stronghold with domain-specific templates (learning, product, feature, research, trading-research). Every stronghold includes core artifacts like `contract.md`, `goals.md`, and `constraints.md`. `ws stronghold-status` lists active strongholds and their states.

```bash
ws stronghold-new --type learning|product|feature|research|trading-research --title "<title>"
ws stronghold-status
ws stronghold-intake <stronghold_id_or_path>
ws stronghold-intake-import <stronghold_id_or_path> --from-file <answers_file>
ws stronghold-architect-handoff <stronghold_id_or_path> --target chatgpt|gemini-browser --purpose master-plan
ws stronghold-plan-import <stronghold_id_or_path> --from-handoff latest|<handoff_id_or_path>
ws stronghold-local-checklist <stronghold_id_or_path> --model hermes3:8b
ws stronghold-report <stronghold_id_or_path>
ws stronghold-decision <stronghold_id_or_path>
```

Strongholds for `trading-research` are limited to backtesting and paper trading; no live trading or capital deployment is enabled. `ws stronghold-intake` generates domain-specific questions to establish absolute understanding before planning begins. `ws stronghold-intake-import` parses human answers to update core artifacts and move the stronghold toward `CONTRACT_READY`. `ws stronghold-architect-handoff` generates a browser-ready Senior Architect prompt requesting a master plan. `ws stronghold-plan-import` promotes a Senior Architect response to the authoritative `architect_plan.md`. `ws stronghold-local-checklist` uses a local "Intern" model to convert the master plan into granular operational tasks. `ws stronghold-report` synthesizes the current state into a comprehensive `final_report.md`. `ws stronghold-decision` analyzes the stronghold to classify the next safe state or action.

## Domain Specific Runners (Phase 6 & 7)

### Learning Run
`ws learning-run` orchestrates interactive tutoring sessions within a learning stronghold.

```bash
ws learning-run <stronghold_id_or_path> --session --dry-run
ws learning-run <stronghold_id_or_path> --session --model hermes3:8b --from-plan <session_plan>
ws learning-run <stronghold_id_or_path> --review-session --model hermes3:8b --from-plan <review_plan>
ws learning-import-answers <stronghold_id_or_path> --from-file <answers_file> [--review]
ws learning-assess <stronghold_id_or_path> --model hermes3:8b [--review]
ws learning-decision <stronghold_id_or_path> [--review]
ws learning-advance <stronghold_id_or_path>
ws learning-review-session <stronghold_id_or_path> --dry-run
```

The `--dry-run` command generates a tactical session plan based on the next task in the operational checklist. The model-backed command invokes a local tutor to generate specific exercises and an answer template. human operators must complete the answer template to progress. `ws learning-import-answers` records completed exercises in the stronghold history (use `--review` for review sessions). `ws learning-assess` uses a local model to evaluate human answers and provide feedback (use `--review` for review assessments). **Note**: This command requires that the latest imported answers are **explicitly linked** to the latest tutor session via `state.json`. If an import fails or if you start a new session, you must (re)import your answers to establish this link before assessment is permitted. This prevents evidence contamination. `ws learning-decision` inspects the latest assessment to categorize the next safe learning action (ADVANCE, REVIEW, or REPEAT). Use `--review` for decisions after review assessments. `ws learning-advance` marks the current task as completed and identifies the next study goal. `ws learning-review-session` generates a targeted study plan to address identified knowledge gaps.

### Research Run
`ws research-run` orchestrates structured analysis of technical sources.

```bash
ws research-run <stronghold_id_or_path> --review-paper --dry-run
ws research-run <stronghold_id_or_path> --review-paper --model <model> --source-text <text_file> --from-plan <paper_review_plan>
ws research-decision <stronghold_id_or_path>
ws research-add-source <stronghold_id_or_path> --source-text <text_file> --label "<label>"
```
The `--dry-run` command generates a structured analysis plan for a paper or technical source. It also initializes key research artifacts if missing or empty: `literature_map.md`, `hypothesis_log.md`, `evidence_matrix.md`, and `research_summary.md`. Terminal states include `RESEARCH_REVIEW_PLAN_READY` on success.

The model-backed command uses a local "Research Intern" persona (via Ollama) to process a plain text source file. It generates structured notes, extracts candidate hypotheses, suggests evidence matrix updates, and synthesizes a source summary. Terminal states include `RESEARCH_SOURCE_NOTES_READY`.

`ws research-decision` performs a local, deterministic evaluation of the research evidence. It classifies the stronghold state (e.g., `NEEDS_MORE_SOURCES`, `ENOUGH_FOR_SYNTHESIS`) and generates a summary report under `reports/`.

`ws research-add-source` registers a new plain-text source file into the research stronghold. It copies the source into a `sources/` folder and updates the `literature_map.md` with a `registered_unreviewed` status.

---

## Agent & Loops:
`ws apply-ready <project_key> <task_file>`: Perform strict pre-execution safety and syntax checks.
`ws agent-run <project_key> <task_file> [flags]`: Run a bounded Windows-native agent task targeting isolated worktrees.
`ws agent-run-worktree <k> <t> --worktree <p> --dry-run [flags]`: Prepare worktree agent packet.
`ws agent-status`: Show the status of the Windows agent orchestrator.
`ws agent-canary`: Run a low-risk Codex canary to verify provider connectivity.
`ws agent-import <run_folder>`: Import results from a manual/failed agent run for local analysis.
`ws agent-validate`: Perform an automated contract check on all agent scripts.
`ws agent-hygiene`: Audit and prune stale agent branches and transient folders.

### Isolation & Worktrees
`ws worktree-plan <k> <t>`: Preview the future isolation path for a task.
`ws worktree-create <k> <t> --apply --from-report <r>`: Securely create a new Git worktree for parallel development.
`ws worktree-review <path>`: Perform a read-only audit of a worktree diff against the main branch.
`ws worktree-sync <path> --dry-run`: Preview what is needed to sync a worktree.
`ws worktree-sync <worktree_path> --apply --from-report <dry_run_report>`: Safely align a worktree with the main branch.
`ws worktree-status`: Summarize all active worktrees and recent plans.

---

## Feature Strongholds (Legacy/Internal)

A Feature Stronghold is the feature-level source of truth for one product increment. `ws feature-new` creates the local folder and contract artifacts only; `ws feature-plan` refreshes `current_plan.md` from local feature files, Git state, and workstation reports only; `ws feature-validate` records local readiness evidence and blocks on failed safety checks; `ws feature-local-review` runs a local Ollama model to provide a qualitative reasoning gate before cloud escalation; `ws feature-architect-handoff` generates a browser-ready prompt for a high-reasoning cloud model to create a master implementation plan; `ws feature-handoff` creates a local feature-aware packet without invoking a provider; `ws feature-report` synthesizes a local summary into `final_report.md`; `ws feature-status` lists existing feature strongholds. `ws feature-run --dry-run` performs a read-only supervised preflight check to prove the feature is ready for future mutation. `ws feature-run --apply` generates a final execution handoff (without running autonomous agents) after strictly verifying worktree alignment and dry-run evidence. Planning, validation, handoff generation, and reporting do not run providers or apply behavior. Execution loops and browser automation come later.

```bash
ws feature-new <project_key> --title "<title>" --from-task <task_file>
ws feature-plan <feature_id_or_path>
ws feature-validate <feature_id_or_path>
ws feature-local-review <feature_id_or_path> --model hermes3:8b
ws feature-architect-handoff <feature_id_or_path> --target chatgpt
ws feature-handoff <feature_id_or_path> --target chatgpt --purpose <purpose>
ws feature-report <feature_id_or_path>
ws feature-status
ws feature-run <feature_id_or_path> --dry-run
ws feature-run <feature_id_or_path> --apply --worktree <path> --from-dry-run <feature_run_dry_report>
```

---

### TUI & Dashboards
`ws tui [--snapshot | --plain | --textual]`: Launch the operator dashboard.
- **Learning Cockpit**: A dedicated terminal-native view within the TUI for tracking study progress. It provides freshness-aware analysis of the active learning stronghold, keeps normal and review decisions separate, suppresses stale advancement previews, and presents the recommended next action as a human-readable operator step.
- **Plain-mode execution**: `ws tui --plain` can execute only the currently recommended safe dry-run planner action through the numbered button flow or `x`, limited to `learning-run --session --dry-run` and `learning-review-session --dry-run`.
- **Artifact viewing**: Plain mode includes a learning artifact menu for plans, tutor sessions, answer templates, answers, assessments, decisions, and progress/practice logs. The paged viewer only opens markdown files that resolve inside the selected learning stronghold.
- **Safety**: Snapshot mode stays read-only. Learning model execution, assessment, import, advance, providers, and browser automation remain disabled from the TUI.

## Workstation Audit And Cleanup

Cleanup is for `D:\_ai_brain` infrastructure only, not project repositories. The default audit and plan commands are read-only. `ws audit-workstation` generates a detailed report grouping issues by severity (**HIGH**, **MEDIUM**, **LOW**) and identifies cleanup candidates.

Nothing is deleted automatically; `cleanup-apply` only archives high-confidence candidates under `D:\_ai_brain\archive\cleanup_<timestamp>` and only when `--apply` is provided.

Use this flow:

```bash
ws audit-workstation
ws cleanup-plan
ws cleanup-status
ws cleanup-apply --apply
```

Review the cleanup plan before applying it. The cleanup system does not touch project source folders, model files, project `graphify-out` folders, `.env` files, credentials, raw datasets, or frontier packets unless they are explicitly classified as safe archive candidates.

## Bounded Product Build Loop

`ws build` is the local planning path. It reads a markdown task queue, builds a compact Graphify context pack, asks local Hermes for a plan, and writes a build run under `D:\_ai_brain\build_runs`. Use plan-only as the normal path; it does not modify files.

```bash
ws build portfolio_website D:\_ai_brain\tasks\MY_TASKS.md --plan-only --max-tasks 1
ws build-status
ws build-runs
ws open-build latest
```

## Frontier Handoffs

The workstation uses deterministic context gathering to prepare safe escalation packets.

`ws handoff-new <project_key> <task_file>`: Create a local-only handoff folder under `handoffs/`.
`ws handoff-copy <handoff_id>`: Copy the generated system prompt and context to the Windows clipboard.
`ws handoff-import <handoff_id>`: Ingest the human-pasted response from a browser lane.
`ws handoff-review <latest|handoff_id_or_path>`: Perform a deterministic local-only review of an imported response and classify it as `REVIEW_ACCEPTED` or `REVIEW_REJECTED` based on structural criteria only. This command does not execute the response or verify its technical logic.
`ws handoff-status`: High-level summary of recent handoff packets.

## Example Usage
```bash
# What strongholds do I have?
ws stronghold-status

# Initialize a new research stronghold
ws stronghold-new --type research --title "Agentic RAG"

# Conduct intake
ws stronghold-intake agentic-rag
```
