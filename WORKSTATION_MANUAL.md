# Global AI Workstation Manual

This is your central control plane for local AI development across all projects.

## Overview
The workstation uses **Graphify** for codebase intelligence and **Ollama (Hermes 3 8B)** for local inference. Strategic planning is human-gated via high-reasoning browser models (ChatGPT/Gemini). Execution is performed by bounded agents (Codex/Gemini CLI) targeting isolated Git worktrees.

## Daily Workflow
1. `ws ready`: Verify system health (Ollama, GPU, WSL, Registry).
2. `ws agent-hygiene`: Audit and cleanup transient agent artifacts.
3. `ws stronghold-status`: Check active cognitive workspaces.
4. `ws task-status`: Review pending implementation tasks.
5. `ws tui`: Open the read-only operator dashboard when you want a terminal summary view.

---

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

`ws tui --snapshot` prints the dashboard and exits. `ws tui --plain` opens the dependency-free line-based dashboard. `ws tui --textual` requires Textual explicitly. Current policy: Textual is optional, no dependency is installed automatically, and plain/snapshot mode must always remain available.

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
- **Learning Cockpit**: A dedicated view within the TUI for tracking study progress. It provides freshness-aware analysis of the active learning stronghold, keeps normal and review decisions separate, suppresses stale advancement previews, and shows the recommended next command.
- **Plain-mode execution**: `ws tui --plain` can execute only the currently recommended safe dry-run planner command via `x`, limited to `learning-run --session --dry-run` and `learning-review-session --dry-run`.
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
