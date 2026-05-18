# Global AI Workstation Manual

This is your central control plane for local AI development across all projects.

## Overview
The workstation uses **Graphify** for codebase intelligence and **Ollama (Hermes 3 8B)** for local inference. It is designed to be project-agnostic, operating through a registry of projects.

## Directory Structure
- `registry/` - YAML files defining projects, models, and workflows.
- `prompts/` - Markdown templates for different AI tasks.
- `scripts/` - Bash scripts (WSL) to execute workstation commands.
- `runs/` - Timestamped artifacts from every AI interaction.
- `worktrees/` - Generated runtime Git worktrees for isolated loops; keep ignored by Git.

## Daily Workflow
Use the unified `ws` command from WSL for normal workstation operation:

```bash
ws daily
ws warm
ws status
ws ready
ws task-status
ws task-next <project_key>
ws build <project_key> <task_file> --plan-only --max-tasks 1
ws open-build latest
```

After reviewing the plan, run the bounded apply step only when you are ready:

```bash
ws agent-run <project_key> <task_file> --mode detect --branch --max-files 5 --max-minutes 10 --stop-on-fail
```

The operator runs `ws` from WSL. `ws agent-run` then crosses into Windows PowerShell and launches Codex through the Windows `codex.cmd` bridge for the bounded apply step. If unattended execution is unavailable or a manual handoff is needed, inspect the resulting run with:

```bash
ws agent-import <run>
```

## Core Commands (WSL)

### Projects
- **List Projects**: `ws projects`
- **View Project Info**: `ws project <project_key>`

### Intelligence
- **Project Question**: `ws ask <project_key> "<question>"`
- **Global Question**: `ws global "<question>"`
- **Direct Graph Query**: `ws graph <project_key|global>`
- **Audit Project**: `ws audit <project_key>`
- **Debug Error**: `ws debug <project_key> <path_to_error_log>`
- **Run Task**: `ws task <project_key> <path_to_task_file>`
- **Run Build Loop**: `ws build <project_key> <path_to_task_file>`

### Models And KV
- `ws model`
- `ws models`
- `ws use <profile>`
- `ws warm [profile]`
- `ws unload`
- `ws kv`
- `ws kvuse <profile>`
- `ws daily`
- `ws moe`

### Frontier Escalation
- `ws frontier`
- `ws packet <project_key> "<question>"`
- `ws redact <packet>`
- `ws escalate <gemini|codex> <packet>`
- `ws review <project_key> <run>` - reserved; do not use until explicitly enabled
- `ws stuck <project_key> <run>` - reserved; do not use until explicitly enabled

### System And Task Lifecycle
- `ws status`
- `ws runs`
- `ws open-run <id>`
- `ws aliases`
- `ws paths`
- `ws audit-workstation`
- `ws cleanup-plan`
- `ws cleanup-apply --apply`
- `ws cleanup-status`
- `ws build-status`
- `ws build-runs`
- `ws open-build <id>`
- `ws agent-status`
- `ws agent-canary`
- `ws apply-ready <project_key> <task_file>`
- `ws agent-run <project_key> <task_file>`
- `ws agent-import <run>`
- `ws agent-validate`
- `ws agent-hygiene`
- `ws agent-mark-stale-reviewed <run>`
- `ws loop-plan <project_key> <task_file>`
- `ws worktree-plan <project_key> <task_file>`
- `ws worktree-create <project_key> <task_file> --dry-run`
- `ws worktree-create <project_key> <task_file> --apply --from-report <report>`
- `ws worktree-review <worktree_path>`
- `ws worktree-status`
- `ws loop-status`
- `ws loop-start <project_key> <task_file>`
- `ws task-new`
- `ws task-split <prd>`
- `ws task-status`
- `ws task-next [project]`
- `ws task-review <file> --with codex`
- `ws task-complete <file> [note]`
- `ws task-block <file> <reason>`

