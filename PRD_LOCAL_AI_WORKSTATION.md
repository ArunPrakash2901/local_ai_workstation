# PRD: Local AI Workstation

Generated: 2026-05-19  
Scope: as-built plus forward-looking product requirements for the existing `D:\_ai_brain` workstation control plane.

Evidence note: file paths in this PRD are relative to `D:\_ai_brain` unless shown as absolute paths. Claims are grounded in repository files inspected for this PRD. Where behavior is inferred from source or design reports rather than verified by executing commands, it is marked as inferred or open.

## 1. Executive Summary

The Local AI Workstation is a local-first workstation control plane centered on `D:\_ai_brain`. It gives a human operator one bounded command surface, one local artifact system, and one terminal cockpit for AI-assisted development, learning, research, and project work.

It is for a single workstation owner who works across Windows, WSL, local Ollama models, Graphify code context, task files, feature strongholds, learning strongholds, handoffs, and bounded agent runs. Its job is not to make the machine fully autonomous. Its job is to make local AI work safer, more visible, more reviewable, and less scattered.

The project already contains working parts:

| Existing capability | Evidence |
|---|---|
| Unified `ws` command dispatcher with project, model, task, feature, stronghold, handoff, worktree, agent, build, cleanup, and TUI commands | `scripts/ws` |
| Local model profile centered on Ollama `hermes3:8b` with 8192 context | `registry/models.yaml`, `registry/active_model.yaml`, `START_HERE.md`, `LOCAL_AI_STACK_STATUS.md` |
| Graphify-based project context and compact context pack generation | `START_HERE.md`, `global/GLOBAL_GRAPH_STATUS.md`, `scripts/ws_context_pack.sh`, `.graphifyignore` |
| Readiness, health, and frontier-provider checks | `scripts/ws_readiness.sh`, `scripts/check_health.ps1`, `scripts/ws_frontier_status.sh`, `reports/READINESS_20260519_214523.md` |
| Manual-first cloud/browser handoff workflow with durable local artifacts | `scripts/ws_handoff_new.sh`, `scripts/ws_handoff_copy.sh`, `scripts/ws_handoff_import.sh`, `scripts/ws_handoff_review.sh`, `reports/PHASE_2_HANDOFF_AUTOMATION_DESIGN.md` |
| Feature strongholds with contract, plan, validation, local review, handoff, report, and run preflight behavior | `features/workstation_control_plane/stabilize-ws-command-documentation/state.json`, `scripts/ws_feature_*.sh`, `reports/PHASE_3_FEATURE_STRONGHOLD_DESIGN.md`, `reports/PHASE_4_SUPERVISED_FEATURE_RUN_DESIGN.md` |
| Generic strongholds for learning, product, research, and trading-research | `strongholds/*/*/state.json`, `scripts/ws_stronghold_*.sh`, `reports/PHASE_5_GENERIC_STRONGHOLD_OPERATING_SYSTEM_DESIGN.md` |
| Learning workflow with plans, tutor sessions, human answers, assessments, decisions, review sessions, and advancement gates | `scripts/ws_learning_*.sh`, `strongholds/learning/fine-tuning-small-open-source-models/state.json`, `reports/PHASE_6_13_LEARNING_LIFECYCLE_MILESTONE_REVIEW.md` |
| Operator TUI/cockpit with Home, Learning, Artifacts, System screens, read-only/safe-dry-run framing, artifact viewer, and safe degraded display | `tui/app.py`, `tui/README.md`, `WORKSTATION_MANUAL.md`, `reports/PHASE_8_12_TUI_COCKPIT_INFORMATION_ARCHITECTURE_POLISH.md` |

The product should become a stable local control plane where every non-trivial AI-assisted workflow has:

- a bounded command entry point
- a clear safety state
- a current next safe action
- durable artifacts
- explicit human gates before external escalation or mutation
- compact local context before any cloud/browser handoff
- calm degraded-state handling when WSL, Ollama, GPU, Git, or provider checks fail

The next product work should consolidate the product model, command surface, state machines, handoff schema, TUI information architecture, and operator playbooks before increasing automation power.

## 2. Product Thesis

The Local AI Workstation is a safety-bounded, local-first control plane for AI-assisted development, learning, research, and project work. Its value is not simply running models or agents. Its value is making agentic work observable, reviewable, reversible where possible, and grounded in local context before any escalation to cloud models or mutation-capable agents.

Repository evidence supports this thesis:

- `START_HERE.md` describes a daily flow that starts with `ws daily`, `ws warm`, `ws status`, `ws ready`, then moves through task selection, local planning, and bounded agent execution only after review.
- `WORKSTATION_MANUAL.md` states that Graphify and Ollama are local primitives, browser models are human-gated strategic reasoning lanes, and execution is performed through bounded agents or worktrees.
- `scripts/ws_context_pack.sh` explicitly tells generated build context not to read or modify secrets, raw datasets, model files, archives, build outputs, dependency folders, `.git`, or `graphify-out`.
- `tui/README.md` states that the operator TUI is intentionally read-only by default and can execute only hardcoded safe learning dry-run planners in plain mode.
- `reports/PHASE_2_HANDOFF_AUTOMATION_DESIGN.md` states that handoffs should prepare, copy, import, and review prompts locally, not invoke providers or automate browsers implicitly.

The product thesis should therefore remain:

> Local-first context, explicit gates, durable artifacts, and visible safety state are the product. Models and agents are replaceable execution lanes behind that control plane.

## 3. Problem Statement

The project solves these concrete problems:

| Problem | Why it matters | Evidence |
|---|---|---|
| Local AI workflows scatter across terminals, scripts, docs, prompts, model profiles, Graphify outputs, and agents. | The operator loses track of current state, latest artifact, and next safe action. | `WORKSTATION_MANUAL.md`, `scripts/ws`, `reports/PHASE_8_TUI_OPERATOR_COCKPIT_DESIGN.md` |
| Agentic coding can become unsafe without bounded execution modes and explicit file boundaries. | Unbounded agents can modify unexpected files, run too long, or operate on dirty repos. | `scripts/ws_agent_run.ps1`, `scripts/ws_apply_ready.sh`, `scripts/ws_apply_guard.sh`, `features/.../feature_contract.md` |
| Context must be reduced and ranked before cloud tools see it. | Uploading raw local folders, datasets, secrets, or huge graphs is unsafe and inefficient. | `START_HERE.md`, `scripts/ws_context_pack.sh`, `.graphifyignore`, `reports/PHASE_2_HANDOFF_AUTOMATION_DESIGN.md` |
| Operators need visibility into what the system knows, what is safe, what is blocked, and what to do next. | Without a cockpit, the operator must reconstruct state from many files and command outputs. | `tui/app.py`, `tui/README.md`, `reports/PHASE_8_12_TUI_COCKPIT_INFORMATION_ARCHITECTURE_POLISH.md` |
| Learning, research, and project workflows need traceable artifacts and decisions. | The workstation is used for more than code mutation; evidence and human progress must be auditable. | `strongholds/learning/.../state.json`, `scripts/ws_learning_*.sh`, `scripts/ws_research_*.sh`, `reports/PHASE_6_13_LEARNING_LIFECYCLE_MILESTONE_REVIEW.md` |
| Windows/WSL/local-model workflows need a reliable control surface. | Ollama runs on Windows, scripts run in WSL, and path bridging is a recurring operational risk. | `START_HERE.md`, `registry/paths.yaml`, `scripts/ws_env.sh`, `scripts/check_health.ps1`, `reports/WORKSTATION_CONSOLIDATION_AUDIT.md` |

## 4. Target Users

### Primary User: Workstation Operator / Owner

Goals:

- Start each day with a clear machine-readiness signal.
- Use local models and Graphify before cloud escalation.
- Select one task, plan it locally, and only then consider bounded execution.
- Track strongholds, decisions, handoffs, artifacts, and stale evidence.
- Know the next safe action without remembering every command.

Frustrations:

- Too many commands and historical artifacts.
- Reconstructing latest state from reports, run folders, strongholds, handoffs, and Git.
- Uncertainty about whether a model, provider, or agent can safely run.
- Windows/WSL path ambiguity.
- Concern that tools may inspect secrets, raw data, model files, or large outputs.

The workstation must provide:

- A stable `ws` command surface.
- A TUI cockpit with obvious safety state and next action.
- Durable local artifacts.
- Explicit handoff and apply gates.
- Clear degraded-state messaging.

### Secondary User: Future Local Agents

Goals:

- Read current project state without scanning unsafe paths.
- Use canonical commands instead of ad hoc shell actions.
- Produce bounded artifacts that a human can review.
- Avoid dirty-worktree and stale-context mistakes.

Frustrations:

- Ambiguous source of truth.
- Multiple similar reports and generated folders.
- Unsafe context surfaces.

The workstation must provide:

- Machine-readable state files.
- A documented command contract.
- Artifact schemas and freshness rules.
- Safety constraints that are easy to follow from code and docs.

### Secondary User: Cloud Agents Receiving Handoffs

Goals:

- Receive compact, relevant context.
- Understand constraints, allowed files, non-goals, and current safety state.
- Avoid requesting secrets or raw data.
- Return a plan or review that can be imported and classified locally.

Frustrations:

- Missing context.
- Overloaded prompts with raw dumps.
- No clear boundary between reasoning and mutation.

The workstation must provide:

- Local context packs.
- Redaction before escalation.
- Handoff metadata and transcript storage.
- Explicit "no permission to modify files" instructions unless a separate apply path is invoked.

### Secondary User: Human Reviewers Of Project State

Goals:

- Understand what happened, what is current, what is stale, and what is blocked.
- Review evidence without replaying shell history.

Frustrations:

- Historical report noise.
- Generated files mixed with curated docs.
- Unclear whether an artifact came from local, browser, CLI, or human input.

The workstation must provide:

- Reports with provenance.
- A documented artifact model.
- Current-state summaries.
- Clear separation between implemented behavior and design-only reports.

### Secondary User: Future Collaborators

Goals:

- Onboard without inheriting unsafe assumptions.
- Use the workstation without accidentally running mutation or cloud escalation.

Frustrations:

- Local machine assumptions and hardcoded paths.
- Missing state machine documentation.

The workstation must provide:

- Project-level onboarding docs.
- Safety-first command guides.
- A PRD and manual that distinguish stable behavior from experiments.

## 5. Current As-Built Scope

| Component | Current behavior | Evidence | Confidence | Notes |
|---|---|---|---|---|
| Workstation root | `D:\_ai_brain` is the current live control plane root. | `START_HERE.md`, `registry/paths.yaml`, `scripts/ws_env.sh` | High | `D:\Local_AI_Workstation` appears as a future parent skeleton, not active. |
| `ws` command surface | Unified dispatcher routes subcommands to Bash, PowerShell, and Python-backed scripts. | `scripts/ws` | High | Canonical command surface is in script source/help text. |
| Daily startup | Docs recommend `ws daily`, `ws warm`, `ws status`, `ws ready`. | `START_HERE.md`, `WORKSTATION_MANUAL.md` | High | `ws ready` writes reports; see safety-model ambiguity. |
| Readiness check | Generates timestamped readiness report with health, model/KV config, project registry, and frontier status. | `scripts/ws_readiness.sh`, `reports/READINESS_20260519_214523.md` | High | Latest inspected report shows Ollama degraded but GPU OK. |
| Health checks | Checks Ollama API, WSL connectivity to Ollama, loaded models, and NVIDIA GPU status. | `scripts/check_health.ps1` | High | Windows-side PowerShell script. |
| Local model profile | `hermes3:8b` is active daily model with 8192 context. | `registry/active_model.yaml`, `registry/models.yaml`, `START_HERE.md` | High | Other local models exist as profiles. |
| Local model runtime | Ollama is the configured runtime with WSL access through localhost. | `LOCAL_AI_STACK_STATUS.md`, `FINAL_RECOMMENDED_PROFILE.md`, `scripts/ollama_call.py` | High | Current runtime may be unavailable at a given time; latest readiness report showed failure. |
| Graphify context workflow | Graphify is used to build local project graphs and compact query context before handoffs/builds. | `START_HERE.md`, `global/GLOBAL_GRAPH_STATUS.md`, `scripts/ws_context_pack.sh` | High | Raw `graphify-out` content intentionally not inspected for this PRD beyond metadata. |
| Graphify exclusions | `.graphifyignore` excludes runs, logs, scratch, models, secrets, credentials, archives, etc. | `.graphifyignore` | High | `.gitignore` also ignores many generated runtime paths. |
| Project registry | Registry contains nine projects including the workstation itself, with graph status and safe-to-modify flags. | `registry/projects.yaml`, `reports/READINESS_20260519_214523.md` | High | Includes `workstation_control_plane`. |
| Build loop | `ws build` creates build runs, defaults to plan-only unless apply flag is given, builds context packs, calls local model, and can produce reports. | `scripts/ws_build.sh`, `scripts/ws_context_pack.sh`, `WORKSTATION_MANUAL.md` | High | Apply path exists but docs call primary apply path `ws agent-run`; build apply is secondary/local-diff-only. |
| Apply guard | Patch guard rejects denied paths, secret-looking names, and destructive/install/migration command text in patches. | `scripts/ws_apply_guard.sh` | High | Guard applies to `ws build --apply` patch path. |
| Apply readiness | `ws apply-ready` checks pre-execution conditions and prints next safe `ws agent-run` command on success. | `scripts/ws_apply_ready.sh` | High | Includes cloud canary/stale run checks. |
| Agent run | Windows-native PowerShell runner can create agent branches, run Codex when allowed, enforce timeouts, parse allowed files, and write reports/status files. | `scripts/ws_agent_run.ps1`, `WORKSTATION_MANUAL.md` | Medium | Actual unattended Codex execution depends on canary/config; PRD should not assume it is always enabled. |
| Agent hygiene | Audits agent branches, stale run folders, generated report ignore status, and unresolved `CODEX_RUNNING` folders. | `scripts/ws_agent_hygiene.sh`, `reports/AGENT_HYGIENE_20260519_214534.md` | High | Latest inspected report showed 0 unresolved stale `CODEX_RUNNING` folders. |
| Worktree isolation | Worktree plan/create/review/sync/status commands exist with dry-run/apply-from-report gating and path checks. | `scripts/ws_worktree_*.sh`, `WORKSTATION_MANUAL.md` | High | Apply operations are guarded by report matching and approved roots. |
| Feature strongholds | Feature folders contain contracts, allowed files, plans, validation evidence, local reviews, handoffs, reports, and state. | `features/workstation_control_plane/stabilize-ws-command-documentation/state.json`, `scripts/ws_feature_*.sh` | High | Current example state is `VALIDATED_LOCAL`. |
| Generic strongholds | Stronghold commands support typed workspaces for learning, product, feature, research, and trading-research. | `scripts/ws_stronghold_*.sh`, `strongholds/*/*/state.json` | High | Phase 5 design says design-only, but scripts now exist. |
| Learning workflow | Learning commands support dry-run session planning, tutor sessions, answer import, assessment, decisions, review sessions, and advancement. | `scripts/ws_learning_*.sh`, `strongholds/learning/fine-tuning-small-open-source-models/state.json`, `reports/PHASE_6_13_LEARNING_LIFECYCLE_MILESTONE_REVIEW.md` | High | Assessment requires answers explicitly linked to the current tutor session. |
| Research workflow | Research commands support paper review planning, local notes, decisions, and source registration. | `WORKSTATION_MANUAL.md`, `scripts/ws_research_*.sh`, `strongholds/research/agentic/state.json` | Medium | Less TUI integration than learning. |
| Handoff workflow | Handoffs create local folders with `prompt.md`, `context_pack.md`, `metadata.json`, `response.md`, `transcript.md`, and reports; copy/import/review update local state. | `scripts/ws_handoff_*.sh`, `reports/PHASE_2_HANDOFF_AUTOMATION_DESIGN.md`, `handoffs/*/metadata.json` | High | Browser lanes remain manual. |
| Frontier packets | `ws packet`, `ws redact`, and `ws escalate` prepare and gate frontier provider packets. | `scripts/ws_make_packet.sh`, `scripts/ws_redact_packet.sh`, `scripts/ws_escalate.sh`, `START_HERE.md` | High | Escalation runs redaction first and refuses unsafe packets. |
| TUI dashboard/cockpit | `ws tui` launches Python TUI with snapshot/plain/textual modes, read-only framing, Home/Learning/Artifacts/System screens, safe artifact viewer, and dry-run action allowlist. | `scripts/ws_tui.sh`, `tui/app.py`, `tui/README.md`, `WORKSTATION_MANUAL.md` | High | Textual optional; stdlib plain/snapshot must remain available. |
| TUI safety modes | TUI displays `READ_ONLY` and `SAFE_DRY_RUN`; model-backed learning, assessment, import, advance, providers, browser, mutation, apply, and trading are disabled from TUI. | `tui/app.py`, `tui/README.md` | High | Plain mode can execute only hardcoded learning dry-run planners. |
| TUI information architecture | Recent TUI polish emphasizes signal-first dashboard, hidden backend commands, safety footer, limited handoff rows, agent hygiene summary, and artifact highlights. | `reports/PHASE_8_12_TUI_COCKPIT_INFORMATION_ARCHITECTURE_POLISH.md`, `tui/app.py` | High | Existing dirty files contain this current TUI work; PRD did not modify them. |
| Cleanup/audit | Workstation audit and cleanup plan/status/apply commands exist; apply is archive-only and requires `--apply`. | `scripts/ws_audit_workstation.sh`, `scripts/ws_cleanup_*.sh`, `START_HERE.md` | High | Excludes projects, models, raw data, secrets, and unsafe paths. |
| Reports/manuals/task files | Repo contains manuals, design reports, implementation reports, task queues, generated tasks, and feature reports. | `WORKSTATION_MANUAL.md`, `START_HERE.md`, `reports/`, `tasks/` | High | Many reports are generated/history and not all are source-of-truth. |

## 6. Product Principles

