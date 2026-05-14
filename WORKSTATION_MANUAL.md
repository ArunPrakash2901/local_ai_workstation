# Global AI Workstation Manual

This is your central control plane for local AI development across all projects.

## Overview
The workstation uses **Graphify** for codebase intelligence and **Ollama (Hermes 3 8B)** for local inference. It is designed to be project-agnostic, operating through a registry of projects.

## Directory Structure
- `registry/` - YAML files defining projects, models, and workflows.
- `prompts/` - Markdown templates for different AI tasks.
- `scripts/` - Bash scripts (WSL) to execute workstation commands.
- `runs/` - Timestamped artifacts from every AI interaction.

## Core Commands (WSL)

### Project Management
- **List Projects**: `bash /mnt/d/_ai_brain/scripts/ai_list_projects.sh`
- **View Project Info**: `bash /mnt/d/_ai_brain/scripts/ai_project.sh <project_key>`

### Codebase Intelligence (Read-Only)
- **Global Question**: `bash /mnt/d/_ai_brain/scripts/ai_global_ask.sh "<question>"`
  - Queries the global graph across all indexed projects.
- **Project Question**: `bash /mnt/d/_ai_brain/scripts/ai_ask.sh <project_key> "<question>"`
  - Uses the project's specific Graphify graph.
- **Debug Error**: `bash /mnt/d/_ai_brain/scripts/ai_debug.sh <project_key> <path_to_error_log>`
  - Analyzes logs with project context.
- **Audit Project**: `bash /mnt/d/_ai_brain/scripts/ai_audit.sh <project_key>`
  - Generates an architectural and quality report.

### Feature Development
- **Run Task**: `bash /mnt/d/_ai_brain/scripts/ai_run_task.sh <project_key> <path_to_task_file>`
  - Generates an implementation plan based on the task description.

## Adding a New Project
1.  Open `D:\_ai_brain\registry\projects.yaml`.
2.  Add a new entry following the existing schema.
3.  In WSL, navigate to the project directory and run `graphify update .` to generate the graph.
4.  Update the `status` to `graphed` in `projects.yaml`.

## Safety Rules
- **No Secrets**: Never read `.env` files or credentials.
- **No Raw Data**: `.graphifyignore` blocks large datasets to prevent graph bloat.
- **Local First**: All processing happens on your RTX 4070. No code or data is sent to the cloud.

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

`ws build` is a controlled local-first engineering loop. It reads a markdown task queue, builds a compact Graphify context pack, asks local Hermes for a plan, and writes a build run under `D:\_ai_brain\build_runs`. Plan-only is the default and does not modify files.

```bash
ws build portfolio_website D:\_ai_brain\tasks\MY_TASKS.md --plan-only --max-tasks 1
ws build portfolio_website D:\_ai_brain\tasks\MY_TASKS.md --apply --branch --max-tasks 1
ws build portfolio_website D:\_ai_brain\tasks\MY_TASKS.md --apply --branch --max-tasks 1 --escalate codex
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
- `--apply` allows bounded changes, but only if the local plan contains a machine-checkable unified diff.
- `--branch` creates/uses `ai-build/<project>/<task>-<timestamp>`.
- No commits are made automatically.
- `--max-tasks`, `--max-attempts`, `--max-files`, and `--max-minutes` bound the loop.

Codex escalation is opt-in with `--escalate codex`. The loop creates/redacts a packet and sends it only after local attempts fail. Gemini remains manual packet review only until its CLI is safe non-interactively from WSL. Avoid unattended runs: use `--max-tasks 1`, review `build_report.md`, inspect `final_diff.patch`, and run project tests yourself when risk is medium or higher.

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
4. Run `ws build <project> <task_file> --apply --branch --max-tasks 1`.
5. Review tests and diff.
6. If stuck, run `ws task-review <task_file> --with codex`, inspect/redact the packet, then explicitly run `ws escalate codex latest` only if needed.
7. Apply a bounded fix.
8. Mark the task complete or blocked.
9. Move to the next task with `ws task-next`.

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

## Closed-Loop Auto Runner

`ws auto` is the bounded closed-loop runner for a single task or a small task batch. It keeps the loop local first, applies only bounded changes, and escalates to Codex only when you explicitly allow it.

Plan-only:

```bash
ws auto workstation_control_plane /mnt/d/_ai_brain/tasks/generated/workstation_control_plane_task_001_stabilize_ws_command_documentation.md --plan-only --max-tasks 1
```

Supervised apply:

```bash
ws auto workstation_control_plane <task_file> --apply --branch --max-tasks 1 --max-attempts 2 --max-files 5 --stop-on-fail
```

Closed-loop apply with Codex escalation:

```bash
ws auto workstation_control_plane <task_file> --apply --branch --max-tasks 1 --max-attempts 2 --max-cloud-attempts 1 --max-files 5 --stop-on-fail --auto-escalate codex
```

Rules:
- No auto-commit.
- No auto-push.
- Codex is used only when `--auto-escalate codex` is present.
- Gemini remains manual packet review only for now.
- Claude stays disabled.
- `qwen2.5:32b` remains lab-only and is not loaded automatically.
- `ws auto` writes a full run folder under `D:\_ai_brain\auto_runs`.
- Review `final_report.md`, `local_attempts.md`, `test_output.md`, and `final_diff.patch` before taking the next step.

## Example Usage
```bash
# What projects do I have?
bash /mnt/d/_ai_brain/scripts/ai_list_projects.sh

# Ask about the GSP project
bash /mnt/d/_ai_brain/scripts/ai_ask.sh gsp "How is the quarterly estimation implemented?"

# Debug a simulation error
bash /mnt/d/_ai_brain/scripts/ai_debug.sh simulation ./error.log
```