Run `ws help` for the canonical live public command list and usage summary.

## Legacy Aliases

The older `ai*` aliases remain available only for compatibility with earlier workflows:

```bash
ws aliases
```

They currently include `ailist`, `aiproj`, `aiask`, `aiglobal`, `aigraph`, `aiaudit`, `aidebug`, `aitask`, `aimodels`, `aimodel`, `aiuse`, `aikv`, and `aidaily`. Prefer the matching `ws ...` commands in new documentation, shell history, and daily use.

## Adding a New Project
1.  Open `D:\_ai_brain\registry\projects.yaml`.
2.  Add a new entry following the existing schema.
3.  In WSL, navigate to the project directory and run `graphify update .` to generate the graph.
4.  Update the `status` to `graphed` in `projects.yaml`.

## Safety Rules
- **No Secrets**: Never read `.env` files or credentials.
- **No Raw Data**: `.graphifyignore` blocks large datasets to prevent graph bloat.
- **Local First**: Local models and local context are the default. Cloud models are explicit orchestrators or consultants only when intentionally invoked.

## Local + Cloud MVP Model

Local-first does not mean local-only. The normal split is:

- local Ollama + Graphify handle planning, summarization, task understanding, and privacy-sensitive first-pass work
- `ws build --plan-only` is the local planning lane
- `ws agent-run` is the explicit bounded Codex apply lane
- `ws agent-import` and packet workflows are fallback or review paths

Codex, Gemini, and Claude are orchestrators or frontier consultants only when intentionally invoked. They are not uncontrolled background agents, and they should never receive secrets, raw datasets, or model files.

## Path Abstraction And Future Migration

The live workstation still runs from `D:\_ai_brain` and `/mnt/d/_ai_brain`. Phase 3 added path variables for future migration:

```bash
source /mnt/d/_ai_brain/scripts/ws_env.sh
echo $WS_HOME
echo $MODEL_HOME
ws paths
```

Current values:

- `WS_HOME=/mnt/d/_ai_brain`
- `MODEL_HOME=/mnt/d/ollama/models`
- `WS_PARENT=/mnt/d/Local_AI_Workstation`

`D:\Local_AI_Workstation` is the future parent folder. No live migration has happened yet, no junctions have been created, and old paths remain valid.

## Frontier Escalation Packets

The workstation is local-first by default. Frontier models are explicit consultants only: the control plane can prepare a compact packet, but it does not send anything to Gemini, Codex, or Claude unless you manually decide to do that later.

Use packets when the local model is stuck, when you need a second opinion on architecture, or when a narrow debugging/review question would benefit from a stronger external model. Packet creation uses Graphify context and local workstation metadata, excludes secrets/raw data by design, and saves markdown under `D:\_ai_brain\frontier\packets`.

```bash
ws frontier
ws packet global "Which project should I improve first?"
ws redact <packet>
ws packet gsp "Prepare a review packet for the modelling flow."
ws escalate codex <packet>
```

Always run `ws redact <packet>` before any manual escalation. `ws escalate` also runs redaction automatically and refuses to send unless the result is `SAFE`. Escalation packets now include a **Constraints** section (e.g., 8k context, no direct mutation) to guide the frontier model. 

Responses are saved under `D:\_ai_brain\frontier\responses`; logs are saved under `D:\_ai_brain\frontier\logs`.

Supported explicit send commands:

```bash
ws escalate codex latest
```

Gemini and Claude escalation is currently **manual-only** until safety integration is finalized. If you attempt to escalate to these providers, the workstation will provide the exact command for manual execution rather than sending it automatically.

## Local Handoff Packets

`ws handoff-new` creates a local prompt packet under `D:\_ai_brain\handoffs` for later manual use with browser or CLI lanes. Browser use remains manual, and creating a packet does not invoke ChatGPT, Gemini, Codex, Claude, or any browser automation.

