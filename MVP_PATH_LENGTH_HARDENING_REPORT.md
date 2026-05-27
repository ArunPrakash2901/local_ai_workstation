# MVP Path-Length Hardening Report v0.1

Date: 2026-05-27
Repo: `D:\_ai_brain`

## Preflight

- `git status --short`: PASS (dirty worktree detected; no cleanup performed)
- `python scripts\validate_ws_command_safety.py`: PASS
- `python scripts\check_ws_manifest_drift.py`: PASS
- `python scripts\test_tui_action_visibility.py`: PASS
- `python scripts\check_local_safety.py`: PASS at preflight start

## Files Changed

- Added `scripts/workstation_ids.py`
- Added `docs/workstation/ID_AND_PATH_POLICY.md`
- Updated compact-ID/path handling in:
  - `runtime_lane/tools/runtime_session.py`
  - `exchange_lane/tools/exchange_packet.py`
  - `exchange_lane/tools/exchange_dispatch_plan.py`
  - `exchange_lane/tools/exchange_fake_dispatch.py`
  - `exchange_lane/tools/exchange_real_dispatch.py`
  - `exchange_lane/tools/exchange_import_result.py`
  - `exchange_lane/tools/exchange_validate_result.py`
  - `exchange_lane/tools/exchange_loop_decision.py`
  - `execution_lane/tools/execution_command.py`
- Updated tests:
  - `scripts/test_runtime_lane.py`
  - `scripts/test_exchange_lane.py`
  - `scripts/test_execution_lane.py`
- Updated docs:
  - `exchange_lane/README.md`
  - `runtime_lane/README.md`
  - `execution_lane/README.md`

## ID and Path Policy Summary

- Compact IDs are now used for new metadata artifacts.
- Filename stems are bounded for Windows safety (target <= 64, hard <= 96).
- Path length checks are applied at write points:
  - warn above 180 characters
  - fail/shorten above 220 characters
- Traceability remains in artifact metadata (JSON/Markdown fields), not verbose filenames.

## Smoke Flow (Normal Names, No Manual Short-Name Workaround)

Flow executed in isolated temp roots:

1. `execution prepare --confirm`
2. `runtime register`
3. `runtime update-status READY`
4. `runtime assign`
5. `exchange packet create`
6. `exchange mark-ready`
7. `exchange approve-planning`
8. `exchange dispatch-plan`
9. `exchange fake-dispatch --confirm`
10. `exchange import-result --confirm`
11. `exchange validate-result`
12. `exchange decide-loop`
13. `exchange real-dispatch --dry-run` (guard only)

Artifact IDs created:

- `run_id`: `run_positive_path_ex_2026-05-27t022912z_0ce1a0c4e031`
- `task_packet_id`: `task_run_positive_pat_2026-05-27t022912z_facaa00a7ac2`
- `assignment_id`: `asn_smoke-session-pa_2026-05-27t023031z_1280d0263de3`
- `packet_id`: `xp_execution_lane_2026-05-27t023041z_a5f340c5ab57`
- `dispatch_plan_id`: `dp_xp_execution_lan_2026-05-27t023106z_08b2ab179a18`
- `result_id`: `res_cap_xp_execution_4641d69d631d`
- `validation_id`: `val_res_cap_xp_execu_2026-05-27t023133z_eafae192abe5`
- `loop_decision_id`: `loop_val_res_cap_xp_e_2026-05-27t023141z_db7c2ca71feb`

Loop outcome:

- Validation status: `VALIDATION_PASSED`
- Recommended loop decision: `COMPLETED_PENDING_DAILY_REVIEW`
- Real dispatch confirm not run; adapter config remained disabled.

## Path-Length Outcome

- Longest generated artifact path observed: `158` characters
- Longest path:
  - `C:\Users\abi62\AppData\Local\Temp\_ai_brain_path_hardening_smoke\execution_lane\worker_task_packets\task_run_positive_pat_2026-05-27t022912z_facaa00a7ac2.json`
- Paths > 180 warning threshold: none in smoke run
- Paths > 220 fail threshold: none

## Validation Results

PASS:

- `python scripts\test_runtime_lane.py`
- `python scripts\test_exchange_lane.py`
- `python scripts\test_execution_lane.py`
- `python runtime_lane\tools\audit_runtime_lane.py --root runtime_lane`
- `python exchange_lane\tools\audit_exchange_lane.py --root exchange_lane`
- `python execution_lane\tools\audit_execution_lane.py --root execution_lane`
- `python scripts\validate_ws_command_safety.py`
- `python scripts\check_ws_manifest_drift.py`
- `python scripts\test_tui_action_visibility.py`
- `wsl bash -lc "cd /mnt/d/_ai_brain && ./scripts/ws exchange audit"`
- `wsl bash -lc "cd /mnt/d/_ai_brain && ./scripts/ws execution audit"`

FAIL (unrelated existing environment issue):

- `python scripts\check_local_safety.py`
  - fails in `scripts/test_repo_context_lane.py` with `PermissionError [WinError 5]` creating temp test roots under:
    - `C:\Users\abi62\AppData\Local\Temp\_ai_brain_repo_context_tests\...`
- `wsl bash -lc "cd /mnt/d/_ai_brain && ./scripts/ws runtime audit"`
  - fails on pre-existing runtime assignment artifacts that reference Windows-only source paths from older smoke fixtures.

## Safety Confirmations

- No real Codex execution
- No real Gemini execution
- No Ollama execution
- No provider/API calls
- No browser automation
- No interactive terminal start
- No real-dispatch `--confirm`
- No branch creation
- No commit/push/merge

## Conclusion

- Path-length hardening for Runtime/Exchange/Execution artifact naming: **PASS**
- Manual `s1` / `p.json` workaround for new flows: **No longer required**
- Global `check_local_safety.py`: **currently blocked by unrelated repo-context temp permission issue**
