# Local AI Workstation MVP Real Codex Acceptance Report

## Purpose

Record the first controlled real Codex CLI dispatch through the Local AI Workstation MVP spine and confirm whether the end-to-end guarded flow works without source mutation or git actions.

## Preconditions

- MVP Path-Length Hardening v0.1 completed.
- MVP Safety Baseline Repair v0.1 completed.
- Fresh compact-ID staging chain created.
- Disabled-adapter real-dispatch dry-run passed.
- Real-dispatch adapter remained disabled by default before deliberate enablement.
- Full workstation safety validation passed before the live run.

## Dispatch Plan Used

- Dispatch plan id: `dp_xp_execution_lan_2026-05-27t033256z_5a556b30bc79`
- Target adapter: `codex_cli`
- Packet id: `xp_execution_lane_2026-05-27t033239z_6a9333bf3dfa`
- Runtime session id: `rt_codex_stage_20260527_0332`
- Runtime assignment id: `asn_rt_codex_stage_2_2026-05-27t033233z_b8834a133fb6`

## Adapter Config State

Before enablement:

- `enabled=false`
- `executable=""`
- `base_args=[]`

During controlled run:

- `enabled=true`
- executable set to native `codex.exe`
- `base_args=["exec","--sandbox","read-only"]`

After cleanup:

- `enabled=false`
- `executable=""`
- `base_args=[]`

## Enabled Dry-Run Result

- Result: `PASS`
- `adapter_enabled=true`
- `argv_count=4`
- `writes=none`
- `executes=no`

## Real Dispatch Capture

- Return code: `0`
- Timed out: `false`
- Capture manifest:
  - `/mnt/d/_ai_brain/exchange_lane/outbox/pkt_xp_exec_b6f6cbad5658/dp_dp_xp_ex_d7c0c6440c24/capture_manifest.json`
- Outbox directory:
  - `/mnt/d/_ai_brain/exchange_lane/outbox/pkt_xp_exec_b6f6cbad5658/dp_dp_xp_ex_d7c0c6440c24`
- Stdout:
  - `/mnt/d/_ai_brain/exchange_lane/outbox/pkt_xp_exec_b6f6cbad5658/dp_dp_xp_ex_d7c0c6440c24/stdout.txt`
- Stderr:
  - `/mnt/d/_ai_brain/exchange_lane/outbox/pkt_xp_exec_b6f6cbad5658/dp_dp_xp_ex_d7c0c6440c24/stderr.txt`
- Command manifest:
  - `/mnt/d/_ai_brain/exchange_lane/outbox/pkt_xp_exec_b6f6cbad5658/dp_dp_xp_ex_d7c0c6440c24/command_manifest.json`

## Import Result

- Result id: `res_cap_xp_execution_7fb5699bbab2`
- Result packet:
  - `/mnt/d/_ai_brain/exchange_lane/result_packets/res_cap_xp_execution_7fb5699bbab2.json`
- Result status: `IMPORTED_PENDING_REVIEW`
- Trusted: `false`
- Lineage preserved:
  - `source_dispatch_plan_id`
  - `source_session_id`
  - `source_assignment_id`
  - `source_artifact_checksum`

Imported output remained untrusted and was not applied to any source repository.

## Validation Result

- Validation id: `val_res_cap_xp_execu_2026-05-27t051214z_83e7028d5aa1`
- Validation record:
  - `/mnt/d/_ai_brain/exchange_lane/result_validations/val_res_cap_xp_execu_2026-05-27t051214z_83e7028d5aa1.json`
- Validation status: `VALIDATION_BLOCKED`

## Loop Decision

- Loop decision id: `loop_val_res_cap_xp_e_2026-05-27t051226z_6568b4bafd91`
- Loop decision record:
  - `/mnt/d/_ai_brain/exchange_lane/loop_decisions/loop_val_res_cap_xp_e_2026-05-27t051226z_6568b4bafd91.json`
- Decision: `BLOCKED_NEEDS_OPERATOR`

## Blocker Analysis

Concrete blocker:

- Codex `exec` attempted `pwsh.exe`-based file inspection commands.
- Those commands were blocked by policy.
- The workstation captured that failure without mutating sources or bypassing policy.

Heuristic blockers recorded in metadata:

- `possible quota/rate-limit blocker`
- `possible permission prompt blocker`

Assessment:

- The concrete blocker is the important one for follow-up.
- The heuristic blockers should remain recorded, but they were not the directly observed stop condition in this run.

## Safety Confirmations

- No source files were modified by Codex.
- No branch was created.
- No commit, push, or merge occurred.
- No Gemini, Ollama, or Graphify execution occurred.
- No browser automation occurred.
- No manual copy/paste was used to move output through the spine.
- Adapter config was restored to disabled after the run.
- Post-run safety validation passed.

## MVP Acceptance Verdict

`PASS`

Reason:

The real Codex CLI call was dispatched through the Exchange/Runtime MVP spine, captured into artifacts, imported as untrusted, validated, and routed to a loop decision without source mutation, branch creation, commit, push, or merge.

The first live run ended in a controlled blocked state, which is acceptable for MVP acceptance because the system preserved safety boundaries and produced the required control-plane artifacts.

## Follow-Up Recommendation

Do not loosen policy yet.

Recommended next slice:

- `Codex read-only command compatibility review`

or

- `CLI prompt/tooling adjustment`

Goal of the follow-up:

- prevent `pwsh.exe`-based inspection attempts inside the guarded read-only dispatch path
- make Codex operate within the workstation’s approved read-only inspection model
- preserve the current no-mutation and no-git-action guarantees