```bash
ws handoff-new <project_key> <task_file> --target chatgpt --purpose next-step
ws handoff-status
```

`ws handoff-status` lists recent local handoff folders and their current states.

`ws handoff-copy <latest|handoff_id_or_path>` copies only the selected packet's `prompt.md` into the Windows clipboard. It does not submit anything to a browser, and browser use remains manual.

`ws handoff-import <latest|handoff_id_or_path> --from-clipboard` imports the current clipboard text into the selected packet's `response.md`, updates local handoff evidence, and still does not invoke any provider or browser automation.

`ws handoff-review <latest|handoff_id_or_path>` performs a deterministic local-only review of an imported response and writes `review.md`. It is rule-based only; it does not invoke a model or change project code.

## Feature Strongholds

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

## Domain Specific Runners (Phase 6)

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

The `--dry-run` command generates a tactical session plan based on the next task in the operational checklist. The model-backed command invokes a local tutor to generate specific exercises and an answer template. human operators must complete the answer template to progress. `ws learning-import-answers` records completed exercises in the stronghold history (use `--review` for review sessions). `ws learning-assess` uses a local model to evaluate human answers and provide feedback (use `--review` for review assessments). `ws learning-decision` inspects the latest assessment to categorize the next safe learning action (ADVANCE, REVIEW, or REPEAT). Use `--review` for decisions after review assessments. `ws learning-advance` marks the current task as completed and identifies the next study goal. `ws learning-review-session` generates a targeted study plan to address identified knowledge gaps.

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

Task files use this format:

```markdown
# Task Queue

## Task 001: Improve README setup instructions
Goal:
Explain the local setup more clearly.

Acceptance Criteria:
- README has a concise setup section.
- Existing commands remain accurate.

Allowed Files:
- README.md
- docs/*

Test Command:
npm test

Risk:
low
```

Plan-only versus apply:

- `--plan-only` creates context and a local Hermes plan only.
- `ws agent-run <project_key> <task_file> --mode detect --branch --max-files <n> --max-minutes <n> --stop-on-fail` is the primary bounded apply path.
- `ws agent-import <run>` is the fallback/manual handoff inspection path.
- `ws build --apply` remains secondary/local-diff-only behavior, not the normal apply workflow.
- No commits are made automatically.

Older `ws auto`, `ws codex-apply`, Codex packet escalation loops, and related patch-generation flows are legacy or experimental unless a later report says otherwise. Gemini remains manual packet review only for now, and older `ws auto` / Codex patch flows are legacy or experimental rather than the operator default.

## Task Lifecycle And Closed Loop Workflow

All task sources should flow into the canonical task folders under `D:\_ai_brain\tasks`: `inbox`, `active`, `generated`, `reviewed`, `completed`, and `blocked`. Tasks can come from manual input, PRDs, audits, Graphify analysis, Codex reviews, Gemini manual reviews, test failures, or build reports.

```bash
ws task-new --project workstation_control_plane --title "Clarify daily docs" --goal "Make the daily workflow obvious"
ws task-split D:\_ai_brain\tasks\workstation_control_plane_prd.md --project workstation_control_plane
ws task-status
ws task-next workstation_control_plane
ws task-review <task_file> --with codex
ws task-complete <task_file> "done after tests"
ws task-block <task_file> "blocked pending clarification"
```

Closed loop:

1. Create or split tasks.
2. Run `ws build <project> <task_file> --plan-only --max-tasks 1`.
3. Review `local_plan.md`.
4. Run `ws agent-run <project> <task_file> --mode detect --branch --max-files <n> --max-minutes <n> --stop-on-fail`.
5. Review the agent report and diff.
6. If a manual handoff or later review is needed, inspect it with `ws agent-import <run>`.
7. Mark the task complete or blocked.
8. Move to the next task with `ws task-next`.

## Independent Loops (MVP)

Independent, unattended agent loops (local-first with cloud-fallback awareness) are currently in an MVP state.