1. Safety before automation.
2. Local-first before cloud escalation.
3. Read-only and dry-run states must be obvious.
4. The operator must always know the next safe action.
5. Artifacts and decisions should be traceable.
6. Context should be reduced before being handed off.
7. The system should degrade calmly when checks fail.
8. No secrets, credentials, or large raw data should be inspected casually.
9. Rendering/UI changes must not change execution semantics.
10. Agent work must be observable and reviewable.
11. `ws` remains the backend API; the TUI must not bypass it.
12. Human approval is required before irreversible boundaries.
13. Generated runtime artifacts are evidence, not hidden state.
14. Cloud/browser lanes are reasoning lanes unless a separate explicit apply command is invoked.
15. Worktree isolation should be preferred before mutation-capable workflows.

## 7. Non-Goals

This project is not:

- A fully autonomous unattended coding system without review.
- A secrets scanner or credential manager.
- A general cloud agent orchestration SaaS.
- A replacement for Git.
- A tool that blindly runs write actions.
- A dashboard that hides safety state.
- A system that uploads raw local context to cloud tools by default.
- A large-data inspection tool.
- A live-trading or capital-deployment system.
- A browser automation product.
- A dependency installer or package manager.
- A universal project migration tool.
- A model benchmark harness, although benchmark reports may exist.
- A database-backed workflow platform, unless a future PRD explicitly adds that scope.

## 8. Safety Model

### 8.1 Core Modes

| Mode | Meaning | Implemented evidence | Operator implication |
|---|---|---|---|
| `READ_ONLY` | UI/control-plane surface should not mutate project code or invoke providers. | `tui/app.py`, `tui/README.md` | Safe for status and artifact inspection, but note that some read/status commands may still write generated reports. |
| `SAFE_DRY_RUN` | Only explicitly allowlisted dry-run actions may execute from the TUI. | `tui/app.py`, `tui/README.md` | Current TUI plain mode can run learning session dry-run planners only. |
| `plan-only` | Planning path that writes local run artifacts but does not modify project files. | `scripts/ws_build.sh`, `WORKSTATION_MANUAL.md` | Default build path before any apply. |
| `dry-run` | Preview/check path that proves eligibility and writes a report without performing the later mutation. | `scripts/ws_feature_run.sh`, `scripts/ws_worktree_create.sh`, `scripts/ws_worktree_sync.sh`, `scripts/ws_agent_run_worktree.sh` | Must be reviewed before supervised apply-from-report flows. |
| Guarded apply | A narrow mutation path gated by allowlists, clean repos, reports, recent dry-runs, branch/worktree checks, and explicit flags. | `scripts/ws_apply_guard.sh`, `scripts/ws_worktree_create.sh`, `scripts/ws_worktree_sync.sh`, `scripts/ws_agent_run.ps1` | Must require explicit operator action and review. |

Important ambiguity: the TUI and docs use `READ_ONLY` to mean no project/source mutation and no provider/browser execution. Some status commands such as `ws ready` and `ws agent-hygiene` write timestamped local reports. The product should explicitly document "read-only with report writes" versus "strict no-write" in a future safety contract.

### 8.2 State Table

| State | Meaning | Operator implication |
|---|---|---|
| `READY` | Checks passed or a component is usable. | Continue to the recommended next safe action. |
| `DEGRADED` | One or more checks failed, but the system can still show useful status. | Do not escalate automatically; inspect details and resolve blocker. |
| `PARTIAL` | Some checks or artifacts are available, others are missing or failed. | Treat recommendations cautiously; use detail view. |
| `UNAVAILABLE` | A command, dependency, or data source cannot be reached or resolved. | Do not infer success; use fallback/manual path. |
| `CHECK_FAILED` | The check itself failed or produced insufficient structured data. | Fix check execution before trusting the result. |
| `UNKNOWN` | State cannot be determined from current evidence. | Avoid action that depends on this state. |
| `FAIL` | A concrete failure was detected. | Stop progression until the failure is understood. |
| `BLOCKED_*` | A workflow-specific blocker prevents progression. | Follow printed next safe action; do not override silently. |
| `PROMPT_READY` | Handoff prompt is locally packaged for review. | Operator may review or copy depending on target. |
| `BROWSER_MANUAL_REQUIRED` | Browser handoff requires human paste/submit; no automation occurred. | Manual browser lane only. |
| `COPIED_TO_CLIPBOARD` | Prompt was explicitly copied. | Operator may paste manually and later import response. |
| `RESPONSE_IMPORTED` | Response has been captured locally. | Review/classify before using it. |
| `REVIEW_ACCEPTED` | Deterministic local review found the imported response structurally acceptable. | Preserve as evidence; execution still requires separate gates. |
| `REVIEW_NEEDS_ATTENTION` / `REVIEW_IMPORTED_UNCLASSIFIED` | Handoff review did not cleanly accept the response. | Human review required. |
| `VALIDATED_LOCAL` | Feature evidence passed local validation. | Eligible for feature-run dry-run or further supervised planning. |
| `LOCAL_CHECKLIST_READY` | Stronghold has a local checklist generated from architect plan. | Domain-specific work may begin under the relevant runner. |

### 8.3 What Must Never Happen

- The TUI must never call Codex, Gemini, Claude, browser automation, apply commands, model-backed assessment, answer import, or learning advancement unless a future phase explicitly enables and tests that lane.
- Cloud/browser escalation must never occur as an automatic fallback when local readiness is degraded.
- Secret, credential, `.env`, broker-key, private-key, raw dataset, model-weight, archive, binary, `.git`, dependency, and raw Graphify output files must not be read casually.
- Agent runs must not proceed without explicit allowed files and bounded execution parameters.
- Worktree or branch creation must not occur without dry-run/report gating where required.
- Cleanup must not delete or touch project repos, models, raw data, secrets, or unsafe paths.
- Trading-research strongholds must not connect to brokers, place orders, allocate capital, or perform live trading.

### 8.4 What Requires Explicit Confirmation

- Any provider/cloud/browser handoff leaving local context.
- Any copy-to-clipboard operation intended for a browser lane.
- Any import of browser/provider response.
- Any apply-capable command.
- Any worktree or branch creation.
- Any learning advancement that changes progress state.
- Any cleanup archive operation.
- Any dependency install or package manager operation.
- Any action that widens allowed files or source scope.

### 8.5 What Can Run Safely By Default

Subject to the "report writes" ambiguity:

- Reading manuals, source files, task files, state files, and reports.
- Listing directory names and file metadata.
- Displaying TUI snapshot/plain status.
- Showing command help from `scripts/ws`.
- Reading project registry and model profile config that do not contain secrets.
- Generating local status summaries where report writes are expected.
- Running dry-run planners only where explicitly allowlisted.

## 9. Information Architecture

The current TUI model is Home, Learning, Artifacts, and System. Evidence: `tui/app.py`, `tui/README.md`, `WORKSTATION_MANUAL.md`, `reports/PHASE_8_12_TUI_COCKPIT_INFORMATION_ARCHITECTURE_POLISH.md`.

### Home

Purpose:

- Provide mission-control view of the workstation.

Primary user questions answered:

- Am I safe?
- Is the machine healthy?
- What am I working on?
- What is blocked?
- What should I do next?

Key information shown:

- Mission-control banner.
- Readiness summary.
- Safety modes.
- Agent hygiene summary.
- Active stronghold.
- Work map.
- Handoff trail.
- Artifact lineage.
- Command stream.

Actions available:

- Navigate to Learning.
- Navigate to Artifacts.
- Navigate to System.
- Refresh.
- Show help.
- Run only the screen-dependent safe dry-run if allowlisted.

Should not show:

- Full raw paths by default.
- Long verbose readiness output by default.
- Backend commands unless explicitly revealed.
- Secrets, raw datasets, model files, raw Graphify content.

### Learning

Purpose:

- Provide active learning stronghold cockpit.

Primary user questions answered:

- What stronghold am I progressing?
- What learning/review state am I in?
- What artifact or review is stale?
- What is the next safe learning action?

Key information shown:

- Current learning stronghold.
- Current task/session status.
- Recommended next action.
- Risk/status.
- Provenance and freshness indicators.
- Artifact highlights.
- Safe action buttons.

Actions available:

- Run allowlisted safe dry-run planner.
- Open artifact browser.
- View latest plan.
- View latest assessment.
- Toggle backend command display where available.

Should not show:

- Model-backed tutor generation as executable unless explicitly enabled in a later phase.
- Assessment, import, or advancement as executable in current TUI.
- Full artifact body unless operator opens viewer.

### Artifacts

Purpose:

- Show artifact lineage and allow bounded read-only inspection.

Primary user questions answered:

- What files/artifacts exist?
- What is the lineage?
- Which decisions are current or stale?
- What handoffs exist?

Key information shown:

- Artifact lineage.
- Review artifacts.
- Recent handoffs.
- Artifact catalog with existence state, relative path, and timestamps.

Actions available:

- Open artifact browser.
- View latest review/session plan.
- View latest assessment.
- View latest decision.

Should not show:

- Non-markdown, binary, model, dataset, archive, secret, credential, `.git`, or outside-stronghold files.

### System

Purpose:

- Provide detailed machine, safety, and backend status.

Primary user questions answered:

- Is Ollama available?
- Is WSL available?
- Is GPU available?
- Is the branch clean?
- Are outputs ignored?
- Is hygiene OK?

Key information shown:

- Ollama, WSL, GPU, loaded model/config, project registry count.
- Safety envelope.
- Branch and unresolved agent run counts.
- Full readiness and hygiene details on demand.

Actions available:

- Refresh.
- Navigate back home.
- Inspect command stream.

Should not show:

- Raw secrets.
- Full generated report noise on the main cockpit.
- Large data/model file content.

## 10. TUI / Dashboard Requirements

The cockpit should remain a safety-first terminal application rather than a raw transcript of backend commands.

### Required Dashboard Elements

| Requirement | Status | Evidence / Notes |
|---|---|---|
| Mission-control banner | Implemented in plain/snapshot rendering. | `tui/app.py`, `reports/PHASE_8_12_TUI_COCKPIT_INFORMATION_ARCHITECTURE_POLISH.md` |
| Machine card | Implemented. | `tui/app.py` |
| Safety envelope card | Implemented. | `tui/app.py` |
| Active stronghold card | Implemented for learning focus. | `tui/app.py` |
| Blocker region | Implemented through blocker text and disabled reasons. | `tui/app.py`, `tui/README.md` |
| Next safe action | Implemented in Learning/Home flow. | `tui/app.py`, `reports/PHASE_8_12_TUI_COCKPIT_INFORMATION_ARCHITECTURE_POLISH.md` |
| Work map | Implemented in Home. | `tui/app.py` |
| Handoff trail | Implemented and capped to recent rows. | `tui/app.py`, `reports/PHASE_8_12_TUI_COCKPIT_INFORMATION_ARCHITECTURE_POLISH.md` |
| Artifact lineage | Implemented. | `tui/app.py` |
| Command stream | Implemented compactly. | `tui/app.py` |
| Footer key map | Implemented. | `tui/app.py` |
| Semantic color system | Implemented with token styling. | `tui/app.py` |
| No-color support | Implemented. | `tui/app.py` |
| `NO_COLOR` support | Implemented. | `tui/app.py` |
| Unicode/ASCII fallback | Implemented via `WS_TUI_ICONS`. | `tui/app.py`, `tui/README.md` |
| Safe render margin | Implemented by layout width calculation and clipping. | `tui/app.py` |
| Width safety at 100, 120, 160 columns | Required. Current code adapts at 100/120/150+ and stacks below 140. | `tui/app.py` |
| Stacked cards below 140 columns | Implemented/inferred from `can_render_card_columns`. | `tui/app.py` |
| Degraded-state clarity | Implemented through semantic statuses and unavailable snippets. | `tui/app.py`, `tui/README.md` |

### Acceptance Criteria

- `READ_ONLY` and `SAFE_DRY_RUN` are visible within 3 seconds of TUI launch or snapshot render.
- Any blocker for the recommended action is visible within 3 seconds.
- The next safe action is visible within 3 seconds.
- No line touches the terminal edge in normal supported widths.
- No border wraps at 100, 120, or 160 columns.
- Cards stack below 140 columns.
- Missing data renders calmly as `UNAVAILABLE`, `UNKNOWN`, `CHECK_FAILED`, or equivalent.
- Color is not the only signal.
- `NO_COLOR` disables color.
- ASCII fallback is available with `WS_TUI_ICONS=ascii`.
- Snapshot mode remains non-interactive and read-only.
- Plain mode remains dependency-free.
- `--textual` fails safely if Textual is absent.
- The TUI never expands execution capability beyond the backend allowlist.

## 11. Command Surface Requirements

Evidence source: `scripts/ws`, `WORKSTATION_MANUAL.md`, and related scripts.

Safety levels used below:

- Read: reads or prints status only, except possible generated report writes where noted.
- Local write: writes workstation artifacts/state only.
- Clipboard/manual: writes clipboard or imports clipboard response.
- Guarded mutation: can modify branches/worktrees/project files only behind explicit gates.
- External/provider: may invoke cloud/local provider lanes.
- Disabled/reserved: exposed but not intended for use.

