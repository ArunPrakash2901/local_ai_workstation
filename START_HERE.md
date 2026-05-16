# AI Workstation Control Centre

Welcome to your optimized local AI workstation.
Everything is configured for stable, low-latency AI assistance on your RTX 4070 (8GB).

## Core Philosophy
- **Ollama (`hermes3:8b`)** is your local driver. It runs at ~50 tokens/second with an 8k context window.
- **Graphify** is your project brain. It chunks large codebases into queryable knowledge graphs so you don't blow up your 8GB VRAM with massive 32k+ prompts.
- **Windows** is your host (where Ollama runs).
- **WSL (Ubuntu)** is your tooling layer (where Graphify and scripts run).

---

## 1. How to Start Daily Work

Start from WSL with the unified `ws` command:

```bash
ws daily
ws warm
ws status
```

- `ws daily` restores the safe daily model and KV-cache profile.
- `ws warm` preloads the active model so the first request is fast.
- `ws status` checks workstation health and shows the active model.

Ollama should start with Windows. If it is not running, open the Ollama app first, then rerun the commands above.

The older `ai*` shell aliases are still supported for compatibility, but they are legacy names. Prefer `ws ...` commands for daily work and use `ws aliases` only when you need to inspect those old aliases.

For normal product work, continue from startup into the same daily flow:

```bash
ws task-status
ws task-next <project_key>
ws build <project_key> <task_file> --plan-only --max-tasks 1
ws open-build latest
ws agent-run <project_key> <task_file> --mode detect --branch --max-files 5 --max-minutes 10 --stop-on-fail
```

That sequence is the default operator path: restore the workstation, choose one task, inspect the local plan, then run the bounded apply step only when ready.

---

## 2. Using Graphify (Project Brain)

Graphify is installed inside an isolated Python environment in WSL.

**To update a project's graph after you write new code:**
1. Open WSL (`wsl`)
2. Navigate to your project (e.g., `cd /mnt/d/portfolio_website`)
3. Run the helper alias or activate the environment and run:
   ```bash
   source /mnt/d/_ai_brain/runtimes/graphify_venv/bin/activate
   graphify update .
   ```

**To ask questions about a codebase:**
Use your AI assistant (Gemini/AntiGravity) and simply ask:
> "Based on the graphify output, how does the useScroll hook interact with the NavBar?"

*(The Graphify skill is already installed for AntiGravity and Gemini!)*

---

## 3. Directory Layout

- `D:\_ai_brain\scripts\` - Helper scripts to manage your AI setup.
- `D:\_ai_brain\benchmarks\` - Performance benchmark reports.
- `D:\_ai_brain\reports\` - Machine state and hardware reports.
- `D:\_ai_brain\frontier\packets\` - Local-only markdown packets for optional manual frontier review.
- `D:\_ai_brain\global\` - Global Graphify status.
- `D:\ollama\models\` - Where all your local models live.

Path abstraction is available for future migration:

```bash
ws paths
source /mnt/d/_ai_brain/scripts/ws_env.sh
```

For now, `WS_HOME` is `/mnt/d/_ai_brain`, `MODEL_HOME` is `/mnt/d/ollama/models`, and `D:\Local_AI_Workstation` is only the future parent skeleton. Nothing has been moved.

## 4. Local-First Frontier Packets

The default workflow stays local: `ws`, Graphify, and Ollama prepare context on your machine. Gemini, Codex, and Claude are explicit consultants only; packet creation does not call them, authenticate them, or upload data.

Create a compact packet when local work is stuck or when you need a narrow architecture, debugging, or strategy review:

```bash
ws frontier
ws packet global "Which project should I improve first?"
ws redact <packet>
ws packet gsp "Prepare a review packet for the modelling flow."
ws escalate codex latest
```

Only escalate after `ws redact <packet>` returns `SAFE`. `ws escalate` runs redaction again before sending and refuses on `WARNING` or `BLOCKED`. Gemini and Codex are explicit consultant commands only; normal `ws ask`, `ws debug`, `ws audit`, and `ws task` stay local.

## 5. Workstation Audit and Cleanup

Audit and cleanup commands are for `D:\_ai_brain` only. They do not clean project repos, delete models, delete project Graphify outputs, read secrets, or inspect raw datasets. The normal mode is read-only.

```bash
ws audit-workstation
ws cleanup-plan
ws cleanup-status
ws cleanup-apply --apply
```

Run `ws cleanup-plan` first and read the generated markdown. `ws cleanup-apply` refuses to move anything unless you pass `--apply`, and even then it archives high-confidence candidates only.

## 6. Daily Product-Building Flow

Use the local planner first, then the Windows-native bounded apply path. The normal daily sequence is:

```bash
ws daily
ws warm
ws task-status
ws task-next workstation_control_plane
ws build <project_key> <task_file> --plan-only --max-tasks 1
ws open-build latest
ws agent-run <project_key> <task_file> --mode detect --branch --max-files 5 --max-minutes 10 --stop-on-fail
```

Planning stays local-first through `ws build --plan-only`. For the primary apply path, the operator still runs `ws` from WSL, but `ws agent-run` crosses into Windows PowerShell and launches Codex through the Windows `codex.cmd` bridge. Review the agent run report and diff before keeping changes.

```bash
ws agent-import <run>
```

Use `ws agent-import <run>` as the fallback/manual handoff review path when unattended execution is not available. `ws build --apply` is a secondary local-diff-only path, not the normal apply workflow. Gemini remains manual packet review only for now, and older `ws auto` / Codex patch flows are legacy or experimental rather than the operator default.

## 7. Task Lifecycle

Use canonical task folders before running builds:

```bash
ws task-status
ws task-next workstation_control_plane
ws build workstation_control_plane <task_file> --plan-only --max-tasks 1
ws open-build latest
ws task-review <task_file> --with codex
ws task-complete <task_file> "completed after review"
ws task-block <task_file> "blocked reason"
```

`ws task-review` creates and redacts a packet but does not send it. Escalation remains explicit with `ws escalate codex latest`.

## 8. Deterministic PRD Task Splitting

Structured PRDs are parsed locally without an LLM when they already contain task headings.

```bash
ws task-split /mnt/d/_ai_brain/tasks/workstation_control_plane_prd.md --project workstation_control_plane --dry-run
ws task-split /mnt/d/_ai_brain/tasks/workstation_control_plane_prd.md --project workstation_control_plane
ws task-split /mnt/d/_ai_brain/tasks/workstation_control_plane_prd.md --project workstation_control_plane --to-inbox
ws task-next workstation_control_plane
```

Generated tasks go to `D:\_ai_brain\tasks\generated` by default. Use `--to-inbox` to promote them into `tasks\inbox`. After splitting, run `ws task-next` to choose the next task and use `ws build <project> <task_file> --plan-only --max-tasks 1` before any apply run.

## Important Constraints
- **Do not graph massive raw datasets** (e.g., inside Kaggle folders). Let the AI read your Python *logic*, not your raw Parquet files. `.graphifyignore` handles this automatically.
- **Do not blindly increase context above 8k**. It will tank performance on your 8GB GPU.

---
*Generated: 2026-05-11 | Model: hermes3:8b | Context: 8192*