The supervised single-loop start command (`ws loop-start`) is active but strictly restricted to local-only planning loops for safety.

```bash
ws loop-start <project_key> <task_file> --mode local-plan
```

This command enforces strict boundaries, generates a plan using the local model, but **does not** apply codebase mutations, create branches, or invoke Codex.

### Reviewing a Local Loop
When `ws loop-start` completes, it will output paths to its artifacts. To review the loop and decide if it is ready for cloud apply:
1. Inspect the loop-start report for the exact terminal state.
2. Read `local_plan.md` in the generated build folder to see the proposed codebase changes.
3. Read `build_report.md` for any issues found during the local execution.
4. Run `ws apply-ready <project_key> <task_file>` as a final read-only check.
5. If the plan looks correct and `apply-ready` passes, proceed to cloud apply using the supervised bounded `ws agent-run` flow:

```bash
ws agent-run <project_key> <task_file> --mode detect --branch --max-files 5 --max-minutes 10 --stop-on-fail
```

Use the read-only tools to check eligibility for independent loops:

```bash
ws loop-plan <project_key> <task_file>
ws worktree-plan <project_key> <task_file>
ws worktree-create <project_key> <task_file> --dry-run
ws worktree-create <project_key> <task_file> --apply --from-report <dry_run_report>
ws worktree-review <worktree_path>
ws worktree-sync <worktree_path> --dry-run
ws worktree-sync <worktree_path> --apply --from-report <dry_run_report>
ws worktree-status
ws loop-status
```

These commands inspect workstation state, Git status, task boundaries, and future worktree eligibility. `ws worktree-plan` is read-only: it reports the future branch and worktree path but does not create either one. `ws worktree-create --dry-run` previews the later Git commands; `ws worktree-create --apply --from-report <dry_run_report>` creates isolation only after supervised checks pass. It does not run tasks or modify project source files. `ws worktree-review` is read-only and should be used before relying on a created worktree. `ws worktree-sync --dry-run` inspects a worktree to see what Git operations are needed to sync it with main, without modifying anything. After creation, inspect the result with `ws worktree-status`. `ws worktree-status` remains read-only: it summarizes current worktrees and recent plans but does not prune or delete worktrees.

## Future: Night-Run Autonomous Workflow

The design for a bounded autonomous overnight workflow (`ws night-run`) is documented in `plans/NIGHT_RUN_DESIGN.md`. This command is not yet enabled and remains in the design phase. It focuses on safety lanes, strict resource monitoring, and automated redaction guards for multi-task autonomous execution.

## Deterministic & LLM PRD Task Splitting

Structured PRDs and task queues are parsed without an LLM when they already contain task headings such as `## Task 001: Title`, `## Task 002 - Title`, or `## Task 003 Title`.

Use the deterministic splitter first:

```bash
ws task-split /mnt/d/_ai_brain/tasks/workstation_control_plane_prd.md --project workstation_control_plane
ws task-split /mnt/d/_ai_brain/tasks/workstation_control_plane_prd.md --project workstation_control_plane --dry-run
ws task-split /mnt/d/_ai_brain/tasks/workstation_control_plane_prd.md --project workstation_control_plane --to-inbox
```

For unstructured PRDs, use the `--llm` mode to decompose the document using the local model:

```bash
ws task-split /mnt/d/_ai_brain/tasks/unstructured_prd.md --project my_project --llm
```

By default, generated tasks are written under `D:\_ai_brain\tasks\generated`. Use `--to-inbox` when you want the generated tasks promoted into `tasks\inbox` for manual selection. Use `ws task-next` to pick the next task, then run `ws build <project> <task_file> --plan-only --max-tasks 1` before any apply run.

## Example Usage
```bash
# What projects do I have?
ws projects

# Ask about the GSP project
ws ask gsp "How is the quarterly estimation implemented?"

# Debug a simulation error
ws debug simulation ./error.log
```