| Command | Purpose | Read/write | Safe in READ_ONLY? | TUI exposure | Notes |
|---|---|---|---|---|---|
| `help` | Show command help. | Read | Yes | No direct screen | Evidence: `scripts/ws`. |
| `projects` | List registered projects. | Read | Yes | System/future | Uses registry. |
| `project` | Show one project. | Read | Yes | System/future | Registry-backed. |
| `ask` | Ask project-specific local question. | External/local model | No in TUI | Not current | Local model path; still model-backed. |
| `global` | Ask cross-project question. | External/local model | No in TUI | Not current | Local model path. |
| `graph` | Query knowledge graph. | Read/model-adjacent | Maybe | Future | Should not expose raw graph content by default. |
| `audit` | Project audit. | Local model/report likely | No in TUI | Future | Needs safety classification. |
| `debug` | Debug log. | Local model/report likely | No in TUI | Future | Must not read secrets/logs casually. |
| `task` | Legacy bounded implementation task. | Guarded mutation | No | No | Legacy/less preferred than build/agent path. |
| `build` | Local-first product build loop. | Local write; guarded mutation with `--apply` | Plan-only only with caveat | Future read/report | Default should be `--plan-only`. |
| `model` | Show active model config. | Read | Yes | System | Evidence: `scripts/ai_model_current.sh`. |
| `models` | List model profiles. | Read | Yes | System/future | Config only. |
| `use` | Switch active model profile. | Local write/config | No | No | Requires explicit operator action. |
| `warm` | Warm active/local model. | Local model runtime | No | No | Refuses lab models without flag. |
| `unload` | Unload models. | Runtime mutation | No | No | Safe utility but not read-only. |
| `kv` | List KV profiles. | Read | Yes | System/future | Config only. |
| `kvuse` | Switch KV profile. | Local write/config | No | No | Requires explicit operator action. |
| `daily` | Restore safe daily model/KV profile. | Runtime/config write | No | Future with confirmation | Calls unload/use profile. |
| `moe` | List lab profiles. | Read | Yes | System/future | Should not warm by default. |
| `ready` | Run readiness check and save report. | Local report write | Ambiguous | Current backend status | TUI uses readiness results; strict no-write mode unresolved. |
| `frontier` | Show provider status. | Local write/dirs possible | Maybe | System/future | Creates frontier dirs if missing. |
| `packet` | Create escalation packet. | Local write | No | Future | Local-first but cloud-bound artifact. |
| `redact` | Safety scan packet. | Read/local output | Yes if no write | Future | Must pass before escalation. |
| `escalate` | Explicit provider escalation. | External/provider | No | No | Refuses unless redaction safe. |
| `review` | Reserved. | Disabled/reserved | No | No | Help says do not use until enabled. |
| `stuck` | Reserved. | Disabled/reserved | No | No | Help says do not use until enabled. |
| `task-new` | Create canonical task. | Local write | No | Future | Task lifecycle. |
| `task-split` | Split structured PRD into generated tasks. | Local write; dry-run possible | Dry-run only | Future | Deterministic parsing path supported. |
| `task-status` | Show task lifecycle counts. | Read | Yes | Future/Home | Good candidate. |
| `task-next` | Print next task. | Read | Yes | Future/Home | Good next-action candidate. |
| `task-review` | Create/redact review packet. | Local write | No | Future | Does not send provider by itself. |
| `task-complete` | Mark task completed. | Local write | No | No | Requires human gate. |
| `task-block` | Mark task blocked. | Local write | No | No | Requires human reason. |
| `feature-new` | Create feature stronghold. | Local write | No | Future | No providers/apply. |
| `feature-plan` | Build local-only feature plan. | Local write | No | Future | Reads local files/Git metadata only. |
| `feature-validate` | Validate local feature readiness. | Local write | No | Future | No provider/apply per script report. |
| `feature-handoff` | Create feature-aware packet. | Local write | No | Future | Browser/manual targets. |
| `feature-report` | Generate feature report. | Local write | No | Future/read with confirmation | Synthesizes evidence. |
| `feature-status` | List feature strongholds. | Read | Yes | Current backend status | TUI allowlisted read command. |
| `feature-local-review` | Run local Ollama review gate. | Local model/write | No | No current execution | PURPLE/local model lane. |
| `feature-architect-handoff` | Create senior architect handoff. | Local write | No | Future | Manual browser lane. |
| `feature-run` | Feature run preflight; apply mode generates handoff/report. | Dry-run local write; apply guarded handoff | Dry-run no in strict read-only | Future | Current apply does not run automatic agent per script notes. |
| `stronghold-new` | Create typed stronghold. | Local write | No | Future | Types include learning/product/feature/research/trading-research. |
| `stronghold-status` | List generic strongholds. | Read | Yes | Current backend status | TUI allowlisted. |
| `stronghold-intake` | Generate intake questions. | Local write | No | Future | No provider/browser. |
| `stronghold-intake-import` | Import human answers. | Local write | No | Future | Updates contract/goals/constraints/state. |
| `stronghold-architect-handoff` | Create senior architect handoff. | Local write | No | Future | Manual browser lane. |
| `stronghold-plan-import` | Import architect plan from handoff. | Local write | No | Future | Safety warnings can block to human review. |
| `stronghold-local-checklist` | Generate local checklist with Ollama. | Local model/write | No | No current TUI execution | Requires local model. |
| `stronghold-report` | Generate stronghold report. | Local write | No | Future | Summarizes current state. |
| `stronghold-decision` | Classify next safe state/action. | Local write | No | Future | Deterministic state transition evidence. |
| `learning-run` | Plan/generate learning sessions. | Dry-run local write; model-backed local write | Dry-run only in TUI | Current safe-dry-run only | TUI allowlists only `--session --dry-run`. |
| `learning-import-answers` | Import human answers. | Local write | No | Disabled current TUI | Requires explicit file/path UX. |
| `learning-assess` | Assess answers with local model. | Local model/write | No | Disabled current TUI | Enforces linked answers. |
| `learning-decision` | Classify learning next action. | Local write | No | Disabled current TUI | Deterministic classifier. |
| `learning-review-session` | Plan targeted review session. | Local write dry-run | Dry-run only in TUI | Current safe-dry-run only | TUI allowlists `--dry-run`. |
| `learning-advance` | Advance learning task. | Local write/progress mutation | No | Disabled current TUI | Requires advance decision. |
| `research-run` | Plan/run research review. | Dry-run/model/write | Dry-run could be future | Future | Current TUI design reserved; not current main screen. |
| `research-decision` | Classify research state. | Local write | No | Future | Deterministic evidence evaluation. |
| `research-add-source` | Register source text. | Local write/copy | No | Future | Must avoid raw data/unsafe files. |
| `apply-ready` | Check if task ready for agent run. | Local report write | No strict read-only | Future | Prints next safe command. |
| `agent-run` | Run bounded Windows-native Codex task. | Guarded mutation/external | No | No | Must remain outside TUI for now. |
| `agent-run-worktree` | Prepare/run worktree agent packet/apply. | Dry-run/local write; apply guarded external | No current TUI | No | Requires worktree and dry-run gating. |
| `agent-status` | Show Windows agent status. | Read | Maybe | Future/System | PowerShell. |
| `agent-canary` | Run Codex canary. | External/local scratch write | No | No | Low-risk but provider execution. |
| `agent-import` | Import/inspect agent run folder. | Local read/write possible | No | Future | Manual recovery path. |
| `agent-validate` | Validate agent scripts. | Report write | No strict read-only | Future | Useful verification. |
| `agent-hygiene` | Audit agent branches/run folders. | Local report write | Ambiguous | Current backend status | TUI allowlisted; writes report. |
| `agent-mark-stale-reviewed` | Mark stale run reviewed. | Local write | No | No | Human remediation action. |
| `loop-plan` | Check local-loop eligibility. | Local report write | No strict read-only | Future | Does not start loop. |
| `loop-start` | Start supervised local-only planning loop. | Local write | No | No current TUI | Only local-plan mode supported by evidence. |
| `loop-status` | Show loop status reports. | Read/report | Yes | Future | Summarizes reports. |
| `worktree-plan` | Preview isolated worktree path. | Local report write | No strict read-only | Future | No worktree creation. |
| `worktree-create` | Dry-run or supervised create worktree. | Dry-run report; guarded mutation with `--apply --from-report` | Dry-run not strict read-only | Future | Apply path must verify fresh matching report. |
| `worktree-review` | Read-only audit of worktree diff/state. | Local report write | No strict read-only | Future | Does not modify worktrees. |
| `worktree-sync` | Preview or apply worktree sync. | Dry-run report; guarded mutation with report | No current TUI | No | Apply requires report. |
| `worktree-status` | Summarize worktrees and plans. | Local report write/read | Ambiguous | Future/System | States no create/delete/prune/move. |
| `handoff-new` | Create local-only handoff packet. | Local write | No | Future | No provider invoked. |
| `handoff-copy` | Copy handoff prompt to clipboard and update metadata. | Clipboard/local write | No | Future with confirmation | Refuses provider/browser automation metadata. |
| `handoff-import` | Import clipboard response. | Clipboard/local write | No | Future with confirmation | No semantic classification until review. |
| `handoff-review` | Deterministic local review of imported response. | Local write | No | Future | Does not verify technical correctness. |
| `handoff-status` | List recent handoffs. | Read | Yes | Current backend status | TUI allowlisted. |
| `status` | Combined health/model status. | Read/runtime check | Maybe | System/future | Calls PowerShell health script. |
| `tui` | Launch operator dashboard. | Read/local safe-dry-run depending mode | Yes with caveats | N/A | Must preserve snapshot/plain fallback. |
| `runs` | List recent run folders. | Read | Yes | Future/System | Metadata only. |
| `open-run` | Show run artifact paths. | Read | Yes | Future/System | Path display only. |
| `aliases` | Show legacy aliases. | Read | Yes | System/future | Docs say `ai*` aliases are legacy. |
| `paths` | Show path abstraction. | Read | Yes | System | Evidence: `scripts/ws_path_status.sh`, `registry/paths.yaml`. |
| `audit-workstation` | Read-only infrastructure audit. | Local report write | No strict read-only | Future/System | Excludes sensitive/project/model paths. |
| `cleanup-plan` | Generate cleanup plan. | Local write | No strict read-only | Future/System | No deletion. |
| `cleanup-apply` | Archive approved candidates. | Local mutation/archive | No | No | Requires `--apply`; archive-only. |
| `cleanup-status` | Show latest cleanup reports/plans. | Read | Yes | Future/System | Metadata/status. |
| `build-status` | Show latest build status. | Read | Yes | Future/System | Reads latest build run. |
| `build-runs` | List build runs. | Read | Yes | Future/System | Metadata only. |
| `open-build` | Summarize build run artifacts. | Read | Yes | Future/System | Reads report/status. |

Open question: the command surface should be exported into a generated, machine-readable command registry with safety level, write behavior, provider behavior, and TUI exposure. Currently this information is distributed across `scripts/ws`, manuals, and individual scripts.

## 12. Workflow Requirements

### 12.1 Workstation Readiness Check

Trigger:

- Start of day, before handoff, before model-backed work, before agent execution, before TUI use.

Inputs:

- Windows Ollama endpoint.
- WSL network connectivity.
- GPU status.
- Active model/KV config.
- Project registry.
- Frontier provider config.

Outputs:

- `reports/READINESS_<timestamp>.md`.
- Concise readiness summary.

Safety constraints:

- Does not inspect secrets/raw data/model weights.
- Must not auto-escalate if degraded.

Failure/degraded behavior:

- Show `DEGRADED`, `FAIL`, `UNAVAILABLE`, or `CHECK_FAILED`.
- Latest inspected report showed Ollama not reachable but GPU OK (`reports/READINESS_20260519_214523.md`).

Next safe action:

- If degraded, fix local runtime or continue only with workflows that do not require the failed dependency.

### 12.2 Agent Hygiene Check

Trigger:

- Start of day, before agent execution, after failed/stale agent runs.

Inputs:

- Git branches.
- `auto_runs/` folders.
- generated validation/hygiene reports.
- ignore policy.

Outputs:

- `reports/AGENT_HYGIENE_<timestamp>.md`.
- Branch/run summary.

Safety constraints:

- Audit and report only; do not delete branches/runs.

Failure/degraded behavior:

- Unresolved `CODEX_RUNNING` folders block further agent action until reviewed.

Next safe action:

- Resolve or mark stale runs reviewed using explicit command.

### 12.3 Learning Stronghold Review

Trigger:

- Operator wants to progress a learning stronghold.

Inputs:

- `state.json`, `architect_plan.md`, `local_checklist.md`, session artifacts, assessments, decisions.

Outputs:

- Recommended next learning action.
- Potential dry-run plan or artifact view.

Safety constraints:

- No project source mutation.
- Human must complete answers.
- Advancement requires explicit advance decision.

Failure/degraded behavior:

- If stale review decision does not match current session, suppress advancement and recommend review plan.

Next safe action:

- Generate session/review dry-run, import answers, assess, decide, or advance depending on evidence.

### 12.4 Review Tutor Generation

Trigger:

- Learning decision says review/repeat or TUI identifies stale/gap state.

Inputs:

- Latest assessment.
- Review session plan.
- Stronghold learning artifacts.

Outputs:

- `sessions/*_review_session_plan.md` from dry-run.
- `sessions/*_review_tutor_session.md` and answer template when model-backed command is run outside current TUI boundary.

Safety constraints:

- TUI can currently run only dry-run planner.
- Model-backed tutor generation remains disabled from current TUI.

Failure/degraded behavior:

- If Ollama unavailable, model-backed generation blocks.

Next safe action:

- Use dry-run planner first; run model-backed command manually only if policy permits.

### 12.5 Review Assessment

Trigger:

- Human review answers have been imported.

Inputs:

- Linked review tutor session.
- Human review answers.
- Prior assessment.

Outputs:

- `assessments/review_assessment_*.md`.
- `assessment.md`, `practice_log.md`, `state.json` updates.

