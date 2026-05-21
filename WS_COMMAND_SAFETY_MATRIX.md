# WS Command Safety Matrix

## 1. Executive Summary

This document classifies the discovered `ws` command surface and related Local AI Workstation command paths by safety behavior, write behavior, model/provider usage, TUI exposure suitability, and confirmation requirements.

The classification matters because `ws` is the backend command API for the workstation and the TUI is a human-facing shell around selected `ws` behavior. Future Codex, Antigravity, TUI, and local-agent work needs a practical way to decide which actions are safe to display, which actions can run in `READ_ONLY`, which actions are only acceptable in `SAFE_DRY_RUN`, and which actions must remain hidden behind explicit confirmation.

The main safety finding is that the current command surface has three distinct categories that are easy to confuse:

| Category | Meaning | Examples |
|---|---|---|
| True read-only | Reads existing state and does not write files. | `ws projects`, `ws model`, `ws feature-status`, `ws handoff-status` |
| Local report-writing status | Performs status/readiness work but writes reports, cache, or controlled workstation status artifacts. | `ws ready`, `ws agent-hygiene`, `ws cleanup-plan`, `ws frontier` |
| Mutation/provider-capable workflows | Can update workstation state, project files, branches, model runtime state, handoffs, or external provider processes. | `ws agent-run`, `ws build --apply`, `ws escalate codex`, `ws cleanup-apply --apply` |

The current TUI source defines `SAFETY_MODE = "READ_ONLY"` and exposes a narrow status-command allowlist plus a small learning dry-run allowlist. Repository evidence shows that some allowlisted status commands write local reports. This creates an ambiguity: `READ_ONLY` currently appears to mean "no project/provider mutation," not "no writes at all." This document recommends splitting that into explicit policies rather than relying on overloaded language.

## 2. Safety Definitions

| Term | Definition |
|---|---|
| Pure read | Reads existing state only. Does not create, modify, delete, refresh, regenerate, or copy files. Does not update caches, reports, registries, logs, or runtime state. |
| Local report write | Reads state but writes local report, cache, status, packet, or generated diagnostic artifacts under controlled workstation paths. It must not mutate project source, branches, provider state, or secrets. |
| Dry-run | Simulates or plans an action without applying project/provider changes. In this repository, some dry-run commands still write local plan/report artifacts; that must be disclosed. |
| Guarded write | Can modify files or state, but only through explicit command intent, confirmation, allowlists, branch checks, dry-run provenance, or apply gates. This includes workstation artifact/state mutations even when project source is not touched. |
| Agent invocation | Can start or delegate to an AI agent/model process. This includes local Ollama model calls and external agent CLI calls. |
| Provider/cloud interaction | Can contact external APIs, cloud tools, or cloud-backed CLIs, or can initiate a workflow that sends prompt/context to such a tool. |
| Project mutation | Can modify project source files, project docs, generated artifacts inside a project, branches, worktrees, or git state. |
| Unsafe/unclassified | Behavior is unclear, missing, or too risky to expose until source and runtime behavior are classified. |

## 3. Safety Classes

| Safety Class | Meaning | TUI Exposure | READ_ONLY | SAFE_DRY_RUN | Confirmation |
|---|---|---|---|---|---|
| PURE_READ | Reads only; no writes. | Allowed. | Allowed. | Allowed. | Not required. |
| LOCAL_REPORT_WRITE | Writes local status/report artifacts only. | Allowed with label. | Allowed only if `READ_ONLY` definition permits local reports. | Allowed. | Usually not required, but must be disclosed. |
| DRY_RUN_ONLY | Plans/simulates; no project/provider apply. May write dry-run artifacts if disclosed. | Allowed with dry-run label. | Allowed only if local dry-run artifacts are permitted. | Allowed. | Not required or light confirmation. |
| GUARDED_WRITE | Can mutate local files/state through gates. | Hidden or guarded. | Not allowed. | Only dry-run path allowed. | Required. |
| AGENT_RUN | Invokes local model or agent-like process. | Guarded. | Not allowed unless explicitly read-only model mode exists. | Depends on command. | Required. |
| PROVIDER_CALL | Can call external provider/cloud or cloud-backed CLI. | Guarded or hidden. | Not allowed unless explicitly approved. | Depends on command. | Required. |
| DESTRUCTIVE | Can delete, overwrite, archive, clean, reset, discard, or materially move state. | Hidden by default. | Not allowed. | Not allowed except dry-run preview. | Strong confirmation. |
| UNKNOWN | Insufficient evidence. | Hidden. | Not allowed. | Not allowed. | Required after classification. |

## 4. Command Inventory Method

Commands were discovered through source and documentation inspection, not by executing workstation workflows.

| Source | Inspection method | Notes |
|---|---|---|
| `scripts/ws` | Read subcommand dispatch logic. | Primary command inventory. |
| `scripts/ws_*` | Read relevant shell and PowerShell scripts. | Classified write behavior, model use, reports, and apply gates. |
| `scripts/ai_*` | Read command helpers routed from `ws` and relevant direct model/runtime helpers. | Classified local Ollama, registry writes, and model pull behavior. |
| `scripts/graphify_project.sh`, `scripts/graphify_query.sh` | Read wrappers only. | Did not inspect raw graph output. |
| `scripts/ollama_call.py` | Read helper source. | Local model call path. |
| `tui/app.py` | Read TUI action routing, safety mode, allowlists, disabled actions, and artifact exclusions. | Evidence for TUI exposure policy. |
| `tui/README.md` | Read TUI safety documentation. | Evidence for read-only and dry-run posture. |
| `WORKSTATION_MANUAL.md` | Read command usage and operational posture. | Evidence for intended workflows. |
| `PRD_LOCAL_AI_WORKSTATION.md` | Read as project product context. | Evidence for `READ_ONLY` ambiguity and safety model. |
| `START_HERE.md` | Read onboarding and local-first workflow guidance. | Evidence for local-first and escalation posture. |
| Registry files | Read non-secret registry files only: `registry/active_model.yaml`, `registry/active_kv_profile.yaml`, `registry/frontier.yaml`. | Did not inspect secret-like files. |
| Git status | Ran `git status --short`. | Used only to identify dirty files before inspection. |

Commands deliberately not executed:

| Command type | Reason |
|---|---|
| Any `ws` workflow command | Source inspection was sufficient and execution could write reports, invoke models, or mutate state. |
| Any Codex, Claude, Gemini, or browser command | Could invoke cloud/provider tooling or automation. |
| Any apply/build/cleanup/worktree command | Could mutate projects, worktrees, branches, reports, or archives. |
| Any model pull or benchmark command | Could download models, invoke Ollama, or write benchmark outputs. |

Files and paths deliberately skipped for safety:

| Skipped path/type | Reason |
|---|---|
| `.env`, credential, token, key, and secret-like files | Secret inspection is out of scope. |
| Raw Graphify output such as `graph.json` | Large/raw context inspection is out of scope. |
| CSV, Parquet, SQLite, database, archive, binary, media, and model files | Large/raw data and binary inspection is out of scope. |
| Model weight directories | Model content inspection is out of scope. |
| Existing dirty files for modification | Dirty files were read only where allowed and were not modified. |

## 5. Command Safety Matrix

One row means one discovered command, entry point, or safety-relevant variant. Some `ws` subcommands are split into variants where behavior changes materially between dry-run, local-model, apply, or provider-capable modes.

