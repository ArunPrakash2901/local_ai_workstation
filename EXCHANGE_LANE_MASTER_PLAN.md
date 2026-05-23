# Exchange / Orchestration Lane Master Plan

## Summary

The Exchange Lane exists so the operator is not the manual copy/paste bus between ChatGPT, Gemini, Codex, local Ollama models, browser platforms, and future MCP tools.

The lane should move structured handoff packets, prompts, outputs, reports, and artifacts through a deterministic workstation-controlled exchange bus. Models and CLIs can propose or execute bounded work, but the workstation stores the artifacts, validates outputs, enforces command safety, and presents operator decisions.

This is a planning document only. It does not implement commands, create queues, modify Product Lane behavior, call models, run agents, run browser automation, or change the command safety registry.

## Objective

The target workflow is automated structured exchange, not manual relay.

- Product Lane creates scoped source artifacts.
- Exchange Lane packages bounded tasks from those artifacts.
- Adapters read handoff packets and write results back.
- The safety layer gates any execution.
- The operator approves, rejects, or clarifies reports instead of copying text between platforms.

Temporary manual inspection is acceptable during early phases. Manual copy/paste is not the target workflow and should not become the permanent transport mechanism.

## Core Principle

Models propose or execute bounded tasks.

The workstation exchange bus stores artifacts.

The deterministic safety layer gates execution.

The human approves/rejects reports.

Local models, browser adapters, CLI adapters, and MCP tools are workers or transports. They are not safety authorities.

## Canonical Directory Structure

Use `exchange/` as the canonical Exchange Lane root.

Rationale:

- `exchange/` clearly describes the lane and can hold queue states.
- Per-handoff directories can live under queue state folders without a second top-level namespace.
- Future safety checks can assert that Exchange Lane writes are bounded to `exchange/<state>/<exchange_id>/`.

Planned structure:

```text
exchange/
  inbox/
  outbox/
  active/
  completed/
  failed/
  archive/
```

Each handoff packet directory should contain:

```text
exchange/<queue_state>/<exchange_id>/
  exchange.yaml
  prompt.md
  source_artifacts.md
  allowed_commands.md
  forbidden_actions.md
  expected_outputs.md
  raw_output.md
  parsed_result.json
  validation.md
  operator_report.md
  run_log.md
```

Queue states:

- `inbox/`: created packets awaiting dispatch or review.
- `outbox/`: packets prepared for an external adapter.
- `active/`: packets currently dispatched or reserved by an adapter.
- `completed/`: packets with validated results.
- `failed/`: packets that hit stop conditions or validation failure.
- `archive/`: old packets retained for audit.

## Handoff Packet Schema

`exchange.yaml` should be the canonical packet manifest. Markdown files hold human-readable prompt and context. JSON files hold parsed machine-readable results.

Required fields:

```yaml
exchange_id: "ex_20260522_001_portfolio_wireframe_review"
created_at: "2026-05-22T00:00:00Z"
source: "product_lane"
target: "codex_cli"
product_id: "portfolio-website-redesign"
task_type: "review"
task_summary: "Review deterministic PRD output for downstream wireframe readiness."
source_artifacts:
  - "products/portfolio-website-redesign/product.yaml"
  - "products/portfolio-website-redesign/scope_lock.md"
  - "products/portfolio-website-redesign/prd.md"
allowed_commands: []
forbidden_actions:
  - "run_agents"
  - "run_models"
  - "call_providers"
  - "browser_automation"
expected_outputs:
  - "operator_report.md"
output_schema: "exchange_result_v1"
stop_conditions:
  - "unclassified_command_requested"
  - "unexpected_file_write"
safety_mode: "REVIEW_ONLY"
approval_required: true
status: "CREATED"
result_paths: []
```

Field policy:

- `exchange_id`: deterministic unique identifier, safe for paths.
- `created_at`: UTC timestamp.
- `source`: producer, such as `product_lane`, `operator`, or `exchange_import`.
- `target`: adapter target, such as `codex_cli`, `gemini_cli`, `local_ollama`, `browser_chatgpt`, `browser_gemini`, or `future_mcp`.
- `product_id`: optional for non-product tasks, required for Product Lane handoffs.
- `task_type`: bounded category, such as `review`, `implementation`, `summarize`, `validate`, `critique`, or `repair_plan`.
- `task_summary`: one-line purpose.
- `source_artifacts`: relative paths the worker may read.
- `allowed_commands`: commands the worker may run, each of which must be covered by `registry/ws_command_safety.yaml` when execution is allowed.
- `forbidden_actions`: explicit prohibitions included in the prompt.
- `expected_outputs`: paths the worker or importer should produce inside the exchange packet.
- `output_schema`: parser contract for `parsed_result.json`.
- `stop_conditions`: conditions requiring adapter stop and operator report.
- `safety_mode`: exchange-level mode, not a new ws safety class.
- `approval_required`: whether the operator must approve before downstream use.
- `status`: lifecycle state.
- `result_paths`: generated result files.

## Worker And Adapter Model

Adapters consume `exchange.yaml` and `prompt.md`, then write output files back into the same exchange packet directory.

### `codex_cli`

Purpose:

- Bounded code implementation, code review, test repair, deterministic workstation tasks.

Input format:

- `exchange.yaml`
- `prompt.md`
- referenced source artifacts

Output format:

- `raw_output.md`
- `parsed_result.json`
- `operator_report.md`
- `run_log.md`

Safety restrictions:

- May run only commands listed in `allowed_commands`.
- Must stop on unclassified command requests.
- Must not exceed packet filesystem scope unless the packet explicitly authorizes repository edits.
- Must not run providers, agents, browser automation, or model calls unless the packet and safety manifest allow them.

First implementation phase:

- Phase 1 CLI adapter after Phase 0 schema and queue commands.

### `gemini_cli`

Purpose:

- Alternate planner/reviewer for structured critique, summarization, or comparison tasks.

Input format:

- Same packet structure as `codex_cli`.

Output format:

- Same result contract, with raw CLI transcript saved.

Safety restrictions:

- No unrestricted shell execution.
- No provider dispatch unless manifest-classified and operator-approved.
- Commands remain bounded by `allowed_commands`.

First implementation phase:

- Phase 1 CLI adapter, after `codex_cli` packet handling proves stable.

### `local_ollama`

Purpose:

- Local summaries, small template filling, smoke-test interpretation, bounded review of artifacts, and lightweight implementation suggestions.

Input format:

- Prompt assembled from `prompt.md` and allowed source artifact excerpts.

Output format:

- `raw_output.md`
- `parsed_result.json`
- `validation.md`

Safety restrictions:

- Local model cannot decide safety policy.
- Local model output is advisory until parsed and validated.
- No shell execution from local model output.
- No access to secrets, credentials, large data, model weights, or raw Graphify outputs.

First implementation phase:

- Phase 1 or Phase 2, after result validation exists.

### `browser_chatgpt`

Purpose:

- Later transport adapter for sending packet prompts to ChatGPT browser UI and capturing responses when API or CLI transport is unavailable or not desired.

Input format:

- `prompt.md` only, plus narrowly allowed attachments if explicitly supported later.

Output format:

- captured browser response in `raw_output.md`
- parsed result and validation files generated locally after capture

Safety restrictions:

- Browser adapter cannot run shell commands.
- Browser adapter cannot browse arbitrary sites.
- Browser adapter cannot visit secrets pages.
- Browser output is never executed directly.

First implementation phase:

- Phase 3, after CLI adapters and result validation.

### `browser_gemini`

Purpose:

- Later transport adapter for Gemini browser UI.

Input format:

- Same browser transport packet model as `browser_chatgpt`.

Output format:

- captured response and validated parsed result.

Safety restrictions:

- Same browser restrictions: allowed domains only, no secrets pages, no shell execution, no arbitrary browsing.

First implementation phase:

- Phase 3.

### `future_mcp`

Purpose:

- Expose safe workstation resources and bounded tools to compatible clients.

Input format:

- MCP resources and tools derived from exchange packets and safe workstation metadata.

Output format:

- MCP tool results imported into exchange result files.

Safety restrictions:

- Not raw shell.
- Not unrestricted filesystem.
- No broad secrets access.
- Tools must map to manifest-classified workstation behavior.

First implementation phase:

- Phase 4, after file-backed exchange behavior is mature.

## No Manual Copy/Paste Design

Manual copy/paste is not the intended Exchange Lane workflow.

Automated adapters should:

- read prompts from `exchange/<state>/<exchange_id>/prompt.md`;
- read constraints from `exchange.yaml`, `allowed_commands.md`, and `forbidden_actions.md`;
- write raw outputs back to `raw_output.md`;
- write parsed results to `parsed_result.json`;
- write operator-facing summaries to `operator_report.md`.

Browser automation can later paste prompts and extract model responses, but only as a transport adapter. It must not become an execution authority.

Temporary manual inspection is allowed for audit, debugging, and operator decisions.

## Safety Model

Exchange Lane does not bypass `registry/ws_command_safety.yaml`.

Rules:

- Any command execution must be manifest-classified.
- Unknown commands are blocked.
- Browser automation cannot run shell commands.
- CLI adapters cannot exceed `allowed_commands`.
- Local models cannot decide safety policy.
- Outputs must be parsed and validated before downstream use.
- No unrestricted filesystem MCP.
- No unrestricted shell MCP.
- Adapters must record commands run, files read, files changed, and stop reasons.
- Exchange packet writes must stay inside the packet directory unless a guarded execution packet explicitly authorizes repository edits.
- Product artifacts remain governed by Product Lane state and artifact rules.

Safety checks should fail closed. Missing schema fields, unknown targets, unsupported modes, malformed outputs, and unclassified commands should produce `failed/` packets and operator reports.

## Exchange Execution Modes

These are exchange-level modes, not new ws command safety classes.

- `DRY_RUN_ONLY`: Produce a preview or dispatch plan. No worker execution and no artifact mutation outside the packet.
- `REVIEW_ONLY`: Worker may read allowed artifacts and return critique or recommendations. No repository writes.
- `GUARDED_EXECUTION`: Worker may perform bounded implementation or repair using manifest-known commands and explicit operator authorization.
- `BROWSER_TRANSPORT`: Browser adapter may move prompt text to an approved model UI and capture response text only.
- `LOCAL_MODEL_WORKER`: Local model may process bounded prompts and return structured output. It cannot execute commands or set policy.

## MVP Phases

### Phase 0: Exchange Schema And File-Backed Queue

Scope:

- `EXCHANGE_PACKET_SPEC.md` or embedded packet schema.
- `ws exchange-new --dry-run`
- `ws exchange-new --confirm`
- `ws exchange-list`
- `ws exchange-status`

Properties:

- No dispatch.
- No shell execution.
- No model calls.
- No browser automation.
- Writes bounded to `exchange/<exchange_id>/` or queue-state equivalent.
- Allowed command references must be manifest-known.

### Phase 1: CLI Adapters

Scope:

- `codex_cli` dispatch.
- `gemini_cli` dispatch.
- `local_ollama` dispatch.
- result capture.

Properties:

- No browser automation.
- Adapter execution is packet-scoped.
- Command execution remains bounded by `allowed_commands`.
- Local model outputs are captured but not trusted until validation.

### Phase 2: Result Import And Validation

Scope:

- `ws exchange-import-result`
- output schema validation
- `operator_report.md` generation
- result status transitions

Properties:

- Malformed output fails closed.
- Operator reports identify files changed, tests run, blocked reasons, and required decisions.
- Downstream Product Lane commands consume only validated results.