Safety constraints:

- Requires explicit answer-to-tutor-session link to prevent evidence contamination.
- Local model only.

Failure/degraded behavior:

- Blocks if answers are missing or not linked to current tutor session.

Next safe action:

- Run `learning-decision --review`.

### 12.6 Decision Recording

Trigger:

- After assessment or review assessment.

Inputs:

- Latest assessment artifact.

Outputs:

- `reports/learning_decision_*.md` or `learning_review_decision_*.md`.
- `state.json` decision fields.

Safety constraints:

- Decision is deterministic/local, but it writes state.

Failure/degraded behavior:

- Blocks if assessment missing.

Next safe action:

- Advance, review, or repeat depending on decision.

### 12.7 Handoff Creation

Trigger:

- Need senior/cloud/browser reasoning after local context is compacted.

Inputs:

- Project/task/feature/stronghold context.
- Latest readiness/hygiene/worktree reports where relevant.
- Git status.

Outputs:

- Handoff folder with `prompt.md`, `context_pack.md`, `metadata.json`, `response.md`, `transcript.md`, `handoff_report.md`.

Safety constraints:

- No provider invocation.
- No browser automation.
- Do not include secrets/raw data/model files.
- Local readiness degradation must be recorded, not silently bypassed.

Failure/degraded behavior:

- Unsupported target or missing task/project blocks packet creation.

Next safe action:

- Review prompt manually; copy only if operator chooses the lane.

### 12.8 Handoff Import/Review

Trigger:

- Operator has pasted prompt into manual browser/provider lane and copied response back.

Inputs:

- Clipboard response.
- Existing handoff metadata.

Outputs:

- `response.md`, `transcript.md`, updated `metadata.json`, optional `review.md`.

Safety constraints:

- Refuse if metadata says provider invocation or browser automation already occurred.
- Deterministic review is structural, not a technical correctness guarantee.

Failure/degraded behavior:

- Empty clipboard or unsupported state blocks import.
- Unclassified review requires human attention.

Next safe action:

- Inspect response manually; separate apply gates remain required.

### 12.9 Feature Stronghold Validation

Trigger:

- After feature plan exists and before any supervised run.

Inputs:

- Feature `state.json`, contract, acceptance criteria, allowed files, validation plan, source task, Git state, latest readiness.

Outputs:

- `evidence/validation_*.md`.
- `state.json` updates to `VALIDATED_LOCAL` or `BLOCKED`.

Safety constraints:

- No provider, browser automation, agent, apply path, worktree creation, or project mutation.

Failure/degraded behavior:

- Missing files, state mismatch, readiness absence, provider/browser flags, or allowed-file problems block.

Next safe action:

- Feature report, local review, handoff, or resolve validation blockers.

### 12.10 Feature Run Dry-Run / Apply-Ready Handoff

Trigger:

- Feature is `VALIDATED_LOCAL` and operator wants supervised implementation readiness.

Inputs:

- Latest validation.
- Handoff review status.
- Readiness/hygiene.
- Allowed files.
- Worktree state if apply mode.

Outputs:

- Feature dry-run report or apply-ready handoff report.

Safety constraints:

- Dry-run does not mutate.
- Apply mode requires `--worktree` and `--from-dry-run`; current script reports `HANDOFF_ONLY` rather than auto-running arbitrary worktree agent.

Failure/degraded behavior:

- Blocks if feature state not `VALIDATED_LOCAL`, validation not pass, final report missing, worktree unready, or dry-run mismatched/stale.

Next safe action:

- Resolve gates; prepare reviewed worktree and handoff only when appropriate.

### 12.11 Graphify Context Generation

Trigger:

- Build planning, handoff, local context query, or project graph refresh.

Inputs:

- Project registry.
- Project Graphify output if present.
- Task details and allowed files.

Outputs:

- Compact Graphify context in run/handoff/build artifacts.

Safety constraints:

- Never graph whole `D:\`.
- Do not inspect raw data, secrets, credentials, model files, archives, dependency folders, or raw large files.

Failure/degraded behavior:

- If graph missing or query times out, record missing/timeout context rather than blocking unrelated local work.

Next safe action:

- Use available compact context; refresh project graph manually only when safe.

### 12.12 Local-to-Cloud Escalation

Trigger:

- Local context/model is insufficient or senior reasoning is needed.

Inputs:

- Redacted packet/handoff.
- Local context pack.
- Target provider/lane.

Outputs:

- Local response record or provider response artifact.

Safety constraints:

- Explicit target only.
- Redaction must pass.
- Browser lanes are manual.
- Cloud must not receive raw dumps by default.

Failure/degraded behavior:

- Redaction warning/block refuses escalation.
- Unsupported provider blocks.
- Gemini/browser remains manual where documented.

Next safe action:

- Fix packet, use manual lane, or continue locally.

## 13. Artifact Model

| Artifact | Purpose | Produced by | Consumed by | Freshness/staleness rule |
|---|---|---|---|---|
| Readiness report | Machine/runtime/provider health evidence. | `ws ready` | TUI, feature/handoff reports, operator | Latest should be checked before provider/model/apply work; stale if machine state changed. |
| Agent hygiene report | Branch/run hygiene evidence. | `ws agent-hygiene` | TUI, feature/handoff reports, operator | Latest before agent execution; unresolved running folders block. |
| Task file | Canonical task goal, criteria, allowed/denied files. | `ws task-new`, `ws task-split`, human | Build, agent, feature creation | Must be current at moment of execution. |
| Build run | Local planning artifacts and status. | `ws build` | `open-build`, feature/handoff workflows | Stale if task or project state changed. |
| Context pack | Reduced local context for model/handoff/build. | `ws_context_pack.sh`, `ws_handoff_new.sh`, `ws_make_packet.sh` | Local model, browser/cloud agent, human | Must reflect current task and local evidence. |
| Review packet/frontier packet | Safe external reasoning packet. | `ws packet`, `ws task-review`, handoff scripts | Manual cloud/browser lane | Must pass redaction before leaving workstation. |
| Handoff prompt | Exact prompt for manual target. | `ws handoff-new`, feature/stronghold handoff scripts | Operator/cloud/browser lane | Current until context changes or response imported. |
| Handoff metadata | Machine-readable state, target, purpose, timestamps, local readiness, evidence refs. | Handoff scripts | Handoff copy/import/review/status | Source of truth for handoff lifecycle. |
| Handoff response | Imported response from manual lane. | `ws handoff-import` | `ws handoff-review`, human | Must not be used for mutation without separate gates. |
| Handoff review | Deterministic local classification of imported response. | `ws handoff-review` | Feature reports, operator | Stale if response or feature context changes. |
| Feature contract | Feature objective, allowed files, constraints. | `ws feature-new` | Feature plan/validate/report/run | Source of truth for feature scope. |
| Feature validation evidence | Gate result for feature local validation. | `ws feature-validate` | Feature report/run | Stale if repo commit, allowed files, task, or contract changes. |
| Feature final report | Summary of feature state/evidence and next action. | `ws feature-report` | Operator, future run/handoff | Stale if validation/review changes. |
| Stronghold state | Machine-readable stronghold state and artifact pointers. | Stronghold/domain commands | TUI, stronghold commands, operator | Source of truth; must be updated atomically where possible. |
| Architect plan | Senior architect response promoted to plan. | `stronghold-plan-import` | Local checklist, reports, learning/research workflows | Stale if contract/goals/constraints change. |
| Local checklist | Tactical work breakdown generated locally. | `stronghold-local-checklist` | Learning/research/product/feature workflows | Stale if architect plan changes. |
| Learning session plan | Tactical plan for next learning session. | `learning-run --session --dry-run` | Tutor session generation, TUI | Stale if current task or review lane changes. |
| Tutor session | Exercises/explanations for human. | `learning-run --session --model` | Human answers, assessment | Must be linked to imported answers. |
| Answer template | Human exercise template. | Tutor session generation | Human, import command | Must match tutor session. |
| Human answers | Completed exercise evidence. | Human, imported via command | Assessment | Must be linked to current tutor session. |
| Assessment | Local model evaluation. | `learning-assess` | `learning-decision`, review planning | Stale if answers/tutor session change. |
| Learning decision | ADVANCE/REVIEW/REPEAT decision. | `learning-decision` | TUI, learning-advance, review planner | Stale if newer session/assessment exists. |
| Review plan/session/assessment/decision | Remediation loop evidence. | `learning-review-session`, `learning-run --review-session`, assess/decision | TUI, learning-advance | Must align with current session; stale decisions block advancement. |
| Research source registration | Source label/path status. | `research-add-source` | Research run/decision | Stale if source text changes. |
| Research notes/evidence matrix/hypothesis log | Research evidence synthesis. | `research-run`, `research-decision` | Research report/decision | Stale if sources change. |
| Worktree plan/review/sync/create reports | Isolation and Git state evidence. | `ws worktree-*` | Feature-run, agent run, operator | Stale after branch/worktree changes or age limits. |
| Cleanup plan/report | Workstation cleanup evidence. | `ws audit-workstation`, `ws cleanup-plan` | Cleanup status/apply | Must be reviewed before archive apply. |
| Graphify outputs | Project graph data and manifest. | Graphify | Context queries/build/handoff | Raw content should not be casually read; use summary/query output. |

## 14. Stronghold Model

A stronghold is a persistent, bounded workspace for one durable objective. It is a case file plus state machine, not just a folder of prompts.

Evidence:

- `reports/PHASE_5_GENERIC_STRONGHOLD_OPERATING_SYSTEM_DESIGN.md`
- `scripts/ws_stronghold_new.sh`
- `scripts/ws_stronghold_status.sh`
- `strongholds/learning/fine-tuning-small-open-source-models/state.json`
- `strongholds/product/local-ai-workstation-control-plane/state.json`
- `strongholds/research/agentic/state.json`
- `strongholds/trading-research/quant-research-from-academic-papers/state.json`

### Current Stronghold Types

| Type | Current evidence | Notes |
|---|---|---|
| `learning` | `strongholds/learning/fine-tuning-small-open-source-models/` | Most mature domain workflow. |
| `product` | `strongholds/product/local-ai-workstation-control-plane/` | Exists but current state inspected was `INTAKE_IN_PROGRESS`. |
| `research` | `strongholds/research/agentic/` | Research commands and state exist. |
| `trading-research` | `strongholds/trading-research/quant-research-from-academic-papers/` | Must remain research/paper/backtest only; no live trading. |
| `feature` | Feature-specific folders currently under `features/`, plus generic design. | Migration/unification open. |

### Inferred State Model

Common states supported by scripts and state files include:

- `CREATED`
- `INTAKE_IN_PROGRESS`
- `CONTRACT_READY`
- `ARCHITECT_REVIEW_READY`
- `ARCHITECT_PLAN_IMPORTED`
- `LOCAL_CHECKLIST_READY`
- `NEEDS_HUMAN_REVIEW`
- `BLOCKED`
- `COMPLETE`

Feature-specific states include:

- `LOCAL_PLAN_READY`
- `VALIDATED_LOCAL`
- `HUMAN_APPROVAL_REQUIRED`
- `BLOCKED`

Learning statuses include:

- `awaiting_human_answers`
- `awaiting_assessment`
- `assessed`
- `decision_recorded`
- `awaiting_review_answers`
- `awaiting_review_assessment`
- `review_assessed`
- `review_decision_recorded`
- `ready_for_next_session`

Open gap: the exact canonical state machine is not fully centralized. It is distributed across scripts and design reports.

### Stale Decisions And Next Safe Action

The workstation should treat "next safe action" as a deterministic recommendation based on:

- current state
- latest artifact timestamps
- linked artifact consistency
- blockers
- safety mode
- domain-specific rules

Learning evidence shows this is already implemented in part:

- `tui/app.py` computes learning next actions and stale review conditions.
- `scripts/ws_learning_assess.sh` blocks assessment if imported answers are not explicitly linked to the latest tutor session.
- `scripts/ws_learning_advance.sh` requires `ADVANCE_TO_NEXT_TASK`.

## 15. Handoff Model

Handoffs exist because the workstation needs high-reasoning cloud/browser support without turning cloud/browser tools into hidden or automatic control paths.

Evidence:

- `reports/PHASE_2_HANDOFF_AUTOMATION_DESIGN.md`
- `scripts/ws_handoff_new.sh`
- `scripts/ws_handoff_copy.sh`
- `scripts/ws_handoff_import.sh`
- `scripts/ws_handoff_review.sh`
- `scripts/ws_handoff_status.sh`
- `scripts/ws_make_packet.sh`
- `scripts/ws_redact_packet.sh`
- `scripts/ws_escalate.sh`

### Why Handoffs Exist

- Reduce repeated manual context assembly.
- Preserve prompt/response transcript.
- Record target, purpose, evidence, and local readiness.
- Keep browser submit manual.
- Keep provider execution separate from local packet preparation.
- Prevent cloud fallback when local checks fail.

### Local-First Context Reduction

Before handoff, local tools should:

- Read project metadata.
- Use Graphify/query summaries where available.
- Include relevant reports and task excerpts.
- Include Git status.
- Exclude secrets, raw datasets, credentials, `.env`, model files, archives, and private keys.

### Handoff Lifecycle

| State | Meaning | Evidence |
|---|---|---|
| `PROMPT_READY` | Local packet ready for review/copy. | `scripts/ws_handoff_new.sh` |
| `BROWSER_MANUAL_REQUIRED` | Browser lane requires manual paste/submit. | `scripts/ws_handoff_new.sh` |
| `COPIED_TO_CLIPBOARD` | Operator explicitly copied prompt. | `scripts/ws_handoff_copy.sh` |
| `RESPONSE_IMPORTED` | Clipboard response imported locally. | `scripts/ws_handoff_import.sh` |
| `REVIEW_ACCEPTED` | Deterministic review accepted structural response. | `scripts/ws_handoff_review.sh` |
| `REVIEW_NEEDS_ATTENTION` | Response had issues needing human attention. | `scripts/ws_handoff_review.sh` |
| `REVIEW_IMPORTED_UNCLASSIFIED` | Response imported but no deterministic rule matched. | `scripts/ws_handoff_review.sh` |

### What Must Be Captured

- Target and purpose.
- Project/task/feature/stronghold identity.
- Current Git status.
- Local readiness state.
- Evidence paths.
- Whether provider invocation occurred.
- Whether browser automation occurred.
- Prompt.
- Context pack.
- Imported response.
- Transcript.
- Review result.

### What Must Not Be Exposed

- Secrets, credentials, `.env`, private keys.
- Raw datasets or large raw data dumps.
- Model files or weights.
- Archives.
- Raw Graphify output unless deliberately summarized.
- Any context beyond the purpose-specific need.

## 16. Local AI / Model Runtime Requirements

### Ollama Role

Ollama is the local inference runtime. It is used for local reasoning, Graphify Q&A style workflows, local tutor/assessor workflows, feature local review, and build planning.

Evidence:

- `START_HERE.md`
- `LOCAL_AI_STACK_STATUS.md`
- `FINAL_RECOMMENDED_PROFILE.md`
- `registry/models.yaml`
- `scripts/ollama_call.py`
- `scripts/ws_feature_local_review.sh`
- `scripts/ws_learning_assess.sh`

### Local Model Role

Local models are "intern" or "local tutor/assessor" lanes. They can:

- Summarize.
- Decompose plans.
- Generate checklists.
- Produce tutor sessions.
- Assess human answers.
- Review feature plans locally.
- Reduce context before cloud escalation.

They must not:

- Authorize risky execution by themselves.
- Replace human approval.
- Widen scope.
- Access secrets/raw data.

### `hermes3:8b`

Repository config sets `hermes3:8b` as the daily active model:

- `registry/active_model.yaml`: `active_model: hermes3:8b`, `context_length: 8192`.
- `registry/models.yaml`: `hermes_default` maps to `hermes3:8b`, daily safe, 8192 context.
- `START_HERE.md` and `LOCAL_AI_STACK_STATUS.md` identify `hermes3:8b` as the default local driver.

Performance claims should be treated as historical/configuration evidence, not guaranteed current runtime facts. `LOCAL_AI_STACK_STATUS.md` and `FINAL_RECOMMENDED_PROFILE.md` report around 50 tokens/second and about 6.2GB VRAM, but the latest inspected readiness report showed Ollama unavailable at that time.

### OpenAI-Compatible Local Endpoint

The repo evidence inspected shows direct Ollama API calls to `localhost:11434`, not an OpenAI-compatible local endpoint as a stable product surface. Open question: whether any local OpenAI-compatible proxy exists outside the inspected safe files.

### WSL Access Considerations

Ollama runs on Windows; WSL scripts access it through localhost. Evidence:

- `START_HERE.md`
- `FINAL_RECOMMENDED_PROFILE.md`
- `scripts/check_health.ps1`
- `reports/READINESS_20260519_214523.md`

The health check must clearly distinguish:

- Windows Ollama unavailable.
- WSL cannot reach Ollama.
- Loaded model query failed.
- GPU status unavailable.

### GPU/VRAM Constraints

The system is configured for an RTX 4070 Laptop GPU with 8GB VRAM per `LOCAL_AI_STACK_STATUS.md` and `FINAL_RECOMMENDED_PROFILE.md`. Requirements:

- Default context should remain conservative.
- Do not blindly raise context beyond 8192 for daily use.
- Lab/big models require explicit allowance.
- Degraded behavior should be calm when GPU/Ollama unavailable.

## 17. Graphify / Context Layer Requirements

Graphify is the local context graph layer. It is used to avoid sending or prompting against raw project folders.

Evidence:

- `START_HERE.md`
- `global/GLOBAL_GRAPH_STATUS.md`
- `plans/GRAPHIFY_PROJECT_PLAN.md`
- `scripts/ws_context_pack.sh`
- `.graphifyignore`
- `registry/projects.yaml`

### Requirements

- Graphify should be used to reduce and rank local context before build planning, local model prompts, or cloud/browser handoffs.
- Each project should be graphed individually; never scan the raw `D:\` root.
- Graphify output should be queried or summarized; raw large graph files should not be displayed by default.
- Missing graph context should degrade to an explicit "No project graph available" or timeout message.
- Context packs must include task, allowed files, project metadata, compact Graphify context, and safety notice.
- Graphify refresh should be manual or clearly gated, not automatic on every trivial state transition.

### Ignored / Excluded

Graphify and context workflows must exclude:

- `.env`
- credentials and tokens
- raw datasets
- CSV/Parquet/SQLite/database files
- media/binary/archive files
- model weights
- dependency folders
- `.git`
- caches/logs/runs
- raw large data folders

Evidence: `.graphifyignore`, `.gitignore`, `scripts/ws_context_pack.sh`, `LOCAL_AI_STACK_STATUS.md`.

## 18. Success Metrics

These metrics are practical for a solo/local workstation.

| Metric | Target / Interpretation |
|---|---|
| Time to identify next safe action from TUI | Under 3 seconds after launch/snapshot for normal state. |
| Safety state visibility | `READ_ONLY` and `SAFE_DRY_RUN` visible on every TUI major screen. |
| Readiness check usefulness | `ws ready` produces clear pass/fail/degraded report and concise summary. |
| Handoff creation success | Handoff folders consistently include prompt, context, metadata, response placeholder, transcript, and report. |
| Handoff review traceability | Every imported response has an explicit state and review result or human-review blocker. |
| Unsafe/ambiguous prompt reduction | Fewer prompts manually copied without local context pack/redaction. |
| Stale decisions caught | Count stale learning/feature decisions blocked before advancement/apply. |
| Workflows completed without manual context reconstruction | Count learning/research/feature flows where TUI or reports point to current artifacts. |
| Agent runs with clean logs and reviewable artifacts | `final_report.md`, status, stdout/stderr/exit artifacts available for every run. |
| Generated report noise managed | Generated reports ignored or curated intentionally; no accidental commit noise. |
| Degraded-state clarity | Missing Ollama/WSL/GPU/provider state appears as clear `DEGRADED`/`UNAVAILABLE`, not misleading `READY`. |
| Secrets/raw-data protection | Zero casual inspections of `.env`, credentials, raw datasets, model weights, archives, or raw Graphify output. |

## 19. Risks and Failure Modes

| Risk | Impact | Mitigation | Detection signal |
|---|---|---|---|
| Agents modify files unexpectedly. | Project corruption or unreviewed changes. | Allowed files, branch/worktree isolation, max-files, max-minutes, final diff review. | Changed-file list outside allowlist; agent final report; Git diff. |
| Hidden unsafe writes under read-only label. | Operator trusts a path that writes state. | Define strict no-write vs report-write modes. | `git status --short`, generated reports, command registry. |
| Stale decisions advance learning/feature state. | Wrong next action or evidence contamination. | Timestamp/freshness checks, linked answers, stale warnings. | TUI stale warning; state timestamps out of order. |
| Handoff state unclear. | Cloud response reused without review. | Lifecycle states and metadata schema. | Missing `metadata.json`, `RESPONSE_IMPORTED` not reviewed, unclassified review. |
| Local/cloud context leakage. | Secrets or raw data leave workstation. | `.graphifyignore`, redaction, handoff prompt constraints, no raw dumps. | Redaction `WARNING`/`BLOCKED`; packet contains forbidden markers. |
| WSL/Ollama/GPU unavailable. | Model-backed workflows fail or hang. | Readiness checks, degraded UI, no auto cloud fallback. | `READINESS_*.md` failures; TUI `DEGRADED`. |
| Dashboard shows misleading `FAIL` or `READY`. | Operator makes wrong decision. | Parse status explicitly, show raw details on demand, tests/snapshots. | TUI snapshot mismatch with readiness report. |
| Overcomplicated UI. | Operator returns to ad hoc shell usage. | Signal-first IA, details on demand, backend commands hidden. | User bypasses TUI; long dashboard output wraps. |
| Context files become stale. | Build/handoff uses outdated evidence. | Freshness rules, state pointers, latest report checks. | Commit mismatch, timestamp mismatch, stale dry-run report. |
| Too much automation before product model is stable. | Unsafe or brittle workflows. | Roadmap gates, dry-run-first policy, no unattended night-run yet. | New command bypasses PRD/safety model. |
| Dirty worktree not respected. | User changes overwritten or mixed with agent work. | Preflight dirty checks; never revert unknown changes. | `git status --short` not clean before apply. |
| Clipboard handoff imports wrong content. | Bad response stored as evidence. | Metadata state checks, operator review, deterministic review. | Empty clipboard, unexpected response format, `REVIEW_IMPORTED_UNCLASSIFIED`. |
| Cleanup archives wrong files. | Loss of useful evidence. | Plan first, high-confidence only, protected prefixes, archive not delete. | Cleanup plan unsafe-to-touch list; skipped candidates. |
| Hardcoded path migration breaks workstation. | `ws`, venvs, Graphify, Ollama fail. | Staged migration with junctions and validation. | Path audit reports; failing `ws help`, `ws ready`. |

## 20. Roadmap

### Now

- Stabilize this PRD as a product source-of-truth.
- Verify real workstation checks without changing code: `ws ready`, `ws agent-hygiene`, `ws tui --snapshot` when safe for the operator.
- Align `WORKSTATION_MANUAL.md`, `START_HERE.md`, and `tui/README.md` with the implemented TUI and command safety contract.
- Capture the canonical `ws` command surface into a generated markdown or JSON registry.
- Add or update golden TUI snapshots if not present.
- Document the difference between "read-only with generated reports" and "strict no-write".
- Mark design-only reports versus implemented capabilities in docs.

### Next

- Formalize the stronghold state machine in one canonical document/schema.
- Formalize the handoff schema and lifecycle states.
- Improve artifact freshness/staleness detection across learning, feature, handoff, and worktree flows.
- Create operator playbooks for daily startup, learning session, feature validation, handoff, degraded Ollama, and agent recovery.
- Add more dashboard tests for 100/120/160 column widths, `NO_COLOR`, ASCII fallback, degraded reports, and stale artifacts.
- Add project-level onboarding docs that explain Windows/WSL/Ollama/Graphify assumptions.
- Create a command safety matrix consumed by TUI and docs.

### Later

- Richer local context graph integration with stronghold artifacts.
- Controlled cloud handoff UI with explicit copy/import/review gates.
- Multi-project cockpit for task queues and Graphify status.
- Durable run history with normalized status schema.
- Safer agent execution orchestration through reviewed worktrees.
- Better observability for generated reports, stale runs, and artifact provenance.
- Optional Textual implementation if dependency policy is approved.
- Night-run design remains later and must stay plan-first until safety model is boring and proven.

## 21. Open Questions

- What is the canonical list of `ws` commands, and can it be generated from one source?
- What is the exact stronghold state machine across generic, feature, learning, research, and trading-research domains?
- What is the canonical handoff schema, including required metadata fields and allowed state transitions?
- Which files are source of truth versus historical reports?
- What is the intended escalation path from local model to cloud model when local readiness is degraded?
- What is the minimum safe workflow before allowing apply/write operations from the TUI, if ever?
- Which TUI screens are final versus experimental?
- Does `READ_ONLY` mean no project mutation or no filesystem writes at all?
- Should `ws ready` and `ws agent-hygiene` have no-write/snapshot variants for strict read-only TUI use?
- Should Graphify outputs be indexed into strongholds, or should stronghold artifacts remain separate until a later graph layer?
- What is the supported local OpenAI-compatible endpoint story, if any?
- How should generated reports be retained, ignored, summarized, or pruned?
- Should feature strongholds be migrated under `strongholds/feature/`, or should `features/` remain separate?
- What command owns "next safe action" globally: TUI logic, stronghold decision scripts, or a future central planner?
- What exact provider/canary states are authoritative for Codex/Gemini/Claude availability?
- What is the canonical browser/cloud escalation audit trail for manually pasted ChatGPT/Gemini responses?
- What safety gate must pass before local model-backed TUI actions are enabled?
- How should the workstation handle existing dirty files when future agents are operating in the same repo?
- What is the rollback plan for failed worktree creation or sync beyond current partial rollback logic?
- Which logs/reports may contain sensitive prompt/context excerpts and should remain ignored?

## 22. Acceptance Criteria for the PRD Itself

This PRD is acceptable if:

- It reflects the actual project, not a fantasy version.
- It distinguishes implemented behavior from proposed behavior.
- It cites repository evidence by file path.
- It documents safety constraints clearly.
- It defines product scope and non-goals.
- It can guide future Codex/Antigravity/agent tasks.
- It gives future contributors enough context to avoid unsafe changes.
- It includes a practical roadmap.
- It captures open questions honestly.

Validation status for this PRD:

- Repository evidence was gathered from safe docs, scripts, reports, task files, TUI source, config files without secrets, and metadata listings.
- Existing code and docs were not modified.
- Large raw Graphify files, raw data, model files, `.env`, credentials, archives, databases, media, and binary files were not inspected.
- The PRD file itself is the only intended new artifact.
