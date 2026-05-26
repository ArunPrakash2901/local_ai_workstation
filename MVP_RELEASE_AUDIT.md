# Local AI Workstation MVP Spine v0.1

- Release status: PASS_READY_TO_CHECKPOINT
- Date/time: 2026-05-26 18:55:13 +10:00
- Audit type: MVP release checkpoint verification

## Included Scope

- Discovery Lane
- Product Development Lane
- Product Review Artifact Layer
- Runtime Lane
- Exchange Lane
- Execution Lane

## Excluded / Post-MVP Scope

- Browser automation
- Fully unattended multi-agent loops
- Automatic branch creation
- Automatic commit/push/merge
- Product Design/Open Design execution
- Quant/Learning lanes
- Custom playground implementation
- Real Codex/Gemini run during tests

## MVP Spine Summary

Discovery/Product Dev artifacts
-> Execution plan/prepare
-> Runtime assignment/workload
-> Exchange packets/dispatch plans
-> fake dispatch/import
-> automated validation/loop decisions
-> guarded real-dispatch infrastructure

## Command Surfaces

- `ws discovery ...`: intake, ingest, approval, handoff, queue planning, audit/status surfaces for frozen Discovery artifacts.
- `ws product-dev ...`: product packet build, review HTML generation, review audit, and product development audit surfaces.
- `ws runtime ...`: session, adapter, assignment, blocker, workload, unassigned-task, status, and audit surfaces.
- `ws exchange ...`: packet lifecycle, approve-planning, dispatch-plan metadata, fake-dispatch, import-result, validate-result, loop decisions, guarded real-dispatch dry-run/confirm, result/status/list, and audit surfaces.
- `ws execution ...`: status, plan dry-run, prepare, run-status, handoff-preview dry-run, and audit surfaces.

## Safety Posture

- No arbitrary shell strings are part of the MVP dispatch path.
- No browser automation is included in the MVP release.
- No hidden provider calls are allowed in validation or tests.
- No CLI permission prompts are auto-approved.
- No branch creation, checkout, commit, push, or merge occurs by default.
- Codex/Gemini adapter command configs are disabled by default and require deliberate enablement.
- Imported results remain untrusted until validation.
- Loop decisions are bounded and produce metadata only in this release.
- Real-dispatch infrastructure captures output only; import-result, validate-result, and decide-loop remain separate steps.

## Validation Results

| Command | Result |
| --- | --- |
| `git status --short` | PASS - dirty worktree recorded |
| `python scripts\validate_ws_command_safety.py` | PASS |
| `python scripts\check_ws_manifest_drift.py` | PASS |
| `python scripts\test_tui_action_visibility.py` | PASS |
| `python scripts\check_local_safety.py` | PASS |
| `python scripts\test_product_review_artifacts.py` | PASS |
| `python product_development_lane\tools\audit_review_artifacts.py --root product_development_lane` | PASS |
| `python discovery_lane\tools\audit_discovery_lane.py --root discovery_lane` | PASS |
| `python product_development_lane\tools\audit_product_development_lane.py --root product_development_lane` | PASS |
| `python product_development_lane\tools\audit_review_artifacts.py --root product_development_lane` | PASS |
| `python runtime_lane\tools\audit_runtime_lane.py --root runtime_lane` | PASS |
| `python exchange_lane\tools\audit_exchange_lane.py --root exchange_lane` | PASS |
| `python execution_lane\tools\audit_execution_lane.py --root execution_lane` | PASS |
| `python scripts\test_discovery_lane.py` | PASS |
| `python scripts\test_product_development_lane.py` | PASS |
| `python scripts\test_product_review_artifacts.py` | PASS |
| `python scripts\test_runtime_lane.py` | PASS |
| `python scripts\test_exchange_lane.py` | PASS |
| `python scripts\test_execution_lane.py` | PASS |
| Final `python scripts\check_local_safety.py` before report | PASS |

Validation note: `scripts\test_product_review_artifacts.py` now uses the Windows system temp base `%TEMP%\_ai_brain_product_review_artifact_tests` and an isolated copied lane fixture. It no longer writes `.test_tmp` under `product_development_lane\review_artifacts`.

## Known Limitations

- `ws` wrapper invocation uses WSL style when `ws` is not globally on PATH in PowerShell: `wsl bash -lc "cd /mnt/d/_ai_brain && ./scripts/ws ..."`
- PowerShell bare `ws` is not on PATH unless configured later.
- Real Codex/Gemini dispatch requires deliberate adapter command config enablement.
- Real provider/CLI dispatch was not run during tests.
- The worktree remains dirty until checkpointed.
- Product Design/Open Design work remains outside this MVP release checkpoint.

## Dirty Worktree Summary

Modified files recorded by `git status --short`:

```text
 M OPEN_DESIGN_LOCAL_EVALUATION_REPORT.md
 M WORKSTATION_MANUAL.md
 M WS_COMMAND_SAFETY_MATRIX.md
 M exchange_lane/README.md
 M exchange_lane/contracts/result_packet_contract.md
 M exchange_lane/tools/audit_exchange_lane.py
 M exchange_lane/tools/exchange_command.py
 M exchange_lane/tools/exchange_packet.py
 M execution_lane/README.md
 M execution_lane/contracts/execution_run_contract.md
 M registry/ws_command_safety.yaml
 M scripts/check_local_safety.py
 M scripts/test_discovery_lane.py
 M scripts/test_exchange_lane.py
 M scripts/test_product_development_lane.py
 M scripts/test_product_review_artifacts.py
 M scripts/test_repo_context_lane.py
 M scripts/test_tui_action_visibility.py
 M scripts/validate_ws_command_safety.py
 M scripts/ws
 M slash_commands/operator_shortcuts.json
 M tui/action_dispatcher.py
 M tui/app.py
 M tui/next_action.py
```

Untracked files/directories recorded by `git status --short`:

```text
?? docs/prompt_kits/
?? exchange_lane/adapter_commands/
?? exchange_lane/contracts/loop_decision_contract.md
?? exchange_lane/contracts/real_dispatch_contract.md
?? exchange_lane/contracts/result_capture_contract.md
?? exchange_lane/contracts/result_validation_contract.md
?? exchange_lane/loop_decisions/
?? exchange_lane/loop_reports/
?? exchange_lane/outbox/
?? exchange_lane/packets/discovery__codex_cli__implementation_planning__WORKSTATION_MANUAL__20260525T061351z.json
?? exchange_lane/repair_packets/
?? exchange_lane/result_validations/
?? exchange_lane/tools/exchange_fake_dispatch.py
?? exchange_lane/tools/exchange_import_result.py
?? exchange_lane/tools/exchange_loop_decision.py
?? exchange_lane/tools/exchange_real_dispatch.py
?? exchange_lane/tools/exchange_validate_result.py
?? execution_lane/contracts/execution_handoff_preview_contract.md
?? execution_lane/contracts/worker_task_packet_contract.md
?? execution_lane/handoff_previews/
?? execution_lane/manifests/
?? execution_lane/run_reports/
?? execution_lane/tools/
?? execution_lane/worker_task_packets/
?? repro_duplicate_approval.py
?? scripts/test_execution_lane.py
```

## Release Decision

PASS_READY_TO_CHECKPOINT

## Recommended Next Steps

- Checkpoint/commit the MVP spine.
- Optionally run the first controlled real CLI smoke run after adapter command config is deliberately enabled.
- Add a daily progress report layer.
- Add branch/commit/push/merge gates later.