### Phase 3: Browser Transport Adapters

Scope:

- `browser_chatgpt`
- `browser_gemini`
- Playwright or BrowserMCP exploration
- strict allowed domains
- response capture

Properties:

- Browser transport cannot execute shell commands.
- Browser transport cannot browse arbitrary pages.
- Browser responses are raw output until parsed and validated.
- No secrets pages or credential inspection.

### Phase 4: MCP Layer

Scope:

- safe workstation resources
- safe bounded workstation tools
- adapter consumption of MCP resources

Properties:

- Not MCP-first.
- No raw shell.
- No unrestricted filesystem.
- Gemini CLI/MCP is likely the first practical integration.
- ChatGPT browser or local MCP remains later and conditional.
- Browser automation remains a separate transport adapter.

## Browser Automation Policy

Future browser adapters must follow these rules:

- Use allowed domains only.
- Use a dedicated browser profile.
- Do not open secrets, credential pages, password managers, `.env` views, token pages, or admin consoles.
- Do not browse arbitrary websites.
- Paste only generated `prompt.md` content.
- Capture only the model response needed for the exchange packet.
- Save captured response to `raw_output.md`.
- Parse response into `parsed_result.json`.
- Never execute returned commands directly.
- Never treat model output as approval.
- The safety layer decides any next action.

Browser adapters are transport, not orchestration policy.

## Output Format Policy

Execution workers should return structured results with:

```json
{
  "task_id": "ex_20260522_001_portfolio_wireframe_review",
  "inputs_read": [],
  "commands_run": [],
  "files_changed": [],
  "tests_run": [],
  "result": "PASS",
  "blocked_reason": "",
  "needs_human_decision": false
}
```

Policy:

- `commands_run` must be exact enough for audit.
- `files_changed` must distinguish exchange packet writes from repository or product artifact writes.
- `tests_run` must include command and result.
- `blocked_reason` must be populated when status is not successful.
- `needs_human_decision` must be true for ambiguous, unsafe, or policy-changing outcomes.
- No open-ended recommendations unless the packet requests them.

## Relationship To Product Lane

Product Lane remains the source of truth for product artifacts and maturity.

- Product Lane creates intake, answers, scope locks, PRDs, reviews, approvals, wireframes, and future technical plans.
- Exchange Lane dispatches bounded packets derived from those artifacts.
- Exchange Lane should not invent requirements after scope lock.
- Exchange results may propose changes, but Product Lane revision workflows must record and gate those changes.
- Stale artifact policy remains Product Lane policy.

For example, a Product Lane PRD review can generate an Exchange Lane critique packet, but validated critique output cannot directly mutate `scope_lock.md`, `prd.md`, or `product.yaml`. It must enter the existing scope-change or future PRD-revision workflow.

## Relationship To Local Models

Local models are workers, not safety authorities.

Appropriate future local model tasks:

- summarize bounded artifacts;
- fill deterministic templates;
- classify small reports;
- smoke-test prompt formats;
- suggest small fixes for operator review;
- compare expected and actual outputs.

Inappropriate local model authority:

- deciding command safety;
- approving PRDs;
- bypassing scope locks;
- running shell commands;
- choosing unrestricted files to inspect;
- accessing secrets or raw sensitive data.

Cloud models can remain planners and reviewers for complex reasoning, but their outputs still pass through the same exchange validation and operator decision gates.

## MCP Strategy

Do not start MCP-first.

Build the file-backed exchange bus first because it gives:

- deterministic audit trails;
- simple validation;
- bounded write paths;
- clear operator reports;
- adapter independence.

Later, expose safe resources and tools via MCP:

- packet status resources;
- read-only product summaries;
- manifest-known command metadata;
- validated artifact lookup;
- bounded exchange result import tools.

Do not expose:

- raw shell;
- unrestricted filesystem;
- secrets;
- credential stores;
- unbounded browser control;
- direct Product Lane mutation without existing command gates.

