# Agent Contract Validation

## Summary
- Result: PASS
- Timestamp: 20260516_151517
- Passed: 18
- Failed: 0
- Dry-run folder: D:\_ai_brain\auto_runs\20260516_151525_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run

## Checks
- PASS: scripts/ws exists
- PASS: scripts/ws dispatches build
- PASS: scripts/ws dispatches agent-status
- PASS: scripts/ws dispatches agent-canary
- PASS: scripts/ws dispatches agent-run
- PASS: scripts/ws dispatches agent-import
- PASS: scripts/ws dispatches agent-validate
- PASS: PowerShell agent scripts parse
- PASS: ws agent-status returns usable output
- PASS: ws agent-canary prints visible startup output
- PASS: ws agent-canary refreshes canary status
- PASS: ws agent-canary passes
- PASS: ws agent-run dry-run returns PLAN_ONLY
- PASS: dry-run writes status.txt and final_report.md
- PASS: dry-run does not leave CODEX_RUNNING
- PASS: apply path requires explicit Allowed Files
- PASS: canonical sample task has explicit Allowed Files
- PASS: auto_runs/ is ignored by Git

## Details
- agent-status output: Windows Agent Orchestrator Status | --------------------------------- | Selected launcher: codex.cmd (APPDATA): C:\Users\abi62\AppData\Roaming\npm\codex.cmd | Canary cache:  | AGENT_CANARY_PASSED | Canary timestamp:  | 2026-05-16T05:14:53.1900641Z | Unattended Codex execution enabled:  | yes
- agent-canary output: Agent canary starting: run=D:\_ai_brain\auto_runs\20260516_151519_agent_canary launcher=codex.cmd (APPDATA): C:\Users\abi62\AppData\Roaming\npm\codex.cmd timeout=3m | AGENT_CANARY_PASSED: D:\_ai_brain\auto_runs\20260516_151519_agent_canary | D:\_ai_brain\auto_runs\20260516_151519_agent_canary
- dry-run output: Agent run starting: run=D:\_ai_brain\auto_runs\20260516_151525_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run mode=codex launcher=codex.cmd (APPDATA): C:\Users\abi62\AppData\Roaming\npm\codex.cmd timeout=10m codex_attempt=False | PLAN_ONLY | D:\_ai_brain\auto_runs\20260516_151525_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run | D:\_ai_brain\auto_runs\20260516_151525_workstation_control_plane_001_stabilize_ws_command_documentation_agent_run\final_report.md
