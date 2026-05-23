# Quant Command Surface Integration Plan (Q32)

## 1. Purpose
This document plans the integration of the standalone Quant research CLIs into the unified Workstation Command Surface (`ws`). The goal is to provide a consistent, safety-validated, and discoverable interface for the entire Quant research lane.

## 2. Current State
- **Scripts:** ~15 standalone Python CLIs exist in `scripts/quant/` (e.g., `backtest_eligibility_cli.py`, `synthetic_execution_cli.py`).
- **Unified Command:** `ws quant` exists but only dispatches to a few basic data and contract checks.
- **Validation:** `check_local_safety.py` and `validate_ws_command_safety.py` are the gatekeepers.
- **Help:** `ws help` lists proposed commands, but many are not yet implemented in the `ws` dispatcher.

## 3. Proposed Command Groups
The standalone CLIs will be mapped to the following logical groups under `ws quant`:

| Group | Commands | Purpose | Underlying Script |
|---|---|---|---|
| `idea` | `new`, `list`, `status` | Research Idea Intake | `idea_cli.py` |
| `paper` | `new`, `list`, `status` | Paper Replication | `paper_replication_cli.py` |
| `candidate` | `draft`, `revise`, `status` | Strategy Candidates | `strategy_candidate_cli.py` |
| `readiness` | `check`, `recheck`, `remediation` | Research Readiness Gates | `strategy_candidate_cli.py`, `readiness_remediation_cli.py` |
| `plan` | `draft`, `rebuild`, `status` | Backtest Planning | `backtest_cli.py`, `backtest_eligibility_cli.py` |
| `data` | `requirements`, `mapping`, `import` | Dataset Preparation | `backtest_preparation_cli.py`, `backtest_execution_gate_cli.py` |
| `eligibility` | `check`, `report` | Master Eligibility Gate | `backtest_eligibility_cli.py` |
| `preflight` | `run` | Final Pre-Execution Gate | `backtest_execution_gate_cli.py` |
| `synthetic` | `run`, `review` | Plumbing Validation | `synthetic_execution_cli.py` |
| `approval` | `draft`, `validate`, `status` | Human-in-the-Loop Approval | `backtest_eligibility_cli.py`, `single_backtest_approval_input.py` |

## 4. Safety & Default Behavior
- **Default Policy:** Every command must default to `--dry-run` (or equivalent no-write mode).
- **Confirmation:** Every command that writes a report (`LOCAL_REPORT_WRITE`) or modifies a registry (`GUARDED_WRITE`) must require a `--confirm` or `--write` flag.
- **Categorization:**
    - `PURE_READ`: Listing and status commands.
    - `DRY_RUN_ONLY`: Previews and draft generators.
    - `LOCAL_REPORT_WRITE`: Most gate checks that output JSON/Markdown reports.
    - `GUARDED_WRITE`: Branching candidate revisions or concretizations.

## 5. Integration Plan
1. **Dispatcher Expansion:** Modify `scripts/ws` to include the new subcommands in the `quant` case.
2. **Registry Sync:** Update `registry/ws_command_safety.yaml` with the new command entries and their safety classes.
3. **Matrix Update:** Ensure `WS_COMMAND_SAFETY_MATRIX.md` reflects the final state.
4. **Validation:** Run `python scripts/validate_ws_command_safety.py` to ensure no drift.

## 6. Implementation Sequence (Future Phases)
1. **Slice 1:** Integrate `idea`, `paper`, and `candidate` groups (Inquiry/Intake).
2. **Slice 2:** Integrate `readiness`, `plan`, and `data` groups (Preparation).
3. **Slice 3:** Integrate `eligibility`, `preflight`, and `synthetic` groups (Validation).
4. **Slice 4:** Integrate `approval` and (eventually) the `runner` groups (Execution).

## 7. Slash Aliases (Proposed)
Slash commands will be thin aliases to the `ws` routes:
- `/quant idea new` -> `ws quant idea new`
- `/quant status` -> `ws quant status`
- `/quant backtest preflight` -> `ws quant backtest preflight`

## 8. Rollback Plan
- If integration causes a safety failure, the `scripts/ws` dispatcher for the `quant` subcommand can be reverted to its current "Phase 6+ preview" state.
- All standalone CLIs remain functional and independent, allowing for decoupled testing before integration.