| Command / Entry Point | Description | Safety Class | Writes Local Files? | Writes Project Files? | Invokes Agent/Model? | External Provider/Cloud? | Safe in READ_ONLY? | Safe in SAFE_DRY_RUN? | TUI Exposure | Confirmation Required | Evidence | Confidence | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ws help` | Prints built-in help text from the wrapper. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws` `help` case | High | Inline wrapper output only. |
| `ws aliases` | Prints suggested shell aliases. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws` `aliases` case | High | Inline wrapper output only. |
| `ws projects` | Lists registered projects. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws`; `scripts/ai_list_projects.sh` | High | Reads registry. |
| `ws project <key>` | Shows project details and graph path status. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws`; `scripts/ai_project.sh` | High | Checks graph path existence; does not read raw graph content. |
| `ws model` | Shows active model profile. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws`; `scripts/ai_model_current.sh` | High | Reads active model/KV registry files. |
| `ws models` | Lists model registry and local Ollama availability. | PURE_READ | No | No | No | Local Ollama only | Yes | Yes | Allowed | None | `scripts/ws`; `scripts/ai_models.sh` | High | Queries local model runtime; no generation or writes observed. |
| `ws moe` | Lists MoE/lab model information through model listing fallback. | PURE_READ | No | No | No | Local Ollama only | Yes | Yes | Allowed | None | `scripts/ws` `moe` case | Medium | `ai_moe_list.sh` was not present; wrapper falls back to `ai_models.sh` filter. |
| `ws kv` | Lists KV/cache profiles. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws`; `scripts/ai_kv_profiles.sh` | High | Reads registry only. |
| `ws paths` | Shows configured workstation paths. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws`; `scripts/ws_path_status.sh` | High | Reads path registry. |
| `ws status` | Runs health/model status checks. | PURE_READ | No | No | No | Local Ollama/WSL probes | Yes | Yes | Allowed | None | `scripts/ws` `status` case; `scripts/check_health.ps1`; `scripts/ai_model_current.sh` | Medium | No file writes observed; probes local services. |
| `ws tui` | Launches the TUI cockpit/operator dashboard. | LOCAL_REPORT_WRITE | Yes | No | No | No | Only if local reports allowed | No | Hidden as an internal TUI action | None | `registry/ws_command_safety.yaml`; `scripts/ws` `tui` case; `scripts/ws_tui.sh`; `tui/app.py` `STATUS_COMMANDS`; `tui/README.md` | High | Source-backed route for opening the cockpit; dashboard status collection may run local-report-writing status paths. It must not bypass existing TUI action visibility metadata or execution gates. |
| `ws runs` | Lists recent run folders. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws` `runs` case | High | Uses directory listing only. |
| `ws open-run <id>` | Prints path/content for a selected run artifact if present. | PURE_READ | No | No | No | No | Yes | Yes | Allowed with path safety | None | `scripts/ws` `open-run` case | High | Reads generated run files. |
| `ws build-status` | Lists latest build run state. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws` `build-status` case | High | Reads `build_runs`. |
| `ws build-runs` | Lists build runs. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws` `build-runs` case | High | Directory listing only. |
| `ws open-build <id>` | Prints latest build report path/content if present. | PURE_READ | No | No | No | No | Yes | Yes | Allowed with path safety | None | `scripts/ws` `open-build` case | High | Reads generated build report. |
| `ws feature-status` | Shows feature stronghold status. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws`; `scripts/ws_feature_status.sh`; `tui/app.py` `STATUS_COMMANDS` | High | TUI status allowlist includes this command. |
| `ws stronghold-status` | Shows stronghold status. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws`; `scripts/ws_stronghold_status.sh`; `tui/app.py` `STATUS_COMMANDS` | High | TUI status allowlist includes this command. |
| `ws handoff-status` | Shows handoff status. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws`; `scripts/ws_handoff_status.sh`; `tui/app.py` `STATUS_COMMANDS` | High | TUI status allowlist includes this command. |
| `ws product-list` | Lists Product Lane Phase 0 registry records. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `PRODUCT_PHASE_0_IMPLEMENTATION_PLAN.md`; `scripts/ws`; `scripts/ws_product_list.py` | High | Reads `products/*/product.yaml`; no writes. |
| `ws product-status` | Shows one Product Lane Phase 0 product record. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `PRODUCT_PHASE_0_IMPLEMENTATION_PLAN.md`; `scripts/ws`; `scripts/ws_product_status.py` | High | Reads `products/<product_id>/product.yaml`; no writes. |
| `ws product-new` | Creates a Product Lane Phase 0 product record. | GUARDED_WRITE | Yes | No | No | No | No | No | Hidden in Phase 0 | Explicit | `PRODUCT_PHASE_0_IMPLEMENTATION_PLAN.md`; `scripts/ws`; `scripts/ws_product_new.py`; `scripts/product_registry.py` | High | Writes only under `products/<product_id>/`; requires explicit confirmation and refuses overwrite by default. |
| `ws product-help` | Prints Product Lane Phase 0 usage and safety notes. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `products/README.md`; `WORKSTATION_MANUAL.md`; `scripts/ws`; `scripts/ws_product_help.py` | High | Quick reference only; must not create products or write files. |
| `ws product-questions --dry-run` | Previews static Product Lane intake questions for one product type or product id. | DRY_RUN_ONLY | No | No | No | No | Yes | Yes | Hidden in Phase 1 Slice 1 | None | `PRODUCT_PHASE_1_INTAKE_SCOPE_PLAN.md`; `PRODUCT_INTAKE_QUESTION_BANK.md`; `scripts/ws`; `scripts/ws_product_questions.py`; `scripts/product_intake_questions.py` | High | Static dry-run preview only; no writes, no model/provider/agent calls. |
| `ws product-intake --dry-run` | Previews Phase 1 intake flow and future artifacts without applying writes. | DRY_RUN_ONLY | No | No | No | No | Yes | Yes | Hidden in Phase 1 Slice 2 | None | `PRODUCT_PHASE_1_INTAKE_SCOPE_PLAN.md`; `PRODUCT_INTAKE_QUESTION_BANK.md`; `scripts/ws`; `scripts/ws_product_intake.py`; `scripts/product_intake_questions.py` | High | Dry-run preview only; no writes, no model/provider/agent calls. |
| `ws product-intake --confirm` | Starts intake for an existing product by writing deterministic intake templates and updating product state. | GUARDED_WRITE | Yes | No | No | No | No | No | Hidden in Phase 1 Slice 2 | Explicit | `PRODUCT_PHASE_1_INTAKE_SCOPE_PLAN.md`; `PRODUCT_INTAKE_QUESTION_BANK.md`; `scripts/ws`; `scripts/ws_product_intake.py`; `scripts/product_intake_artifacts.py` | High | Writes only under `products/<product_id>/` (`intake.md`, `questions.md`, `product.yaml` update, action log append if present). Refuses missing/non-INBOX/duplicate template cases. |
| `ws product-answer-import` | Imports operator-provided intake answers, writes `answers.md`, and classifies intake as `SCOPE_READY` or `CLARIFICATION_NEEDED`. | GUARDED_WRITE | Yes | No | No | No | No | No | Hidden in Phase 1 Slice 3 | Explicit | `PRODUCT_PHASE_1_INTAKE_SCOPE_PLAN.md`; `PRODUCT_INTAKE_QUESTION_BANK.md`; `scripts/ws`; `scripts/ws_product_answer_import.py`; `scripts/product_answer_import.py` | High | Writes only under `products/<product_id>/` (`answers.md`, `product.yaml` update, action log append if present). Rejects unknown/duplicate IDs and missing/non-intake state. |
| `ws product-scope --dry-run` | Previews deterministic scope draft content from product intake state without writing files. | DRY_RUN_ONLY | No | No | No | No | Yes | Yes | Hidden in Phase 1 Slice 4 | None | `PRODUCT_PHASE_1_INTAKE_SCOPE_PLAN.md`; `PRODUCT_SCOPE_LOCK_SPEC.md`; `scripts/ws`; `scripts/ws_product_scope.py`; `scripts/product_scope.py` | High | Requires `SCOPE_READY` and complete required/blocking/privacy answers; renders `TODO/UNKNOWN` for unavailable scope fields; no model/provider/agent calls. |
| `ws product-scope-change --dry-run` | Previews deterministic scope change impact from product metadata and an operator-authored change file. | DRY_RUN_ONLY | No | No | No | No | Yes | Yes | Hidden in Scope Revision Slice 1 | None | `PRODUCT_SCOPE_REVISION_PLAN.md`; `PRODUCT_PRD_WARN_TRIAGE_PORTFOLIO_WEBSITE.md`; `scripts/ws`; `scripts/ws_product_scope_change.py`; `scripts/product_scope_change.py` | High | Parses a small deterministic change-file format, reports affected artifacts and future staleness implications, and writes no files or state. |
| `ws product-scope-change --confirm` | Records a product scope change decision and marks downstream artifacts stale/needs-revision without revising immutable scope artifacts yet. | GUARDED_WRITE | Yes | No | No | No | No | No | Hidden in Scope Revision Slice 2 | Explicit | `PRODUCT_SCOPE_REVISION_PLAN.md`; `PRODUCT_PRD_WARN_TRIAGE_PORTFOLIO_WEBSITE.md`; `scripts/ws`; `scripts/ws_product_scope_change.py`; `scripts/product_scope_change.py` | High | Writes only under `products/<product_id>/` (`decisions/scope_change_<change_id>.md`, `product.yaml`, optional action log append). Does not modify `scope_lock.md`, `prd.md`, or `answers.md`; no model/provider/agent calls. |
| `ws product-scope-revision --dry-run` | Previews deterministic revised scope text from `scope_lock.md` and confirmed `decisions/scope_change_*.md` without writing files. | DRY_RUN_ONLY | No | No | No | No | Yes | Yes | Hidden in Scope Revision Slice 3 | None | `PRODUCT_SCOPE_REVISION_PLAN.md`; `PRODUCT_PRD_WARN_TRIAGE_PORTFOLIO_WEBSITE.md`; `scripts/ws`; `scripts/ws_product_scope_revision.py`; `scripts/product_scope_revision.py` | High | Reads only confirmed scope change decisions plus current scope lock, previews section-level replacements for supported fields, and does not modify `scope_lock.md`, `product.yaml`, or `prd.md`. |
| `ws product-scope-revision --confirm` | Writes a versioned revised scope lock artifact from confirmed scope change decisions and updates active scope metadata. | GUARDED_WRITE | Yes | No | No | No | No | No | Hidden in Scope Revision Slice 4 | Explicit | `PRODUCT_SCOPE_REVISION_PLAN.md`; `PRODUCT_PRD_WARN_TRIAGE_PORTFOLIO_WEBSITE.md`; `scripts/ws`; `scripts/ws_product_scope_revision.py`; `scripts/product_scope_revision.py` | High | Writes only under `products/<product_id>/` (`scope_locks/scope_lock_vN.md`, `product.yaml`, optional action log append). Keeps original `scope_lock.md` immutable, does not rewrite `prd.md` or `answers.md`, and leaves PRD stale/`NEEDS_REVISION`; no model/provider/agent calls. |
| `ws product-lock-scope` | Locks scope for a `SCOPE_READY` product by writing immutable `scope_lock.md` and recording scope lock metadata. | GUARDED_WRITE | Yes | No | No | No | No | No | Hidden in Phase 1 Slice 5 | Explicit | `PRODUCT_PHASE_1_INTAKE_SCOPE_PLAN.md`; `PRODUCT_SCOPE_LOCK_SPEC.md`; `scripts/ws`; `scripts/ws_product_lock_scope.py`; `scripts/product_scope_lock.py` | High | Writes only under `products/<product_id>/` (`scope_lock.md`, `product.yaml` update, action log append if present). Refuses overwrite and refuses when lock metadata already exists. |
| `ws product-prd --dry-run` | Previews deterministic PRD content from locked scope and product metadata without writing files. | DRY_RUN_ONLY | No | No | No | No | Yes | Yes | Hidden in Phase 2 Slice 1 | None | `PRODUCT_PHASE_2_PRD_PLAN.md`; `scripts/ws`; `scripts/ws_product_prd.py`; `scripts/product_prd.py` | High | Requires `SCOPE_LOCKED`; deterministic no-write preview from `product.yaml` and `scope_lock.md`; no model/provider/agent calls. |
| `ws product-prd --confirm` | Writes deterministic PRD content from locked scope to `prd.md` and updates product metadata without changing product state. | GUARDED_WRITE | Yes | No | No | No | No | No | Hidden in Phase 2 Slice 2 | Explicit | `PRODUCT_PHASE_2_PRD_PLAN.md`; `scripts/ws`; `scripts/ws_product_prd.py`; `scripts/product_prd.py` | High | Requires `SCOPE_LOCKED`; writes only under `products/<product_id>/`; deterministic write from `product.yaml` and `scope_lock.md`; no model/provider/agent calls; refuses overwrite. |
| `ws product-prd-review --dry-run` | Reviews deterministic PRD structure and grounding from `product.yaml`, `scope_lock.md`, and `prd.md` without writing files. | DRY_RUN_ONLY | No | No | No | No | Yes | Yes | Hidden in Phase 2 Slice 3A | None | `PRODUCT_PHASE_2_PRD_REVIEW_PLAN.md`; `scripts/ws`; `scripts/ws_product_prd_review.py`; `scripts/product_prd_review.py` | High | Requires `SCOPE_LOCKED`, `scope_lock.md`, `scope_lock_hash`, and `prd.md`; reports `PASS/WARN/FAIL`; no model/provider/agent calls. |
| `ws product-prd-approve` | Approves deterministic PRD metadata only when deterministic review status is `PASS`; writes approval decision artifact and product metadata updates. | GUARDED_WRITE | Yes | No | No | No | No | No | Hidden in Phase 2 Slice 3B | Explicit | `PRODUCT_PHASE_2_PRD_REVIEW_PLAN.md`; `scripts/ws`; `scripts/ws_product_prd_approve.py`; `scripts/product_prd_approval.py` | High | Requires `SCOPE_LOCKED`, `scope_lock.md`, `scope_lock_hash`, and `prd.md`; refuses `WARN/FAIL` review and duplicate approval; writes only under `products/<product_id>/` (`decisions/prd_approval.md`, `product.yaml`, optional action log append); does not modify `prd.md` or `scope_lock.md`; no model/provider/agent calls. |
| `ws product-prd-status` | Shows Product Lane PRD artifact status from product metadata and artifact presence checks only. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `PRODUCT_PHASE_2_PRD_REVIEW_PLAN.md`; `scripts/ws`; `scripts/ws_product_prd_status.py`; `scripts/product_prd_status.py` | High | Reports derived `NOT_CREATED`/`DRAFTED`/`APPROVED` style status without modifying product files; does not run review/approval; no model/provider/agent calls. |
| `ws product-wireframe --dry-run` | Previews deterministic text/ASCII wireframes from approved PRD and locked scope. | DRY_RUN_ONLY | No | No | No | No | Yes | Yes | Hidden in Phase 2 Slice 4 | None | `PRODUCT_PHASE_2_PRD_REVIEW_PLAN.md`; `scripts/ws`; `scripts/ws_product_wireframe.py`; `scripts/product_wireframe.py` | High | Requires `SCOPE_LOCKED`, `prd_status=APPROVED`, `scope_lock.md`, `scope_lock_hash`, and `prd.md`; website/webapp/dashboard supported; non-UI product types return a non-applicable message; no model/provider/agent calls. |
| `ws redact <packet>` | Scans a frontier packet for redaction status. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws`; `scripts/ws_redact_packet.sh` | High | Prints `SAFE`, `WARNING`, or `BLOCKED`; no write observed. |
| `ws agent-import <run>` | Imports or displays an existing agent run result. | PURE_READ | No observed | No | No | No | Yes, if display-only | Yes | Hidden until verified | Light | `scripts/ws`; `scripts/ws_agent_import.ps1`; `scripts/ws_agent_run.ps1` `Run-Import` | Medium | Source suggests read/import handling; verify before TUI exposure. |
| `scripts/check_health.ps1` | Direct health probe helper. | PURE_READ | No | No | No | Local service probes | Yes | Yes | Allowed as backend-only | None | `scripts/check_health.ps1` | High | Used by `ws status` and readiness workflows. |
| `scripts/ws_apply_guard.sh` | Validates patch/apply safety conditions. | PURE_READ | No | No | No | No | Yes | Yes | Backend-only | None | `scripts/ws_apply_guard.sh` | High | Guard helper; no project mutation by itself. |
| `scripts/graphify_query.sh` | Queries existing graph context. | PURE_READ | No | No | No | No | Yes if graph read is allowed | Yes | Backend-only | None | `scripts/graphify_query.sh` | High | Query wrapper; raw graph output was not inspected. |
| `ws ready` | Performs readiness checks and writes readiness report. | LOCAL_REPORT_WRITE | Yes | No | No | Local probes | Only if local reports allowed | Yes | Allowed with `writes report` label | None or light | `scripts/ws`; `scripts/ws_readiness.sh`; `tui/app.py` `STATUS_COMMANDS`; `PRD_LOCAL_AI_WORKSTATION.md` | High | Writes `reports/READINESS_<timestamp>.md`; may call frontier status. |
| `ws frontier` | Checks frontier tooling and writes frontier registry/status scaffolding. | LOCAL_REPORT_WRITE | Yes | No | No | Detects provider CLIs only | Only if local reports allowed | Yes | Allowed with label | None or light | `scripts/ws`; `scripts/ws_frontier_status.sh` | High | Creates frontier dirs and updates `registry/frontier.yaml`. |
| `ws graph <project/global>` | Runs graph query and writes run output. | LOCAL_REPORT_WRITE | Yes | No | No | No | Only if local reports allowed | Yes | Allowed with label | None or light | `scripts/ws`; `scripts/ai_graph.sh` | High | Writes `runs/<timestamp>_graph_*` artifacts. |
| `ws task-status` | Shows task status and ensures task directories exist. | LOCAL_REPORT_WRITE | Yes | No | No | No | Only if local scaffold writes allowed | Yes | Allowed with label | None or light | `scripts/ws`; `scripts/ws_task_status.sh`; `WORKSTATION_MANUAL.md` | High | Creates task lifecycle directories before reading status. |
| `ws task-next` | Shows next task and ensures task directories exist. | LOCAL_REPORT_WRITE | Yes | No | No | No | Only if local scaffold writes allowed | Yes | Allowed with label | None or light | `scripts/ws`; `scripts/ws_task_next.sh` | High | Creates task lifecycle directories before selecting next task. |
| `ws apply-ready` | Produces apply-readiness report for an agent run. | LOCAL_REPORT_WRITE | Yes | No | No | No | Only if local reports allowed | Yes | Backend-only | Light | `scripts/ws`; `scripts/ws_agent_apply_ready.sh` | High | Does not apply changes; report artifact only. |
| `ws agent-status` | Shows agent launcher/canary status. | LOCAL_REPORT_WRITE | Potentially | No | No | No | Only if local scaffold writes allowed | Yes | Allowed with label | None or light | `scripts/ws`; `scripts/ws_agent_status.ps1`; `scripts/ws_agent_run.ps1` | Medium | The shared PowerShell runner ensures scratch directories before dispatch. |
| `ws agent-hygiene` | Scans agent run hygiene and writes report. | LOCAL_REPORT_WRITE | Yes | No | No | No | Only if local reports allowed | Yes | Allowed with label | None or light | `scripts/ws`; `scripts/ws_agent_hygiene.sh`; `tui/app.py` `STATUS_COMMANDS` | High | Writes `reports/AGENT_HYGIENE_<timestamp>.md`. |
| `ws worktree-plan` | Writes a worktree plan report. | LOCAL_REPORT_WRITE | Yes | No | No | No | Only if local reports allowed | Yes | Backend-only | Light | `scripts/ws`; `scripts/ws_worktree_plan.sh` | High | Planning/report only. |
| `ws worktree-review` | Writes a worktree review report. | LOCAL_REPORT_WRITE | Yes | No | No | No | Only if local reports allowed | Yes | Backend-only | Light | `scripts/ws`; `scripts/ws_worktree_review.sh` | High | Review/report only. |
| `ws worktree-status` | Writes worktree status report. | LOCAL_REPORT_WRITE | Yes | No | No | No | Only if local reports allowed | Yes | Allowed with label | None or light | `scripts/ws`; `scripts/ws_worktree_status.sh` | High | Status report under workstation paths. |
| `ws loop-plan` | Writes loop planning report. | LOCAL_REPORT_WRITE | Yes | No | No | No | Only if local reports allowed | Yes | Backend-only | Light | `scripts/ws`; `scripts/ws_loop_plan.sh` | High | No project mutation observed. |
| `ws loop-status` | Writes loop status report. | LOCAL_REPORT_WRITE | Yes | No | No | No | Only if local reports allowed | Yes | Allowed with label | None or light | `scripts/ws`; `scripts/ws_loop_status.sh` | High | No project mutation observed. |
| `ws audit-workstation` | Audits workstation files and writes audit reports. | LOCAL_REPORT_WRITE | Yes | No | No | Local Ollama tags may be queried | Only if local reports allowed | Yes | Backend-only | Light | `scripts/ws`; `scripts/ws_audit_workstation.sh` | High | Writes cleanup audit markdown/JSON. |
| `ws cleanup-plan` | Writes cleanup plan from audit. | LOCAL_REPORT_WRITE | Yes | No | No | No | Only if local reports allowed | Yes | Backend-only | Light | `scripts/ws`; `scripts/ws_cleanup_plan.sh` | High | May run workstation audit if no audit JSON exists; writes plan markdown/JSON. |
| `ws cleanup-status` | Shows cleanup status; ensures cleanup directories exist. | LOCAL_REPORT_WRITE | Yes | No | No | No | Only if local scaffold writes allowed | Yes | Allowed with label | None or light | `scripts/ws`; `scripts/ws_cleanup_status.sh` | High | Creates cleanup/report/archive dirs before listing status. |
| `ws feature-report` | Writes final feature report artifact. | LOCAL_REPORT_WRITE | Yes | No | No | No | No in strict mode | Yes | Backend-only | Light | `scripts/ws`; `scripts/ws_feature_report.sh` | High | Local artifact/report write. |
| `ws stronghold-report` | Writes stronghold report artifact. | LOCAL_REPORT_WRITE | Yes | No | No | No | No in strict mode | Yes | Backend-only | Light | `scripts/ws`; `scripts/ws_stronghold_report.sh` | High | Local artifact/report write. |
| `ws task-review` | Creates a local review packet for task review. | GUARDED_WRITE | Yes | No | No | No | No | Yes with confirmation | Backend-only | Light | `scripts/ws`; `scripts/ws_task_review_packet.sh` | High | Writes frontier packet; does not send to provider. |
| `ws packet` | Creates local frontier packet. | GUARDED_WRITE | Yes | No | No | No | No | Yes with confirmation | Guarded | Light | `scripts/ws`; `scripts/ws_context_pack.sh`; `scripts/ws_frontier_packet.sh` | High | Local-first context packet; no upload observed. |
| `ws use <profile>` | Changes active model profile. | GUARDED_WRITE | Yes | No | No | No | No | No | Guarded | Light | `scripts/ws`; `scripts/ai_model_use.sh` | High | Writes `registry/active_model.yaml`. |
| `ws kvuse <profile>` | Changes active KV/cache profile. | GUARDED_WRITE | Yes | No | No | No | No | No | Guarded | Light | `scripts/ws`; `scripts/ai_kv_use.sh` | High | Writes `registry/active_kv_profile.yaml`. |
| `ws daily` | Applies daily model/KV defaults and unloads active model. | GUARDED_WRITE | Yes | No | Local Ollama runtime | No | No | No | Guarded | Light | `scripts/ws`; `scripts/ai_daily.sh` | High | Writes active model/KV registry and calls local model runtime unload. |
| `ws task-new` | Creates a new task file/artifact. | GUARDED_WRITE | Yes | No | No | No | No | No | Guarded | Light | `scripts/ws`; `scripts/ws_task_new.sh` | High | Mutates workstation task state. |
| `ws task-split` | Splits task into generated task artifacts. | GUARDED_WRITE | Yes | No | Optional local model by flag | No | No | Only `--dry-run` safe | Guarded | Light | `scripts/ws`; `scripts/ws_task_split.sh` | High | Non-dry-run writes task files. |
| `ws task-complete` | Marks task complete. | GUARDED_WRITE | Yes | No | No | No | No | No | Guarded | Light | `scripts/ws`; `scripts/ws_task_complete.sh` | High | Mutates task lifecycle state. |
| `ws task-block` | Marks task blocked. | GUARDED_WRITE | Yes | No | No | No | No | No | Guarded | Light | `scripts/ws`; `scripts/ws_task_block.sh` | High | Mutates task lifecycle state. |
| `ws handoff-new` | Creates a local handoff directory and prompt/context artifacts. | GUARDED_WRITE | Yes | No | No | No | No | Yes with confirmation | Guarded | Light | `scripts/ws`; `scripts/ws_handoff_new.sh` | High | Local handoff artifact only; no provider send observed. |
| `ws handoff-copy` | Copies handoff prompt to clipboard and updates metadata/transcript. | GUARDED_WRITE | Yes | No | No | Manual cloud handoff possible | No | No | Guarded | Provider/cloud confirmation if target is cloud | `scripts/ws`; `scripts/ws_handoff_copy.sh` | High | Clipboard bridge can expose context to manual browser/cloud workflow. |
| `ws handoff-import` | Imports clipboard response into handoff artifacts. | GUARDED_WRITE | Yes | No | No | Reads clipboard | No | No | Guarded | Clipboard confirmation | `scripts/ws`; `scripts/ws_handoff_import.sh` | High | Risk is importing unintended clipboard content. |
| `ws handoff-review` | Reviews handoff response and writes review metadata/report. | GUARDED_WRITE | Yes | No | No | No | No | Yes with confirmation | Guarded | Light | `scripts/ws`; `scripts/ws_handoff_review.sh` | High | Deterministic local review/write. |
| `ws feature-new` | Creates feature stronghold structure/state. | GUARDED_WRITE | Yes | No | No | No | No | No | Guarded | Light | `scripts/ws`; `scripts/ws_feature_new.sh` | High | Mutates feature stronghold artifacts. |
| `ws feature-plan` | Writes feature plan and updates feature loop state. | GUARDED_WRITE | Yes | No | No | No | No | Yes with confirmation | Guarded | Light | `scripts/ws`; `scripts/ws_feature_plan.sh` | High | Reads project context and writes local feature artifacts. |
| `ws feature-validate` | Writes feature validation evidence/state. | GUARDED_WRITE | Yes | No | No | No | No | Yes with confirmation | Guarded | Light | `scripts/ws`; `scripts/ws_feature_validate.sh` | High | Checks readiness and git state; writes validation artifacts. |
| `ws feature-handoff` | Creates feature handoff packet for a target. | GUARDED_WRITE | Yes | No | No | Manual/CLI target metadata only | No | Yes with confirmation | Guarded | Target confirmation | `scripts/ws`; `scripts/ws_feature_handoff.sh` | High | Does not invoke provider; target may imply later cloud/manual use. |
| `ws feature-architect-handoff` | Creates senior architect handoff packet. | GUARDED_WRITE | Yes | No | No | Manual target metadata only | No | Yes with confirmation | Guarded | Target confirmation | `scripts/ws`; `scripts/ws_feature_architect_handoff.sh` | High | Local packet creation only. |
| `ws feature-run --apply` | Creates apply-ready feature handoff after dry-run gates. | GUARDED_WRITE | Yes | No observed | No | No | No | No | Hidden or guarded | Branch/workflow confirmation | `scripts/ws`; `scripts/ws_feature_run.sh` | High | `HANDOFF_ONLY`; does not launch agent, but advances apply-ready workflow state. |
| `ws stronghold-new` | Creates stronghold structure/state. | GUARDED_WRITE | Yes | No | No | No | No | No | Guarded | Light | `scripts/ws`; `scripts/ws_stronghold_new.sh` | High | Mutates stronghold artifacts. |
| `ws stronghold-intake` | Writes stronghold intake artifacts. | GUARDED_WRITE | Yes | No | No | No | No | Yes with confirmation | Guarded | Light | `scripts/ws`; `scripts/ws_stronghold_intake.sh` | High | Local state/artifact write. |
| `ws stronghold-intake-import` | Imports intake artifact into stronghold workflow. | GUARDED_WRITE | Yes | No | No | No | No | No | Guarded | Light | `scripts/ws`; `scripts/ws_stronghold_intake_import.sh` | High | Mutates stronghold state. |
| `ws stronghold-architect-handoff` | Creates stronghold architect handoff packet. | GUARDED_WRITE | Yes | No | No | Manual/cloud target metadata only | No | Yes with confirmation | Guarded | Target confirmation | `scripts/ws`; `scripts/ws_stronghold_architect_handoff.sh` | High | Local handoff artifact; no provider call observed. |
| `ws stronghold-plan-import` | Imports plan into stronghold workflow state. | GUARDED_WRITE | Yes | No | No | No | No | No | Guarded | Light | `scripts/ws`; `scripts/ws_stronghold_plan_import.sh` | High | Mutates stronghold state. |
| `ws stronghold-decision` | Writes stronghold decision record and state update. | GUARDED_WRITE | Yes | No | No | No | No | No | Guarded | Light | `scripts/ws`; `scripts/ws_stronghold_decision.sh` | High | Decision/state mutation, not a pure report. |
| `ws learning-import-answers` | Imports human answers into learning artifacts. | GUARDED_WRITE | Yes | No | No | No | No | No | Hidden or guarded | Light | `scripts/ws`; `scripts/ws_learning_import_answers.sh`; `tui/app.py` `DISABLED_ACTIONS` | High | Disabled in TUI source. |
| `ws learning-decision` | Writes deterministic learning decision artifact/state. | GUARDED_WRITE | Yes | No | No | No | No | No | Hidden or guarded | Light | `scripts/ws`; `scripts/ws_learning_decision.sh` | High | Decision/state mutation. |
| `ws learning-advance` | Advances learning stronghold progress after decision. | GUARDED_WRITE | Yes | No | No | No | No | No | Hidden | Typed or explicit confirmation | `scripts/ws`; `scripts/ws_learning_advance.sh`; `tui/app.py` `DISABLED_ACTIONS` | High | Disabled in TUI source; state advancement should be explicit. |
| `ws learning-confirm --confirm` | Confirms a learning dry-run action and writes confirmation artifacts. | GUARDED_WRITE | Yes | No | No | No | No | No | Hidden | Explicit | `scripts/ws`; `scripts/ws_learning_confirm.sh`; `scripts/learning_confirmation_core.py` | High | Writes confirmation markdown and `learning_confirmations.jsonl` under the learning stronghold. |
| `ws research-decision` | Writes deterministic research decision artifact/state. | GUARDED_WRITE | Yes | No | No | No | No | No | Guarded | Light | `scripts/ws`; `scripts/ws_research_decision.sh` | High | Decision/state mutation. |
| `ws research-add-source` | Copies source text into research source artifacts and updates state. | GUARDED_WRITE | Yes | No | No | No | No | No | Hidden or guarded | Source confirmation | `scripts/ws`; `scripts/ws_research_add_source.sh` | High | Can copy local source text; source safety matters. |
| `ws worktree-create --apply` | Creates git branch/worktree from a prior dry-run report. | GUARDED_WRITE | Yes | Worktree/git state | No | No | No | No | Hidden or guarded | Branch confirmation | `scripts/ws`; `scripts/ws_worktree_create.sh` | High | Uses `git branch` and `git worktree add`; rollback branch delete on failure. |
| `ws worktree-sync --apply` | Fast-forwards a worktree from main after dry-run/report gate. | GUARDED_WRITE | Yes | Worktree/git state | No | No | No | No | Hidden or guarded | Branch/worktree confirmation | `scripts/ws`; `scripts/ws_worktree_sync.sh` | High | Uses `git merge --ff-only main` in worktree. |
| `ws agent-mark-stale-reviewed` | Writes reviewed marker for stale agent run. | GUARDED_WRITE | Yes | No | No | No | No | No | Guarded | Light | `scripts/ws`; `scripts/ws_agent_mark_stale_reviewed.sh` | High | Local marker under `auto_runs`. |
| `scripts/graphify_project.sh` | Generates Graphify output for a project. | GUARDED_WRITE | Yes | Generated project context output | No | No | No | No | Hidden or guarded | Project/path confirmation | `scripts/graphify_project.sh` | High | Writes project `graphify-out/graph.json`; raw output was not inspected. |
| `scripts/ai_apply_ollama_profile.ps1` | Applies Ollama environment/profile settings and restarts runtime. | GUARDED_WRITE | Yes | No | Local Ollama runtime | No | No | No | Hidden | System/runtime confirmation | `scripts/ai_apply_ollama_profile.ps1` | High | Mutates user environment/runtime process state. |
| `scripts/ws_test_runner.sh` | Runs test command and writes test output artifact. | GUARDED_WRITE | Yes | Possible test side effects | No | No | No | Only with safe command preview | Backend-only | Test command confirmation | `scripts/ws_test_runner.sh` | High | Blocks some unsafe test commands but arbitrary tests may still write. |
| `ws build --dry-run` | Parses/builds dry-run metadata and exits before plan/apply. | DRY_RUN_ONLY | Yes | No | No | No | Only if dry-run artifacts allowed | Yes | Allowed with `dry-run writes artifacts` label | None or light | `scripts/ws`; `scripts/ws_build.sh` | High | Creates build run artifacts before dry-run exit. |
| `ws task-split --dry-run` | Plans task split without creating task files. | DRY_RUN_ONLY | Yes | No | No | No | Only if scaffold writes allowed | Yes | Allowed with label | None or light | `scripts/ws`; `scripts/ws_task_split.sh` | High | Creates generated/inbox dirs before dry-run. |
| `ws feature-run --dry-run` | Writes feature dry-run readiness report. | DRY_RUN_ONLY | Yes | No | No | No | Only if dry-run artifacts allowed | Yes | Allowed with label | None or light | `scripts/ws`; `scripts/ws_feature_run.sh` | High | Writes `runs/feature_run_dry_run_<timestamp>.md`. |
| `ws learning-run --session --dry-run` | Writes learning session plan/log/state without model call. | DRY_RUN_ONLY | Yes | No | No | No | Only if dry-run artifacts allowed | Yes | Allowed in TUI plain mode | Light in TUI | `scripts/ws`; `scripts/ws_learning_run.sh`; `tui/app.py` `LEARNING_DRY_RUN_ALLOWLIST` | High | TUI explicitly allows this exact dry-run path. |
| `ws learning-review-session --dry-run` | Writes learning review plan/log/state without model call. | DRY_RUN_ONLY | Yes | No | No | No | Only if dry-run artifacts allowed | Yes | Allowed in TUI plain mode | Light in TUI | `scripts/ws`; `scripts/ws_learning_review_session.sh`; `tui/app.py` `LEARNING_DRY_RUN_ALLOWLIST` | High | TUI explicitly allows this exact dry-run path. |
| `ws learning-action-pack --dry-run` | Generates a dry-run learning action pack from existing stronghold state. | DRY_RUN_ONLY | No | No | No | No | Yes | Yes | Hidden in current TUI | None | `scripts/ws`; `scripts/ws_learning_action_pack.sh`; `scripts/learning_action_pack.py` | High | Requires `--dry-run`; no writes, models, providers, or agents. |
| `ws learning-pointer-plan` | Generates a dry-run learning next task pointer update plan from existing stronghold state and confirmation ledger. | DRY_RUN_ONLY | No | No | No | No | Yes | Yes | Hidden in current TUI | None | `scripts/ws`; `scripts/ws_learning_pointer_plan.sh`; `scripts/learning_pointer_update_planner.py`; `scripts/test_learning_pointer_update_planner.py` | High | Wrapper/planner enforce `--dry-run`; reads `state.json` and `learning_confirmations.jsonl` and prints a proposed pointer update only; apply path is not implemented. |
| `ws learning-state-sync-plan` | Generates a dry-run learning state synchronization plan from existing stronghold state and confirmation ledger. | DRY_RUN_ONLY | No | No | No | No | Yes | Yes | Hidden in current TUI | None | `scripts/ws`; `scripts/ws_learning_state_sync_plan.sh`; `scripts/learning_state_sync_planner.py` | High | Wrapper/planner enforce `--dry-run`; reads `state.json` and `learning_confirmations.jsonl` and prints proposed sync changes only; apply path is not implemented. |
| `ws learning-state-sync-apply` | Applies eligible learning state synchronization changes. | GUARDED_WRITE | Yes | No | No | No | No | No | Hidden | Required | `scripts/ws`; `scripts/ws_learning_state_sync_apply.sh`; `scripts/learning_state_sync_apply.py` | High | Route supports `--dry-run` preview and `--confirm-sync` apply mode; confirm-sync creates `state_backups`, rewrites learning `state.json`, and appends `state_sync_audit.jsonl` without model/provider/agent calls. |
| `ws learning-ledger-repair` | Repairs legacy learning confirmation ledger artifact paths. | GUARDED_WRITE | Yes | No | No | No | No | No | Hidden | Explicit | `scripts/ws`; `scripts/ws_learning_ledger_repair.sh`; `scripts/learning_confirmation_ledger_repair.py` | High | Route supports `--dry-run` preview and `--repair-ledger` apply mode; repair mode creates `ledger_backups`, rewrites `learning_confirmations.jsonl`, and appends `ledger_repair_audit.jsonl` without modifying `state.json`. |
| `ws learning-advancement-plan` | Generates a dry-run learning advancement readiness plan from existing stronghold state and audit artifacts. | DRY_RUN_ONLY | No | No | No | No | Yes | Yes | Hidden | None | `scripts/ws`; `scripts/ws_learning_advancement_plan.sh`; `scripts/learning_advancement_readiness_planner.py` | High | Wrapper and planner enforce `--dry-run` only; reads `state.json`, `learning_confirmations.jsonl`, and `state_sync_audit.jsonl`, and may call the pointer planner in dry-run JSON mode only. |
| `ws learning-advancement-review` | Generates a dry-run human advancement review summary or writes a local advancement review packet for a learning stronghold. | LOCAL_REPORT_WRITE | Yes | No | No | No | Only if local reports allowed | Yes | Hidden | Light | `scripts/ws`; `scripts/ws_learning_advancement_review.sh`; `scripts/learning_advancement_review_packet.py` | High | Requires either `--dry-run` or `--create-packet`; dry-run reads stronghold state and planner outputs only, while `--create-packet` writes a review packet under `strongholds/learning/<id>/review_packets/` with no model/provider/agent calls. |
| `ws learning-confirm --dry-run` | Previews learning action confirmation without writing artifacts. | DRY_RUN_ONLY | No | No | No | No | Yes | Yes | Hidden in current TUI | None | `scripts/ws`; `scripts/ws_learning_confirm.sh`; `scripts/learning_confirmation_core.py` | High | Requires `--dry-run`; reads learning state and prints a proposed confirmation record only. |
| `ws research-run --review-paper --dry-run` | Writes research review plan/placeholders without model call. | DRY_RUN_ONLY | Yes | No | No | No | Only if dry-run artifacts allowed | Yes | Hidden or guarded | Light | `scripts/ws`; `scripts/ws_research_run.sh` | High | Research cockpit is not implemented in TUI source. |
| `ws worktree-create --dry-run` | Writes worktree create dry-run report. | DRY_RUN_ONLY | Yes | No | No | No | Only if dry-run artifacts allowed | Yes | Allowed with label | None or light | `scripts/ws`; `scripts/ws_worktree_create.sh` | High | Does not create branch/worktree. |
| `ws worktree-sync --dry-run` | Writes worktree sync dry-run report. | DRY_RUN_ONLY | Yes | No | No | No | Only if dry-run artifacts allowed | Yes | Allowed with label | None or light | `scripts/ws`; `scripts/ws_worktree_sync.sh` | High | Does not merge. |
| `ws quant` | Dispatches the Quant foundation CLI to local validation and inspection subcommands. | DRY_RUN_ONLY | No | No | No | No | Yes | Yes | Hidden | None | `scripts/ws`; `scripts/quant/cli.py`; `scripts/quant/contracts.py`; `scripts/quant/schema.py`; `scripts/quant/freshness.py`; `scripts/quant/paths.py` | High | Base route prints help when no subcommand is given and currently dispatches only to read-only or in-memory dry-run checks; no quantization, model loading, provider calls, or file mutation paths are implemented. |
| `ws quant data-contract-check` | Validates Quant YAML contracts. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws`; `scripts/quant/cli.py` | High | Reads YAML only. |
| `ws quant data-schema-check` | Validates sample OHLCV schema. | DRY_RUN_ONLY | No | No | No | No | No | Yes | Allowed | None | `scripts/ws`; `scripts/quant/cli.py` | High | In-memory dry-run only; available in SAFE_DRY_RUN, not READ_ONLY_STRICT. |
| `ws quant data-freshness-check` | Checks data freshness policy. | DRY_RUN_ONLY | No | No | No | No | No | Yes | Allowed | None | `scripts/ws`; `scripts/quant/cli.py` | High | Arithmetic check only; available in SAFE_DRY_RUN, not READ_ONLY_STRICT. |
| `ws quant data-ingest-fixture` | Fetches and validates synthetic fixture OHLCV data and can write a tiny local fixture artifact under approved quant paths. | LOCAL_REPORT_WRITE | Yes | No | No | No | No | Yes | Hidden | Light | `scripts/ws`; `scripts/quant/cli.py`; `scripts/quant/ingest.py`; `scripts/quant/persistence.py`; `scripts/quant/storage.py` | High | Uses a deterministic local fixture adapter with no network/provider/model calls; default flow is dry-run, but `--write-fixture` can write a local `data/quant/raw/.../*.json.fixture` artifact, so TUI dispatch remains disabled and preview-only. |
| `ws quant dataset-catalog` | Scans and lists Quant datasets. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws`; `scripts/quant/cli.py`; `scripts/quant/catalog.py` | High | Path scanning only; no data reads during cataloging. |
| `ws quant dataset-profile` | Profiles a Quant dataset. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws`; `scripts/quant/cli.py`; `scripts/quant/analytics.py` | High | Reads approved data files to generate metadata profile. |
| `ws quant analytics-capabilities` | Detects local analytics libraries. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws`; `scripts/quant/cli.py`; `scripts/quant/analytics.py` | High | Capability probing only. |
| `ws quant feature-contract-check` | Validates Quant feature building contract. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws`; `scripts/quant/cli.py`; `scripts/quant/features.py` | High | Reads YAML only. |
| `ws quant feature-build` | Builds research features from a dataset. | LOCAL_REPORT_WRITE | Yes | No | No | No | No | Yes | Hidden | Light | `scripts/ws`; `scripts/quant/cli.py`; `scripts/quant/features.py`; `scripts/quant/persistence.py` | High | Deterministic feature calculation; default is dry-run. No trading signals generated. |
| `ws quant persistence-capabilities` | Detects local persistence libraries. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws`; `scripts/quant/cli.py`; `scripts/quant/persistence.py` | High | Capability probing only. |
| `ws quant paths-check` | Verifies approved quant paths. | PURE_READ | No | No | No | No | Yes | Yes | Allowed | None | `scripts/ws`; `scripts/quant/cli.py` | High | Path inspection only. |
| `ws agent-run --dry-run` | Writes agent run work order/report without launching Codex. | DRY_RUN_ONLY | Yes | No | No | No | Only if dry-run artifacts allowed | Yes | Allowed with label | Light | `scripts/ws`; `scripts/ws_agent_run.ps1`; `WORKSTATION_MANUAL.md` | High | Plan-only run artifact. |
| `ws agent-run-worktree --dry-run` | Writes worktree agent dry-run packet/report without launching Codex. | DRY_RUN_ONLY | Yes | No | No | No | Only if dry-run artifacts allowed | Yes | Hidden or guarded | Light | `scripts/ws`; `scripts/ws_agent_run_worktree.sh` | High | Produces dry-run packet. |
| `ws ask` | Builds local context and calls local Ollama for an answer. | AGENT_RUN | Yes | No | Local Ollama | No | No | Depends; no apply | Guarded | Model confirmation | `scripts/ws`; `scripts/ai_run.sh`; `scripts/ollama_call.py` | High | Writes `runs/<timestamp>_*` answer artifacts. |
| `ws global` | Runs local-model global question workflow. | AGENT_RUN | Yes | No | Local Ollama | No | No | Depends; no apply | Guarded | Model confirmation | `scripts/ws`; `scripts/ai_global.sh`; `scripts/ollama_call.py` | High | Writes run artifacts. |
| `ws audit` | Runs local-model audit workflow. | AGENT_RUN | Yes | No | Local Ollama | No | No | Depends; no apply | Guarded | Model confirmation | `scripts/ws`; `scripts/ai_audit.sh`; `scripts/ollama_call.py` | High | Writes run artifacts; not same as `audit-workstation`. |
| `ws debug` | Runs local-model debug workflow. | AGENT_RUN | Yes | No | Local Ollama | No | No | Depends; no apply | Guarded | Model confirmation | `scripts/ws`; `scripts/ai_debug.sh`; `scripts/ollama_call.py` | High | May read log files passed by user; avoid secrets. |
| `ws task` | Runs local-model task planning/draft workflow. | AGENT_RUN | Yes | No observed | Local Ollama | No | No | Depends; no apply | Guarded | Model confirmation | `scripts/ws`; `scripts/ai_run_task.sh` | High | `--apply` path warns that apply is not implemented and still produces reviewable output. |
| `ws build --plan-only` | Creates build plan using local model and writes build artifacts. | AGENT_RUN | Yes | No | Local Ollama | No | No | Yes if no apply | Guarded | Model confirmation | `scripts/ws`; `scripts/ws_build.sh`; `scripts/ws_build_report.sh` | High | Local plan only; no project mutation. |
| `ws warm` | Warms selected local model through Ollama. | AGENT_RUN | No observed | No | Local Ollama | No | No | No | Guarded | Model/runtime confirmation | `scripts/ws`; `scripts/ai_warm_model.sh` | High | Refuses lab/big model unless explicitly allowed. |
| `ws unload` | Unloads active model from Ollama runtime. | AGENT_RUN | No observed | No | Local Ollama runtime | No | No | No | Guarded | Model/runtime confirmation | `scripts/ws`; `scripts/ai_unload_model.sh` | High | Runtime state change; no file write observed. |
| `ws feature-local-review` | Runs local Ollama review for feature artifacts. | AGENT_RUN | Yes | No | Local Ollama | No | No | Depends; no apply | Guarded | Model confirmation | `scripts/ws`; `scripts/ws_feature_local_review.sh` | High | Writes review/evidence/state artifacts. |
| `ws stronghold-local-checklist` | Runs local Ollama checklist generation for stronghold. | AGENT_RUN | Yes | No | Local Ollama | No | No | Depends; no apply | Guarded | Model confirmation | `scripts/ws`; `scripts/ws_stronghold_local_checklist.sh` | High | Writes checklist/evidence/state artifacts. |
| `ws learning-run --model` | Runs local Ollama tutor/session workflow. | AGENT_RUN | Yes | No | Local Ollama | No | No | Depends; no apply | Hidden or guarded | Model confirmation | `scripts/ws`; `scripts/ws_learning_run.sh`; `tui/app.py` `DISABLED_ACTIONS` | High | Model-backed learning actions are disabled in TUI source. |
| `ws learning-assess` | Runs local Ollama assessment workflow. | AGENT_RUN | Yes | No | Local Ollama | No | No | No | Hidden | Model confirmation | `scripts/ws`; `scripts/ws_learning_assess.sh`; `tui/app.py` `DISABLED_ACTIONS` | High | Disabled in TUI source. |
| `ws research-run --model` | Runs local Ollama paper/research workflow. | AGENT_RUN | Yes | No | Local Ollama | No | No | Depends; no apply | Hidden or guarded | Model and source confirmation | `scripts/ws`; `scripts/ws_research_run.sh` | High | Reads supplied source text and writes research artifacts. |
| `ws loop-start --mode local-plan` | Starts loop by running local build plan workflow. | AGENT_RUN | Yes | No | Local Ollama | No | No | Depends; no apply | Hidden or guarded | Model/workflow confirmation | `scripts/ws`; `scripts/ws_loop_start.sh`; `scripts/ws_build.sh` | High | Calls `ws_build.sh --plan-only`. |
| `ws task-split --llm` | Uses local model to split task and write generated task artifacts. | AGENT_RUN | Yes | No | Local Ollama | No | No | Only dry-run variant | Guarded | Model confirmation | `scripts/ws`; `scripts/ws_task_split.sh` | Medium | Local model flag path inferred from source. |
| `scripts/ollama_call.py` | Direct helper for local Ollama chat calls. | AGENT_RUN | No by itself | No | Local Ollama | No | No | Depends | Backend-only | Model confirmation | `scripts/ollama_call.py` | High | Helper called by multiple workflows. |
| `scripts/warm_model.ps1` | Direct local model warm helper. | AGENT_RUN | No observed | No | Local Ollama | No | No | No | Backend-only | Model/runtime confirmation | `scripts/warm_model.ps1` | High | Also checks local runtime/GPU status. |
| `scripts/ai_model_bench.sh` | Benchmarks local model and writes benchmark output. | AGENT_RUN | Yes | No | Local Ollama | No | No | No | Hidden | Model/runtime confirmation | `scripts/ai_model_bench.sh` | High | Benchmark/report artifact write. |
| `scripts/benchmark_ollama.sh` | Direct local Ollama benchmark path. | AGENT_RUN | Yes | No | Local Ollama | No | No | No | Hidden | Model/runtime confirmation | `scripts/benchmark_ollama.sh` | High | Related workstation command path, not `ws` subcommand. |
| `scripts/benchmark_ollama_v2.sh` | Direct local Ollama benchmark path. | AGENT_RUN | Yes | No | Local Ollama | No | No | No | Hidden | Model/runtime confirmation | `scripts/benchmark_ollama_v2.sh` | High | Related workstation command path, not `ws` subcommand. |
| `ws escalate codex` | Sends redacted packet to Codex CLI in read-only sandbox. | PROVIDER_CALL | Yes | No intended | Codex CLI | Yes | No | No | Hidden or strongly guarded | Provider/cloud confirmation | `scripts/ws`; `scripts/ws_escalate.sh`; `START_HERE.md` | High | `claude` and `gemini` paths are manual-only; `codex` can invoke external CLI. |
| `ws agent-canary` | Runs Codex canary and writes scratch/status artifacts. | PROVIDER_CALL | Yes | No intended | Codex CLI | Yes | No | No | Hidden | Provider/cloud confirmation | `scripts/ws`; `scripts/ws_agent_canary.ps1`; `scripts/ws_agent_run.ps1` | High | Canary asks Codex to append to scratch file and writes status JSON. |
| `ws agent-run` | Runs Codex-backed bounded agent workflow. | PROVIDER_CALL | Yes | Yes, through allowed files | Codex CLI | Yes | No | Only `--dry-run` path | Hidden or strongly guarded | Provider, branch, dirty-worktree confirmation | `scripts/ws`; `scripts/ws_agent_run.ps1`; `WORKSTATION_MANUAL.md` | High | Can create branches and mutate project/workstation files through allowlist/gates. |
| `ws agent-run-worktree --apply` | Runs Codex agent inside a prepared worktree. | PROVIDER_CALL | Yes | Yes, worktree/project | Codex CLI | Yes | No | No | Hidden or strongly guarded | Provider and worktree confirmation | `scripts/ws`; `scripts/ws_agent_run_worktree.sh`; `scripts/ws_agent_run.ps1` | High | Requires dry-run packet/worktree validation. |
| `ws agent-validate` | Runs validation report plus agent status, canary, and agent dry-run. | PROVIDER_CALL | Yes | Scratch/auto-run artifacts | Codex canary | Yes | No | No | Hidden | Provider/cloud confirmation | `scripts/ws`; `scripts/ws_agent_validate.sh`; `scripts/ws_agent_run.ps1` | High | Name sounds like status, but it invokes canary behavior. |
| `ws build --apply --escalate codex` | Applies build patch and can escalate to Codex. | PROVIDER_CALL | Yes | Yes | Local Ollama and optional Codex | Yes | No | No | Hidden | Provider, branch, apply confirmation | `scripts/ws`; `scripts/ws_build.sh` | High | Highest-risk build path. |
| `scripts/ai_model_pull.sh` | Pulls/downloads model through Ollama API. | PROVIDER_CALL | Yes, model storage | No | Ollama model registry | Yes/network | No | No | Hidden | Provider/network/storage confirmation | `scripts/ai_model_pull.sh` | High | Can download model files; not routed through `ws` in inspected wrapper. |
| `ws build --apply` | Applies generated patch to project after build gates. | GUARDED_WRITE | Yes | Yes | Local Ollama | Optional if escalation flag used | No | No | Hidden or strongly guarded | Branch/apply confirmation | `scripts/ws`; `scripts/ws_build.sh`; `scripts/ws_test_runner.sh` | High | Without escalation it is local model plus git apply/test workflow. |
| `ws cleanup-apply --apply` | Archives high-confidence cleanup candidates. | DESTRUCTIVE | Yes | No intended | No | No | No | No | Hidden | Strong typed confirmation | `scripts/ws`; `scripts/ws_cleanup_apply.sh` | High | Moves files/folders into archive; refuses without `--apply`. |
| `ws review` | Wrapper route points to missing script. | UNKNOWN | Unknown | Unknown | Unknown | Unknown | No | No | Hidden | Required after classification | `scripts/ws`; missing `scripts/ws_review.sh` | High | Entry point exists but target script was absent. |
| `ws stuck` | Wrapper route points to missing script. | UNKNOWN | Unknown | Unknown | Unknown | Unknown | No | No | Hidden | Required after classification | `scripts/ws`; missing `scripts/ws_stuck.sh` | High | Entry point exists but target script was absent. |

## 6. TUI Exposure Policy

| TUI Mode | Allowed Safety Classes | Hidden Safety Classes | Required UI Labeling |
|---|---|---|---|
| `READ_ONLY_STRICT` | `PURE_READ` only. | `LOCAL_REPORT_WRITE`, `DRY_RUN_ONLY`, `GUARDED_WRITE`, `AGENT_RUN`, `PROVIDER_CALL`, `DESTRUCTIVE`, `UNKNOWN`. | No write-capable labels needed because writes are not exposed. |
| `READ_ONLY_WITH_LOCAL_REPORTS` | `PURE_READ`, selected `LOCAL_REPORT_WRITE`. | `GUARDED_WRITE`, `AGENT_RUN`, `PROVIDER_CALL`, `DESTRUCTIVE`, `UNKNOWN`; selected `DRY_RUN_ONLY` only if explicitly allowed. | Every local-writing status command must show `writes local report/status`. |
| `SAFE_DRY_RUN` | `PURE_READ`, selected `LOCAL_REPORT_WRITE`, selected `DRY_RUN_ONLY`. | Apply-capable `GUARDED_WRITE`, `AGENT_RUN` unless model dry-run is explicitly reviewed, `PROVIDER_CALL`, `DESTRUCTIVE`, `UNKNOWN`. | Dry-run commands must show artifacts written and must say no project/provider mutation. |
| `OPERATOR_GUARDED` | Selected `PURE_READ`, `LOCAL_REPORT_WRITE`, `DRY_RUN_ONLY`, and `GUARDED_WRITE`. | `PROVIDER_CALL`, `DESTRUCTIVE`, `UNKNOWN` unless a separate confirmation flow exists. | Requires explicit confirmation text and post-run artifact path. |
| `PROVIDER_HANDOFF` | Selected `PURE_READ`, `LOCAL_REPORT_WRITE`, `DRY_RUN_ONLY`, `GUARDED_WRITE`, and explicit handoff commands. | Automatic provider execution, `DESTRUCTIVE`, `UNKNOWN`. | Must show target, redaction status, packet path, and manual-vs-automatic distinction. |
| `ADMIN_RECOVERY` | Explicitly selected recovery/admin commands only. | `UNKNOWN` until classified. | Must show destructive/move/archive warning and require typed confirmation. |

Required policy:

| Rule | Requirement |
|---|---|
| `READ_ONLY` | Hide or disable project mutation and provider mutation actions. |
| `SAFE_DRY_RUN` | Prefer plan/simulate commands and show whether local artifacts are written. |
| `LOCAL_REPORT_WRITE` | Label clearly if the active mode permits local reports. |
| `UNKNOWN` | Never expose in the TUI. |
| `AGENT_RUN` | Require explicit confirmation and display local model/provider/runtime used. |
| `PROVIDER_CALL` | Require explicit provider/cloud confirmation. |
| `DESTRUCTIVE` | Hidden unless a future explicit recovery/admin mode exists. |

## 7. READ_ONLY Ambiguity Resolution

Current observed behavior:

| Observation | Evidence | Implication |
|---|---|---|
| TUI source sets `SAFETY_MODE = "READ_ONLY"`. | `tui/app.py` | The UI presents itself as read-only. |
| TUI status allowlist includes `ready`, `stronghold-status`, `handoff-status`, `feature-status`, and `agent-hygiene`. | `tui/app.py` `STATUS_COMMANDS` | Some status commands are callable from the TUI. |
| `ws ready` writes readiness reports. | `scripts/ws_readiness.sh` | Not strict read-only. |
| `ws agent-hygiene` writes hygiene reports. | `scripts/ws_agent_hygiene.sh` | Not strict read-only. |
| `ws cleanup-status` creates cleanup/report/archive directories before listing status. | `scripts/ws_cleanup_status.sh` | Even status can have scaffold writes. |
| TUI docs say plain mode can execute only hardcoded safe dry-run planner actions. | `tui/README.md` | The implemented safety model already distinguishes read display from safe dry-run artifact writes. |

Recommended policy: Option C, split modes.

| Mode | Meaning | Why this fits the project |
|---|---|---|
| `READ_ONLY_STRICT` | Absolutely no writes, including local reports, caches, scaffolds, logs, registry refreshes, or dry-run artifacts. | Needed for future agents, audits, and tests that must prove no filesystem writes occurred. |
| `READ_ONLY_WITH_LOCAL_REPORTS` | No project mutation and no provider mutation, but selected local report/status writes are permitted and labeled. | Matches current TUI behavior more closely without pretending report-writing status commands are pure reads. |
| `SAFE_DRY_RUN` | No project/provider mutation, but selected dry-run plan artifacts may be written and must be reviewable. | Matches current learning dry-run allowlist and future planning workflows. |

Do not implement this policy in this document. The recommendation is to make the existing ambiguity explicit in docs, command metadata, and TUI labels before expanding TUI actions.

## 8. Required Confirmation Rules

| Action Type | Confirmation Level | Example | Reason |
|---|---|---|---|
| Pure read | No confirmation. | `ws projects` | No write or provider risk. |
| Local report write | No confirmation or light confirmation depending on mode. | `ws ready` | Writes controlled local artifacts; user should at least see that writes occur. |
| Dry-run artifact write | Light confirmation if triggered interactively. | `ws learning-run --session --dry-run` | Writes plans/logs/state but does not apply project/provider changes. |
| Local state/artifact mutation | Light confirmation. | `ws feature-new` | Creates or updates workstation workflow state. |
| Decision/progress mutation | Explicit confirmation. | `ws learning-advance` | Advances workflow state and can unblock later apply paths. |
| Branch/worktree mutation | Branch confirmation. | `ws worktree-create --apply` | Creates branch/worktree state that affects git workflows. |
| Dirty-worktree sensitive action | Dirty-worktree confirmation plus clean-state check where possible. | `ws build --apply`, `ws agent-run` | Avoids applying agent output into ambiguous local changes. |
| Local model invocation | Model/runtime confirmation. | `ws ask`, `ws build --plan-only` | May consume local compute and write model output artifacts. |
| Provider/cloud invocation | Provider/cloud confirmation. | `ws escalate codex`, `ws agent-run` | Can send context to cloud-backed tools. |
| Clipboard handoff | Clipboard confirmation. | `ws handoff-copy`, `ws handoff-import` | Clipboard can leak or import unintended context. |
| Destructive/archive/move | Strong typed confirmation. | `ws cleanup-apply --apply` | Moves or discards operational state. |
| Unknown command | Classification required before execution. | `ws review`, `ws stuck` | Missing or unclear target behavior. |

## 9. Dry-Run Policy

`SAFE_DRY_RUN` should guarantee:

| Guarantee | Requirement |
|---|---|
| No project mutation | Dry-run commands must not modify project source, project docs, generated project files, branches, worktrees, or git state. |
| No provider mutation | Dry-run commands must not call cloud/provider tools or perform automatic handoff. |
| No destructive action | Dry-run commands must not delete, archive, move, reset, or clean state. |
| Disclosed local writes | If dry-run writes local plans/logs/reports/state, the command output and TUI label must say so. |
| Reviewable output | Dry-run output should produce a stable artifact path where useful. |
| Clear simulated action | Output must state what would happen in apply mode and what did not happen. |
| No hidden model calls | If a dry-run uses a model, it must be classified as `AGENT_RUN` unless explicitly documented as a model-free plan. |

Observed examples:

| Command | Dry-run behavior |
|---|---|
| `ws build --dry-run` | Writes build run metadata/artifacts and exits before plan/apply. |
| `ws learning-run --session --dry-run` | Writes learning plan/log/state without model call; explicitly allowed by TUI plain mode. |
| `ws agent-run --dry-run` | Writes work order/report without launching Codex. |
| `ws worktree-create --dry-run` | Writes report without creating branch/worktree. |

## 10. Agent and Provider Policy

| Policy Area | Requirement |
|---|---|
| Local model commands | Commands that call Ollama must show model name, local endpoint/runtime, artifact path, and whether project files can be changed. |
| Cloud/provider commands | Commands that can invoke Codex, Gemini, Claude, browser automation, or other cloud-backed tools must require provider/cloud confirmation. |
| No implicit provider calls | Status, readiness, redaction, packet creation, and handoff creation must never invoke cloud providers implicitly. |
| Handoff distinction | Creating or copying a handoff is not the same as automatic cloud execution. The TUI must label manual handoff separately from provider invocation. |
| TUI display | Any model/provider action must show `LOCAL_MODEL`, `PROVIDER_CALL`, or `MANUAL_HANDOFF` before execution. |
| Artifact trail | Model/provider actions must write or reference reviewable artifacts, logs, packet paths, and response paths. |

Discovered local model paths include `ws ask`, `ws global`, `ws audit`, `ws debug`, `ws task`, `ws build --plan-only`, `ws warm`, `ws unload`, `ws feature-local-review`, `ws stronghold-local-checklist`, `ws learning-run --model`, `ws learning-assess`, `ws research-run --model`, `ws loop-start --mode local-plan`, and direct benchmark/warm helpers.

Discovered provider/cloud-capable paths include `ws escalate codex`, `ws agent-canary`, `ws agent-run`, `ws agent-run-worktree --apply`, `ws agent-validate`, `ws build --apply --escalate codex`, and direct model pull behavior through `scripts/ai_model_pull.sh`.

## 11. Degraded / Unknown Behavior

| State | Meaning | TUI Exposure | Next Safe Action |
|---|---|---|---|
| READY | Command is classified, dependencies are available, and safety gates are satisfied. | Expose according to safety class. | Show command or next safe action. |
| DEGRADED | Command is classified but a non-critical dependency or artifact is missing/stale. | Expose read/status actions; disable mutation. | Show repair/readiness action. |
| PARTIAL | Some required evidence or output exists, but not enough to complete workflow. | Expose status and review actions only. | Show missing artifact or stale step. |
| UNAVAILABLE | Dependency, script, model runtime, worktree, or provider is absent. | Hide apply/provider actions. | Show dependency check or setup instruction. |
| CHECK_FAILED | A safety, hygiene, redaction, readiness, branch, or dirty-worktree check failed. | Disable guarded actions. | Show failed check and remediation. |
| UNKNOWN | Command behavior is not classified. | Hidden. | Require source classification and test plan. |
| FAIL | Command failed during execution. | Show failure artifact/log if safe. | Show recovery or retry guidance; do not auto-advance. |

Rules:

| Condition | Required behavior |
|---|---|
| Missing script target | Mark command `UNKNOWN` and hide it. |
| Missing Ollama/WSL/GPU | Keep pure read/status visible; disable local model actions. |
| Failed redaction | Disable provider/cloud handoff. |
| Dirty worktree | Disable apply/agent/build mutation unless command has explicit dirty-worktree handling. |
| Stale decision or unresolved artifact | Disable advancement/apply; show review action. |

## 12. Recommended Changes

| Recommendation | Priority | Reason | Risk if not done |
|---|---|---|---|
| Add explicit command registry. | High | `scripts/ws` is authoritative but safety metadata is implicit in script behavior. | TUI and agents may expose unsafe commands by name alone. |
| Add machine-readable safety manifest. | High | Each command needs class, writes, provider use, confirmation, and TUI exposure metadata. | Safety policy will drift from implementation. |
| Split `READ_ONLY_STRICT` from `READ_ONLY_WITH_LOCAL_REPORTS`. | High | Current status commands can write reports despite read-only language. | Operators and agents may assume no writes occurred. |
| Add tests ensuring TUI never exposes disallowed classes. | High | TUI action availability should be enforced, not only documented. | Future UI changes may accidentally expose apply/provider actions. |
| Add command-level provider flags. | High | Provider use is spread across wrappers and helper scripts. | Cloud-capable commands may be misclassified. |
| Add command-level local write paths. | Medium | Local report writes are acceptable only if controlled and visible. | Report/cache writes can surprise strict read-only runs. |
| Add dry-run artifact contract. | Medium | Dry-run commands write artifacts inconsistently. | Operators may not know what changed during a dry-run. |
| Add canonical handoff schema. | Medium | Handoff commands write multiple files and metadata fields. | Import/review tooling can diverge. |
| Add provider handoff redaction gate tests. | Medium | Redaction is a core safety barrier. | Unsafe packets may be copied or sent. |
| Add snapshot tests for TUI action availability by mode. | Medium | Width/render tests are not enough; action policy needs snapshots too. | Visual polish could hide safety regressions. |
| Add missing-script checks for `ws review` and `ws stuck`. | Medium | Wrapper exposes routes whose targets were absent during inspection. | Users or agents may invoke undefined workflows. |
| Add explicit local model runtime policy. | Low | Ollama commands are local but still invoke models and mutate runtime state. | Local model actions may be treated as harmless reads. |

## 13. Open Questions

| Question | Why it matters |
|---|---|
| Which `ws` commands are canonical versus legacy? | The wrapper routes many commands; not all may be intended for TUI or future agents. |
| Should `READ_ONLY` allow local report writes? | Current behavior suggests yes for operator mode, but strict agent/audit mode needs no writes. |
| Which local report paths are safe in `READ_ONLY_WITH_LOCAL_REPORTS`? | Report writes need a bounded allowlist. |
| Should scaffold writes such as `mkdir -p` be treated like report writes? | Some status commands create directories before reading. |
| Which commands can call providers indirectly through helper scripts or installed CLIs? | Provider risk is not always visible from the top-level command name. |
| Should `agent-validate` be renamed or relabeled? | It invokes canary behavior and is not a pure validator. |
| Should handoff clipboard operations be considered provider/cloud actions or guarded local actions? | Clipboard is a boundary even when provider send is manual. |
| What is the minimum confirmation before any apply-capable action? | Build, agent, and worktree paths need consistent gates. |
| Should command safety metadata live in code, YAML, or docs? | TUI and agents need machine-readable enforcement. |
| Which dashboards/screens are allowed to trigger commands versus only display state? | Prevents accidental execution from visual UI elements. |
| What is the policy for direct scripts not routed through `ws`? | Some risky functionality exists outside the canonical wrapper. |
| Should raw Graphify output generation be allowed from TUI? | It can scan projects and write context outputs. |

## 14. Acceptance Criteria for This Document

This document is acceptable if:

| Criterion | Status |
|---|---|
| It lists discovered commands and entry points. | Met. |
| It classifies each command with evidence. | Met, with confidence levels. |
| It distinguishes pure reads from local report writes. | Met. |
| It identifies commands that can invoke agents/models/providers. | Met. |
| It identifies commands that can mutate project files. | Met. |
| It recommends a `READ_ONLY` policy. | Met; recommends split modes. |
| It gives clear TUI exposure rules. | Met. |
| It marks unknowns honestly. | Met; missing `ws review` and `ws stuck` targets are `UNKNOWN`. |
| It does not invent unsupported behavior. | Met; uncertain items are marked medium confidence or open questions. |
| It can guide future TUI and agent safety work. | Met. |
