# MVP Real Gemini Acceptance Report

## Purpose

Record the first controlled real Gemini CLI dispatch through the Local AI Workstation Exchange/Runtime MVP spine and confirm Gemini parity with the previously accepted Codex path.

## Preconditions

- MVP Path-Length Hardening v0.1 completed.
- MVP Safety Baseline Repair v0.1 completed.
- Exchange/Runtime guarded real-dispatch infrastructure already validated.
- Codex parity acceptance already passed and was checkpointed separately.
- Gemini adapter remained disabled by default before this run.
- Gemini disabled-adapter dry-run refusal had already passed.
- Compact-ID runtime/exchange staging chain existed before the accepted run.

## Dispatch Plans

### Initial Gemini plan

- Dispatch plan: `dp_xp_execution_lan_2026-05-27t052633z_6acb3b8b7b2e`
- This was used for the first guarded confirm attempt.
- That attempt was not accepted because the Gemini bundle path was passed in WSL form while Windows Node executed the command, causing Node to resolve the script path incorrectly as `D:\mnt\c\...`.
- Result: capture was created, return code was non-zero, and the run was treated as a configuration-path failure rather than the acceptance run.

### Accepted Gemini plan

- Replacement dispatch plan: `dp_xp_execution_lan_2026-05-27t054225z_b49279055602`
- This plan was created after correcting the direct bundle path handling for the local Gemini CLI invocation.
- The accepted real Gemini run used this replacement plan.

## Adapter Config Before / During / After

### Before

- `enabled=false`
- `executable=""`
- `base_args=[]`

### During accepted run

- `enabled=true`
- `executable=/mnt/c/Program Files/nodejs/node.exe`
- `base_args=[`
- `"C:\\Users\\abi62\\AppData\\Roaming\\npm\\node_modules\\@google\\gemini-cli\\bundle\\gemini.js",`
- `"--approval-mode",`
- `"plan",`
- `"--output-format",`
- `"json",`
- `"--skip-trust"`
- `]`

### After

- Restored to `enabled=false`
- Restored to `executable=""`
- Restored to `base_args=[]`

## Enabled Dry-Run Result

- Status: PASS
- `adapter_enabled=true`
- `argv_count=7`
- `writes=none`
- `executes=no`

The dry-run confirmed that the guarded dispatch command built argv successfully without launching Gemini and without writing capture artifacts.

## Real Dispatch Capture Paths

Accepted real Gemini run:

- Dispatch plan: `dp_xp_execution_lan_2026-05-27t054225z_b49279055602`
- Return code: `0`
- Timeout: `false`
- Capture manifest:
  `/mnt/d/_ai_brain/exchange_lane/outbox/pkt_xp_exec_478fc33222fd/dp_dp_xp_ex_59487406010c/capture_manifest.json`
- Outbox:
  `/mnt/d/_ai_brain/exchange_lane/outbox/pkt_xp_exec_478fc33222fd/dp_dp_xp_ex_59487406010c`
- Stdout:
  `/mnt/d/_ai_brain/exchange_lane/outbox/pkt_xp_exec_478fc33222fd/dp_dp_xp_ex_59487406010c/stdout.txt`
- Stderr:
  `/mnt/d/_ai_brain/exchange_lane/outbox/pkt_xp_exec_478fc33222fd/dp_dp_xp_ex_59487406010c/stderr.txt`
- Command manifest:
  `/mnt/d/_ai_brain/exchange_lane/outbox/pkt_xp_exec_478fc33222fd/dp_dp_xp_ex_59487406010c/command_manifest.json`

## Import Result and Untrusted Status

- Result ID: `res_cap_xp_execution_001e65bb2412`
- Result status: `IMPORTED_PENDING_REVIEW`
- Trusted: `false`

Lineage preserved in the imported result packet:

- `source_dispatch_plan_id`
- `source_session_id`
- `source_assignment_id`
- `source_artifact_checksum`

The imported output remained untrusted and was not applied to source files.

## Validation Result

- Validation ID: `val_res_cap_xp_execu_2026-05-27t054408z_fb6c55373a9a`
- Validation status: `VALIDATION_BLOCKED`

The validation record confirmed that the captured artifacts were complete and that no forbidden git or source-mutation flags were present, while still surfacing run blockers for operator review.

## Loop Decision

- Loop decision ID: `loop_val_res_cap_xp_e_2026-05-27t054415z_7274d2127269`
- Decision: `BLOCKED_NEEDS_OPERATOR`

The resulting loop decision remained metadata-only and did not trigger repair dispatch, source mutation, or any git action.

## Blocker Analysis

- The accepted Gemini run itself returned `0`.
- Validation still produced `VALIDATION_BLOCKED`, so the workstation correctly escalated the result into a metadata-only operator gate.
- Stderr recorded a workspace restriction issue for `D:\_ai_brain\discovery_lane\worker_prompts` being outside Gemini's allowed workspace for that run.
- No source mutation occurred.
- No branch, commit, push, or merge occurred.

## Safety Confirmations

- No app/source files were modified by Gemini.
- No branch/commit/push/merge occurred.
- No Codex/Ollama/Graphify/browser automation ran during this parity acceptance task.
- No manual copy/paste was used.
- Gemini adapter config was restored to its disabled baseline after the run.
- Post-run safety validation passed.

## Gemini Parity Verdict

PASS.

A real Gemini CLI call was dispatched through Exchange/Runtime, captured into workstation artifacts, imported as untrusted, validated, and routed to a metadata-only loop decision without source mutation or git actions.

## Follow-Up Recommendation

- Do not loosen policy yet.
- A later slice can review Gemini workspace configuration and prompt-boundary handling so read-only Gemini runs can access the intended context without broadening safety scope.

## Timestamp

- Report generated: `2026-05-27T15:49:09+10:00`
