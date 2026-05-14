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

1. **Verify Ollama is Running**:
   Ollama should start with Windows. If not, just open the Ollama app.
   To verify it's working and the model is hot, run this in PowerShell:
   ```powershell
   D:\_ai_brain\scripts\check_health.ps1
   ```

2. **Load the Model (Keep it Hot)**:
   The system is configured to keep models loaded in VRAM for 30 minutes (`OLLAMA_KEEP_ALIVE=30m`). 
   Run this script to preload `hermes3:8b` so your first query of the day is instant:
   ```powershell
   D:\_ai_brain\scripts\warm_model.ps1
   ```

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

Use the bounded build loop when you want the workstation to turn a task queue into a plan or a small guarded change.

```bash
ws daily
ws warm
ws build <project> <task_file> --plan-only --max-tasks 1
ws open-build latest
ws build <project> <task_file> --apply --branch --max-tasks 1
ws open-build latest
```

After the apply run, review `final_diff.patch`, `test_output.md`, and `build_report.md`. If local Hermes gets stuck and the packet is safe, explicitly opt into Codex:

```bash
ws build <project> <task_file> --apply --branch --max-tasks 1 --escalate codex
```

Gemini is manual packet review only for now because its CLI is not safe non-interactively from WSL.

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
