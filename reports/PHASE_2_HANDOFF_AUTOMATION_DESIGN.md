# Phase 2: Handoff Automation Design

Date: 2026-05-17  
Status: Design only. No handoff commands are implemented in this phase.

## Executive Summary

Phase 2 should reduce operator copy-paste without changing the workstation's safety model. The first handoff layer should be local-only and read-only: collect local context, generate a bounded prompt, copy it to the clipboard, import a returned answer, store the transcript, and classify the next safe action. It should not drive Chrome, invoke a cloud model, mutate project repositories, or bypass any existing human approval gate.

The core design stance is:

1. local context first
2. explicit target selection
3. browser lanes remain manual
4. CLI execution is a later, separate capability
5. every handoff writes durable local artifacts before the next action is suggested

This extends the current control-plane style already used by `ws loop-plan`, `ws loop-start`, `ws apply-ready`, `ws agent-run`, and `ws worktree-review`: fresh local inspection first, explicit state labels, markdown reports, and no hidden state-changing step.

## 1. Manual Copy-Paste That Exists Today

The operator is currently acting as the transport and routing layer:

1. run local commands in WSL or PowerShell
2. decide which command output, report, diff, and task material matters
3. copy selected local context into ChatGPT or Gemini in Chrome
4. ask the browser model for a plan, review, or prompt
5. copy browser-generated prompts into Codex CLI or Gemini CLI
6. copy Codex or Gemini CLI output back into ChatGPT or Gemini in Chrome
7. manually preserve the useful parts of the exchange in local notes or reports
8. decide whether the answer means "plan locally", "ask for cloud review", "run a bounded apply gate", or "stop for human approval"

The highest-friction parts are not only the clipboard actions. They are the repeated judgment calls about what context to include, which prior artifact is latest, which model lane should see it, and how to preserve an auditable transcript afterward.

## 2. What Can Be Safely Automated

The first automation layer can safely handle deterministic, local-only work:

- resolve the project and task
- read the current branch and Git status
- gather the latest relevant local reports and build artifacts
- gather the latest saved command output when a report-backed artifact exists
- assemble Graphify-backed context and local summaries before any cloud/browser handoff
- render a target-specific `prompt.md`
- write a complete handoff folder and metadata record
- run local redaction/safety checks before any cloud-bound copy action
- copy a prepared prompt to the clipboard on explicit request
- import a response from the clipboard on explicit request
- append a durable `transcript.md`
- classify the imported response into the next safe operator state
- show latest handoff status and review summaries

These actions are deterministic, inspectable, reversible, and do not require trusting a remote provider or a changing browser UI.

## 3. What Must Stay Human-Gated

The following steps should remain explicit operator decisions:

- choosing the handoff target
- reviewing any prompt that will leave the workstation
- pasting and submitting prompts in ChatGPT or Gemini in Chrome
- deciding whether to trust or reuse a browser response
- choosing whether a later CLI provider run should occur
- any project-repository mutation
- any branch creation, worktree creation, sync, merge, or deletion
- any transition from a reviewed plan into `ws apply-ready` or `ws agent-run`
- any override after failed local validation, failed redaction, quota exhaustion, or provider unavailability

The handoff layer should recommend next actions, not execute them. A response that looks correct should still end in `HUMAN_APPROVAL_REQUIRED` whenever the next step would modify code, create isolation, or send additional cloud requests.

## 4. Why Browser Automation Should Be Experimental

Browser automation should not be the primary architecture because it is the least stable and least auditable lane:

- Chrome DOMs, selectors, login flows, and provider UI controls change without notice.
- Browser sessions may require MFA, CAPTCHA, rate-limit handling, or manual account selection.
- A hidden automated submit action is harder to review than a prompt file plus a deliberate paste.
- Terms, quotas, and provider-side safety behavior can change independently of workstation code.
- Browser control failures are noisy to debug and can turn a simple handoff into a fragile integration project.
- The browser lane is valuable precisely because it is a human reasoning gate, not an unattended transport path.

If browser automation is explored later, it should be a clearly labeled experiment around an already working clipboard workflow. It should never be required for the core handoff path.

## 5. Browser ChatGPT/Gemini Support Through Clipboard Handoff

For `chatgpt` and `gemini-browser`, the supported path should be:

1. `ws handoff-new ... --target chatgpt|gemini-browser --purpose <purpose>`
2. local artifact creation and redaction
3. `ws handoff-copy latest`
4. operator manually pastes into Chrome and submits
5. operator copies the browser answer
6. `ws handoff-import latest --from-clipboard`
7. `ws handoff-review latest`

The workstation should record that no browser automation occurred and set browser targets to `BROWSER_MANUAL_REQUIRED` after prompt creation. After `handoff-copy`, the clipboard step can move the handoff to `COPIED_TO_CLIPBOARD`, but the actual browser submit remains outside workstation control.

This still removes most repeated friction: prompt construction, context selection, transcript storage, and response classification become standardized, while the browser submit stays visible to the operator.

## 6. Later Direct CLI Support For Codex And Gemini

`codex-cli` and `gemini-cli` should share the same handoff artifact schema as browser targets from day one, even before direct execution is enabled. Later, `ws handoff-run` can use those stored prompts for CLI-only providers:

- `codex-cli`: later use an explicit read-only Codex invocation for review/reasoning work, separate from the existing bounded mutation lane in `ws agent-run`
- `gemini-cli`: later use the configured non-interactive terminal command for review/reasoning work
- `claude-code`: remain targetable for packaging, but currently classify as `CLI_PROVIDER_UNAVAILABLE`

The important separation is:

- `ws handoff-run` = later reasoning/review execution against a provider prompt
- `ws agent-run` = existing bounded Codex apply lane that can modify files under its own gates

`handoff-run` should only be available for CLI providers, require an explicit target, capture stdout/stderr/exit code into the handoff folder, and never be reused as a disguised browser submit path.

## 7. Local Ollama And Graphify Before Cloud/Browser Handoff

Before any cloud/browser handoff becomes usable, the system should build the strongest safe local context it can:

- Graphify query for repository structure and task-relevant code relationships
- deterministic project metadata from the registry
- the current task file and `Allowed Files` boundary
- the latest local plan or build report when present
- local workstation state such as readiness, loop, apply, and worktree reports
- an optional local-model compression pass when Ollama is healthy

The local lane should be used to reduce, rank, and annotate context before cloud exposure. This preserves privacy, lowers prompt size, and keeps the operator from uploading large raw dumps just to ask a narrow question.

If local readiness is degraded, the system must not silently compensate by making a cloud call. It should record the degraded local context state in `metadata.json` and use `VALIDATION_FAILED` or `HUMAN_APPROVAL_REQUIRED` until the operator decides how to proceed. The 2026-05-17 validation run makes this design requirement concrete: `ws ready` reported that Ollama was not reachable from Windows or WSL even though the frontier CLIs were detected.

## 8. Command Surface

### First implementation

```bash
ws handoff-new <project_key> <task_file> --target chatgpt|gemini-browser|codex-cli|gemini-cli|local --purpose <purpose>
ws handoff-copy latest
ws handoff-import latest --from-clipboard
ws handoff-status
ws handoff-review latest
```

Recommended behavior:

- `handoff-new`
  - local-only artifact creation
  - no provider invocation
  - validates target, task path, allowed files, project metadata, local safety, and context sources
  - writes prompt, context, metadata, transcript stub, and report
- `handoff-copy`
  - explicit clipboard write only
  - refuses unsafe or unreviewable prompts
  - never submits to a provider
- `handoff-import`
  - imports the operator-selected clipboard response into `response.md`
  - appends transcript history
  - runs response classification locally
- `handoff-status`
  - summarizes recent handoffs, targets, current states, blockers, and report paths
- `handoff-review`
  - prints the latest handoff summary, response classification, evidence used, and next safe action

### Later addition

```bash
ws handoff-run <handoff_id|latest>
```

`handoff-run` should be deferred and CLI-only. It should refuse `chatgpt` and `gemini-browser`, refuse unavailable providers, and remain separate from code-mutation commands.

## 9. Files And Folders

Each handoff should create a self-contained folder:

```text
D:\_ai_brain\handoffs\<timestamp>_<target>_<purpose>\
  prompt.md
  context_pack.md
  metadata.json
  response.md
  transcript.md
  handoff_report.md
```

Recommended artifact roles:

- `prompt.md`: exact prompt prepared for the chosen target
- `context_pack.md`: deterministic local evidence bundle and Graphify/local summary
- `metadata.json`: machine-readable state, target, project, task, timestamps, evidence paths, local health, redaction result, and current outcome state
- `response.md`: imported answer or later CLI response
- `transcript.md`: chronological prompt/response ledger with import timestamps and source lane
- `handoff_report.md`: human-readable summary, blockers, next safe action, and provenance

The `handoffs/` root should be ignored by Git in a later implementation because these folders may contain task excerpts, diffs, and provider responses. Curated phase reports remain tracked under `reports/`.

## 10. Supported Targets

| Target | Lane | Initial behavior |
| --- | --- | --- |
| `chatgpt` | browser/manual | package + clipboard only |
| `gemini-browser` | browser/manual | package + clipboard only |
| `codex-cli` | terminal CLI | package now, direct run later |
| `gemini-cli` | terminal CLI | package now, direct run later |
| `claude-code` | terminal CLI | packageable target, currently unavailable |
| `local` | local/operator | local-only package and review lane |

Current workstation facts already support this split:

- `codex` and `gemini` are detected
- `claude` is currently not found and disabled in `registry/frontier.yaml`
- browser ChatGPT/Gemini are already part of the operator workflow but should stay manual in Phase 2

## 11. Outcome States

The handoff folder should keep one current outcome state plus structured blocker fields. Required states:

| State | Meaning |
| --- | --- |
| `PROMPT_READY` | local packaging completed and prompt is ready for operator review |
| `COPIED_TO_CLIPBOARD` | prompt was explicitly copied by the operator |
| `RESPONSE_IMPORTED` | a returned answer was imported into the handoff folder |
| `LOCAL_PLAN_READY` | imported or local response is suitable for local-plan review only |
| `CLOUD_REVIEW_READY` | response is suitable for cloud/browser review but no mutation is approved |
| `CLI_PROVIDER_UNAVAILABLE` | requested CLI target is not currently usable |
| `BROWSER_MANUAL_REQUIRED` | browser target requires operator paste/submit |
| `QUOTA_BLOCKED` | provider or canary state prevents an intended cloud action |
| `HUMAN_APPROVAL_REQUIRED` | next step crosses an explicit approval boundary |
| `VALIDATION_FAILED` | local safety, redaction, task, or evidence validation failed |

Suggested transitions:

1. `handoff-new` -> `PROMPT_READY`
2. browser target after prompt creation -> `BROWSER_MANUAL_REQUIRED`
3. `handoff-copy` -> `COPIED_TO_CLIPBOARD`
4. `handoff-import` -> `RESPONSE_IMPORTED`
5. response classifier -> `LOCAL_PLAN_READY`, `CLOUD_REVIEW_READY`, or `HUMAN_APPROVAL_REQUIRED`
6. unavailable provider, quota issue, or failed checks override the happy path with `CLI_PROVIDER_UNAVAILABLE`, `QUOTA_BLOCKED`, or `VALIDATION_FAILED`

The state model should remain conservative. A good answer can recommend an apply step, but it should not itself produce an apply authorization.

## 12. Prompt Contract

Every handoff prompt should have a stable, inspectable schema:

1. target and purpose
2. project key and repository path
3. current branch and current commit
4. current `git status --short --branch`
5. current `git diff --stat`
6. task file path plus the task body or bounded task summary
7. explicit `Allowed Files`
8. latest relevant reports, with paths and timestamps
9. latest relevant saved command output, with provenance
10. compact Graphify context
11. local-model summary when available
12. hard constraints
13. requested output format

Recommended hard constraints:

- do not modify files unless explicitly asked in a later apply lane
- respect `Allowed Files`
- do not request secrets, raw datasets, credentials, `.env` files, model files, or archived artifacts
- state assumptions and blockers
- separate observations, recommendations, and exact next commands

Recommended requested output format:

```markdown
## Assessment
## Risks Or Blockers
## Recommended Next Action
## Evidence Used
## Suggested Command Or Prompt
```

### Selecting latest reports and command output

Selection should be deterministic and purpose-aware, not left to ad hoc operator memory:

- readiness purpose: latest `READINESS_*`, latest `AGENT_HYGIENE_*`
- local-loop review purpose: latest matching `LOOP_START_*`, latest matching `build_report.md`, `local_plan.md`
- apply-readiness purpose: latest matching `APPLY_READY_*`
- worktree purpose: latest matching `WORKTREE_REVIEW_*`, latest `WORKTREE_STATUS_*`
- general task review: latest task file, latest relevant build report, latest relevant Git snapshot

