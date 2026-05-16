# R3 Workstation Contract Tests

## Files Changed
- `scripts/ws_agent_validate.sh`
- `scripts/ws`
- `WORKSTATION_MANUAL.md`
- `reports/R3_WORKSTATION_CONTRACT_TESTS.md`

## Checks Added
- `scripts/ws` exists and dispatches the expected agent workflow commands.
- Windows agent PowerShell scripts parse successfully.
- `ws agent-status` returns usable status output.
- `ws agent-canary` prints visible output, refreshes canary status, and passes.
- `ws agent-run --dry-run` returns `PLAN_ONLY`.
- Dry-run creates `status.txt` and `final_report.md`.
- Dry-run does not leave `status.txt` as `CODEX_RUNNING`.
- Apply-capable agent runs require explicit `Allowed Files`.
- The canonical sample task has explicit `Allowed Files`.
- `auto_runs/` is ignored by Git.

## Commands Run
- `ws agent-validate`
- `git status --short`
- `git diff --stat`

Latest validation result:
- `reports/AGENT_CONTRACT_VALIDATION_20260516_151517.md`
- Result: `PASS`
- Checks: `18 passed, 0 failed`

## Pass/Fail Behavior
- `ws agent-validate` writes a timestamped markdown report under `reports/`.
- It prints `PASS` and exits `0` only when every contract check succeeds.
- It prints `FAIL` and exits non-zero when any contract check fails.
- It does not launch a real apply; it uses canary and dry-run paths only.

## Remaining Gaps
- The validator proves the current control-plane contract, not project-specific tests.
- It does not validate long-running unattended apply behavior.
- A later real bounded apply is still required whenever you want evidence from the actual apply path.

## Recommended Next Step
Use the new validation command as the gate before any future independent loop or night-loop design work:

```bash
ws agent-validate
```