Gemini CLI/MCP is likely the first practical MCP integration. ChatGPT browser or local MCP should remain later and conditional. Browser automation remains a separate transport adapter because browser UI automation has different risks than MCP resource/tool access.

## Risks And Mitigations

Prompt injection:

- Treat external and model output as untrusted.
- Parse and validate results before use.
- Keep allowed commands explicit.

Browser UI brittleness:

- Isolate browser adapters to Phase 3.
- Use dedicated profiles and strict allowed domains.
- Save raw captures for audit.

Accidental command execution:

- Block unknown commands.
- Require manifest coverage.
- Require explicit operator approval for guarded execution.

Malformed output:

- Validate against `output_schema`.
- Mark packet failed when parsing fails.
- Generate an operator report instead of guessing.

Stale artifacts:

- Include source artifact hashes where practical.
- Check source artifact freshness before import.
- Require Product Lane staleness rules before downstream use.

Secret leakage:

- Do not include secrets in source artifacts.
- Block secret-like paths.
- Do not inspect `.env`, credential, token, key, or secret-like files.
- Use dedicated browser profiles without secrets pages.

Adapter runaway loops:

- One packet dispatch per explicit command.
- Record status transitions.
- Limit retries.
- Require operator approval for redispatch.

Local model overreach:

- Local model output is advisory.
- No shell execution from local model output.
- No safety policy decisions by models.

MCP over-permissioning:

- Expose narrow resources and tools only.
- Avoid raw shell and unrestricted filesystem.
- Keep Product Lane mutations behind existing command gates.

## Phase 0 Implementation Proposal

First implementation slice:

- Create `EXCHANGE_PACKET_SPEC.md` or embed the initial schema in an Exchange Lane helper module.
- Implement `ws exchange-new --dry-run`.
- Implement `ws exchange-new --confirm`.
- Implement `ws exchange-list`.
- Implement `ws exchange-status`.

Phase 0 command behavior:

- `exchange-new --dry-run` validates packet inputs and prints the packet preview.
- `exchange-new --confirm` writes a packet directory under `exchange/inbox/<exchange_id>/`.
- `exchange-list` lists packet IDs, targets, modes, statuses, and timestamps.
- `exchange-status` prints a deterministic packet summary.

Phase 0 constraints:

- No dispatch.
- No worker execution.
- No shell execution from packet content.
- No model/provider/agent calls.
- No browser automation.
- All writes bounded to `exchange/inbox/<exchange_id>/`.
- Unknown targets rejected.
- Unknown exchange modes rejected.
- `allowed_commands` must be empty or manifest-known.

Initial safety classification proposal using existing ws safety classes:

- `ws exchange-new --dry-run`: `DRY_RUN_ONLY`
- `ws exchange-new --confirm`: `LOCAL_REPORT_WRITE`
- `ws exchange-list`: `PURE_READ`
- `ws exchange-status`: `PURE_READ`

These are proposals only and should be confirmed against implementation source before adding manifest entries.

## Tests Needed Later

Planned tests:

- packet schema validation;
- `exchange_id` path safety;
- unknown target rejected;
- unknown exchange mode rejected;
- forbidden actions recorded;
- allowed commands must be manifest-known;
- dry-run writes no files;
- confirm writes only inside `exchange/inbox/<exchange_id>/`;
- list/status are pure read;
- no shell execution in Phase 0;
- no model/provider/agent calls;
- no browser automation;
- malformed packet fails closed;
- check_local_safety integration.

## Recommended First Implementation Prompt

Implement Exchange Lane Phase 0 Slice 1: deterministic `ws exchange-new --dry-run`.

The command should validate a proposed exchange packet, render a no-write packet preview, reject unknown targets and unsupported safety modes, require manifest-known `allowed_commands`, and call no agents, models, providers, browser automation, or shell execution from packet content.

Do not implement dispatch, import, browser transport, MCP, or write mode in the first slice.