When no report-backed command output exists, the system should require an explicit file or imported clipboard block rather than scraping shell history. `metadata.json` should record why each artifact was included.

## 13. Avoiding Accidental Cloud Calls

The system should make unintended cloud usage hard:

- no default target that implies a cloud provider
- `handoff-new`, `handoff-copy`, `handoff-import`, `handoff-status`, and `handoff-review` are local-only
- browser targets never auto-submit
- CLI execution is deferred into a separate future `handoff-run`
- `handoff-run` later accepts CLI targets only and requires an explicit handoff id
- redaction must pass before any cloud-bound copy or run
- provider availability and quota/canary status must be recorded before a run is considered
- handoff metadata must say whether any provider invocation occurred
- no state transition should call a provider implicitly

This keeps "prepare", "copy", "import", "review", and "execute" as separate verbs instead of overloading one command with hidden behavior.

## 14. Integration With Existing `ws` Commands

### `ws ready`

- source of latest local-health evidence
- should gate cloud/browser readiness when local context is required
- should be referenced in `context_pack.md` and `handoff_report.md`
- current observed failure mode, such as unavailable Ollama, should become visible evidence rather than trigger automatic fallback

### `ws loop-start`

- its `local_plan.md`, `build_report.md`, and `LOOP_START_*` report should be first-class inputs for local-plan review handoffs
- it may later recommend `ws handoff-new ... --purpose review-local-plan`, but it should not auto-create or auto-send one

### `ws apply-ready`

- remains the final read-only gate before any bounded apply path
- handoff imports may recommend running it, but cannot replace it
- any response that proposes mutation should normally classify as `HUMAN_APPROVAL_REQUIRED`

### `ws agent-run`

- remains the bounded Codex apply lane
- should not be replaced by `handoff-run`
- its reports can be included in later review handoffs when an agent result needs external interpretation

### `ws worktree-review`

- its latest report should be included for worktree-related handoffs
- non-`READY` worktree classifications should prevent any handoff report from suggesting execution without explicit operator review

## 15. Recommended First Implementation

The first implementation should be exactly the small read-only/local-only slice already proposed:

```bash
ws handoff-new <project_key> <task_file> --target chatgpt|gemini-browser|codex-cli|gemini-cli|local --purpose <purpose>
ws handoff-copy latest
ws handoff-import latest --from-clipboard
ws handoff-status
```

Add `ws handoff-review` in the same phase if the classification logic is already present; otherwise keep it immediately adjacent as the next small command.

First implementation behavior should be limited to:

1. create the handoff folder and artifacts
2. assemble deterministic local context
3. run local safety/redaction checks
4. copy a prepared prompt only on explicit request
5. import a clipboard response only on explicit request
6. classify the next safe action without executing it

Do not implement yet in this phase:

- browser automation
- direct CLI provider execution
- worktree creation
- project-repo mutation
- automatic cloud fallback when local readiness fails
- night-run integration

## Recommended Phase Order After This Design

1. implement artifact schema and state machine
2. implement `handoff-new`
3. implement `handoff-copy`
4. implement `handoff-import`
5. implement `handoff-status`
6. add `handoff-review`
7. only after the clipboard workflow is stable, design `handoff-run` for CLI providers
8. keep browser automation as a separate experiment, not a dependency

## Validation Run

Requested validation performed on 2026-05-17:

- `ws ready`
  - failed local readiness because Ollama was not reachable on `localhost:11434`
  - WSL could not reach Ollama
  - Gemini and Codex were detected
  - Claude was not found
- `ws agent-hygiene`
  - current branch: `main`
  - agent branches: `12`
  - unresolved `CODEX_RUNNING` folders: `0`
  - reviewed `CODEX_RUNNING` folders: `4`
- `ws worktree-status`
  - active worktrees: `2`
  - stale-looking directories: `0`
- `git status --short`
  - existing user changes before this report: modified `WORKSTATION_MANUAL.md`, untracked `reports/R25_WORKTREE_SYNC_DRY_RUN_DESIGN.md`
- `git diff --stat`
  - existing user diff before this report: `WORKSTATION_MANUAL.md | 2 +-`

No handoff command was implemented, no project repository was modified, no worktree was created, no model provider was invoked, and no apply path was run.
