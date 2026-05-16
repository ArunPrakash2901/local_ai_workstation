# R5A Local + Cloud Workflow Audit

Date: 2026-05-16  
Scope: workstation control plane only; read-only inspection of scripts, registries, and operator docs.

## Executive Summary

The workstation already contains a usable local + cloud MVP split:

- local Ollama + Graphify provide project understanding, local-first answers, audits, debugging, task context, and build planning
- Windows-native Codex through `ws agent-run` is the current bounded cloud apply lane
- packet/redaction commands provide explicit frontier review paths for Codex and Gemini

The main defect is not missing machinery. It is workflow drift: older local patch/apply flows still exist beside the newer `agent-run` path, and `LOCAL_AI_STACK_STATUS.md` still describes the older build-loop apply model as if it were the normal path.

## Current Command Map

### Commands That Use Local Ollama

Evidence: `scripts/ai_ask.sh`, `ai_global_ask.sh`, `ai_audit.sh`, `ai_debug.sh`, `ai_run_task.sh`, and `ws_build.sh` call `scripts/ollama_call.py`.

- `ws ask <project> "<question>"`
- `ws global "<question>"`
- `ws audit <project>`
- `ws debug <project> <log>`
- `ws task <project> <task_file>`
- `ws build <project> <task_file> --plan-only`

`registry/active_model.yaml` shows the current daily local lane as:

- profile: `hermes_default`
- model: `hermes3:8b`
- context: `8192`

### Commands That Use Graphify

Evidence: Graphify calls appear in `ai_ask.sh`, `ai_global_ask.sh`, `ai_audit.sh`, `ai_debug.sh`, `ai_graph.sh`, `ai_run_task.sh`, `ws_context_pack.sh`, and `ws_make_packet.sh`.

- `ws ask`
- `ws global`
- `ws graph`
- `ws audit`
- `ws debug`
- `ws task`
- `ws build` through context-pack generation
- `ws packet`

### Commands That Use Codex Or Cloud Execution

- `ws agent-run` uses Windows PowerShell and the Windows Codex launcher for bounded apply work.
- `ws escalate codex <packet>` explicitly sends a redacted packet to Codex.
- `ws task-review <task> --with codex` creates a Codex review packet but does not send it.
- `ws escalate gemini <packet>` exists as an explicit packet path.

### Gemini And Claude State

- Gemini CLI is configured in `registry/frontier.yaml` and has an explicit escalation path, but normal workflow docs keep it manual and bounded.
- Claude is configured as unavailable: `enabled: false` in `registry/frontier.yaml`, and `ws_escalate.sh` reports it as unavailable unless installed later.
- Neither Gemini nor Claude is part of the normal local planning or bounded apply lane.

## Lane Assessment

### Is `ws build --plan-only` Truly The Local Planning Lane?

Yes. `ws_build.sh` builds a local context pack, calls `ollama_call.py`, and defaults to plan-only behavior unless explicit apply flags are passed.

### Is `ws agent-run` Clearly The Cloud Codex Apply Lane?

Yes in the newer operator docs and dispatcher surface. `WORKSTATION_MANUAL.md` and `START_HERE.md` now define `agent-run` as the primary bounded apply path, while `scripts/ws` exposes it directly.

### Current Ambiguities

1. `LOCAL_AI_STACK_STATUS.md` still describes `ws build --apply` and explicit Codex escalation as the bounded build-loop apply model, which is older than the current `agent-run` workflow.
2. Legacy and experimental paths still exist beside the current lane:
   - `ws build --apply`
   - older Codex packet escalation loops
   - older `ws auto` / patch-generation flows
3. Validation is asymmetric:
   - cloud/agent health has `ws agent-validate`
   - local health does not yet have an equally explicit validation gate

## Clean MVP Division Of Responsibility

### Local Model Responsibilities

- local-first planning
- task decomposition support
- summarization
- Graphify-assisted repository understanding
- low-risk drafting
- privacy-sensitive work
- pre-cloud compression and redaction

### Cloud Model Responsibilities

- Codex: bounded apply through `ws agent-run`
- Gemini: frontier reasoning, architecture, strategy review when manually or safely invoked
- Claude Code: architecture, refactor, and review only if later installed and explicitly invoked

Cloud models must not receive raw private folders, secrets, raw datasets, or model files.

## Recommended Command Taxonomy

### Local Planning

- `ws ask`
- `ws global`
- `ws graph`
- `ws audit`
- `ws debug`
- `ws task`
- `ws build --plan-only`

### Cloud Apply

- `ws agent-run`
- `ws agent-import`

### Frontier Review

- `ws packet`
- `ws redact`
- `ws task-review --with codex`
- `ws escalate codex`
- `ws escalate gemini`

### Validation

- existing: `ws agent-validate`
- existing: `ws agent-hygiene`
- recommended next addition: `ws local-validate`

### Legacy Or Experimental

- `ws build --apply`
- older Codex patch-generation flows
- older `ws auto` behavior

## Minimal Local Validation Gate

Add a small local-health gate before any independent-loop work:

```bash
ws local-validate
```

Recommended checks:

1. Ollama endpoint is reachable without generation.
2. Active model registry is readable.
3. `hermes3:8b` is listed locally.
4. `MODEL_HOME` still resolves to `D:\ollama\models`.
5. Graphify venv exists.
6. Graphify executable can be invoked.
7. The validation performs no model mutation, pulls, warmups, or benchmark calls.

Keeping this separate from `ws agent-validate` is cleaner than folding local and cloud health into one large command. The workstation needs both gates, and failures mean different things operationally.

## R5 Independent-Loop Design Implications

An independent loop should use both lanes deliberately:

1. local lane performs task understanding, graph lookup, compression, and first-pass planning
2. guard layer confirms explicit task boundaries and local-health status
3. cloud lane performs bounded implementation only when explicitly selected
4. local validation and cloud validation both pass before unattended repetition is considered
5. reports must state which lane acted at each step

Night loops remain out of scope until both validation gates pass consistently. Running unattended while either local-health checks or cloud-agent checks are unstable would turn a bounded system into a harder-to-debug batch processor.

## Recommended Next Step

Implement `ws local-validate` as a small, read-only counterpart to `ws agent-validate`, then update `LOCAL_AI_STACK_STATUS.md` so the documented apply lane matches the live `agent-run` workflow.

## Validation Performed

Commands run:

- `ws agent-validate`
- `ws agent-hygiene`
- `ws model`
- `ws models`
- non-generative Ollama endpoint probe: `GET /api/tags`
- Graphify executable presence/invocation check

Results:

- local lane health checks passed:
  - Ollama endpoint reachable
  - active profile remains `hermes_default`
  - active model remains `hermes3:8b`
  - `hermes3:8b` is installed
  - active model path remains `/mnt/d/ollama/models` from `registry/paths.yaml`
  - Graphify binary exists and invokes successfully
- `ws agent-hygiene` passed
- `ws agent-validate` failed on the current run because `ws agent-canary` returned `CODEX_FAILED`, even though the cached previous canary result was `AGENT_CANARY_PASSED`

This confirms that local validation and cloud-agent validation should stay separate. The local MVP lane is presently healthy; unattended Codex execution is not yet consistently proven.
