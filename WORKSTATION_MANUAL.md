# Global AI Workstation Manual

This is your central control plane for local AI development across all projects.

## Overview
The workstation uses **Graphify** for codebase intelligence and **Ollama (Hermes 3 8B)** for local inference. It is designed to be project-agnostic, operating through a registry of projects.

## Directory Structure
- `registry/` - YAML files defining projects, models, and workflows.
- `prompts/` - Markdown templates for different AI tasks.
- `scripts/` - Bash scripts (WSL) to execute workstation commands.
- `runs/` - Timestamped artifacts from every AI interaction.

## Daily Workflow

Use the unified `ws` command from WSL for normal workstation operation:

```bash
ws daily
ws warm
ws status
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
- `ws agent-run <project_key> <task_file>`
- `ws agent-import <run>`
- `ws agent-validate`
- `ws agent-hygiene`
- `ws task-new`
- `ws task-split <prd>`
- `ws task-status`
- `ws task-next [project]`
- `ws task-review <file>`
- `ws task-complete <file>`
- `ws task-block <file>`

Run `ws help` for the canonical live command list and usage summary.

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

Always run `ws redact <packet>` before any manual escalation. `ws escalate` also runs redaction automatically and refuses to send unless the result is `SAFE`. Responses are saved under `D:\_ai_brain\frontier\responses`; logs are saved under `D:\_ai_brain\frontier\logs`.

Supported explicit send commands:

```bash
ws escalate gemini latest
ws escalate codex latest
```

Claude currently reports unavailable unless the CLI is installed. If a provider CLI cannot safely run non-interactively, the workstation writes a response note with the exact manual command instead of hanging.

## Workstation Audit And Cleanup

Cleanup is for `D:\_ai_brain` infrastructure only, not project repositories. The default audit and plan commands are read-only. Nothing is deleted automatically; `cleanup-apply` only archives high-confidence candidates under `D:\_ai_brain\archive\cleanup_<timestamp>` and only when `--apply` is provided.

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

Older `ws auto`, `ws codex-apply`, Codex packet escalation loops, and related patch-generation flows are legacy or experimental unless a later report says otherwise. Gemini remains manual packet review only. Avoid unattended runs: review reports and diffs, keep task boundaries explicit, and run project tests yourself when risk is medium or higher.

Before attempting longer independent runs, use `ws agent-validate` to check the current dispatcher, PowerShell parse health, canary refresh, dry-run terminal state, task allowlist guard, and Git ignore contract. Use `ws agent-hygiene` when you need a read-only report of agent branches, worktrees, run-folder statuses, stale `CODEX_RUNNING` artifacts, and generated-report noise. Timestamped `AGENT_CONTRACT_VALIDATION_*` and `AGENT_HYGIENE_*` reports are generated runtime evidence and ignored by Git; curated summary reports stay tracked.

## Task Lifecycle And Closed Loop Workflow

All task sources should flow into the canonical task folders under `D:\_ai_brain\tasks`: `inbox`, `active`, `generated`, `reviewed`, `completed`, and `blocked`. Tasks can come from manual input, PRDs, audits, Graphify analysis, Codex reviews, Gemini manual reviews, test failures, or build reports.

```bash
ws task-new --project workstation_control_plane --title "Clarify daily docs" --goal "Make the daily workflow obvious"
ws task-split D:\_ai_brain\tasks\workstation_control_plane_prd.md
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

## Deterministic PRD Task Splitting

Structured PRDs and task queues are parsed without an LLM when they already contain task headings such as `## Task 001: Title`, `## Task 002 - Title`, or `## Task 003 Title`.

Use the deterministic splitter first:

```bash
ws task-split /mnt/d/_ai_brain/tasks/workstation_control_plane_prd.md --project workstation_control_plane
ws task-split /mnt/d/_ai_brain/tasks/workstation_control_plane_prd.md --project workstation_control_plane --dry-run
ws task-split /mnt/d/_ai_brain/tasks/workstation_control_plane_prd.md --project workstation_control_plane --to-inbox
```

By default, generated tasks are written under `D:\_ai_brain\tasks\generated`. Use `--to-inbox` when you want the generated tasks promoted into `tasks/inbox` for manual selection. Use `ws task-next` to pick the next task, then run `ws build <project> <task_file> --plan-only --max-tasks 1` before any apply run.

The `--llm` flag is only a placeholder for future freeform PRD splitting. It is not implemented in this phase.

## Example Usage
```bash
# What projects do I have?
ws projects

# Ask about the GSP project
ws ask gsp "How is the quarterly estimation implemented?"

# Debug a simulation error
ws debug simulation ./error.log
```
