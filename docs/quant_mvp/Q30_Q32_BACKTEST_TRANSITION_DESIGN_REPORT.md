# Q30-Q32 Backtest Transition Design Report

## 1. Files Inspected
- `docs/quant_mvp/Q4_Q29_QUANT_LANE_CONSOLIDATION.md`
- `docs/workstation/SAFETY_REPAIR_REPORT.md`
- `docs/workstation/OPERATOR_COMMANDS.md`
- `docs/workstation/RESOURCE_BUDGET.md`
- `docs/workstation/LOW_RESOURCE_MODE.md`
- `docs/workstation/SLASH_COMMAND_STRATEGY.md`
- `docs/quant_mvp/Q21_Q23_BACKTEST_ELIGIBILITY_REPORT.md`
- `docs/quant_mvp/Q24_Q26_BACKTEST_EXECUTION_GATE_REPORT.md`
- `docs/quant_mvp/Q27_Q29_SYNTHETIC_EXECUTION_REPORT.md`
- `docs/quant_mvp/BACKTEST_PROTOCOL.md`
- `registry/ws_command_safety.yaml`
- `scripts/ws`

## 2. Files Created
- `docs/quant_mvp/REAL_BACKTEST_RUNNER_DESIGN_REVIEW.md`
- `docs/quant_mvp/HUMAN_APPROVAL_UX_SPEC.md`
- `docs/quant_mvp/QUANT_COMMAND_SURFACE_INTEGRATION_PLAN.md`
- `docs/quant_mvp/REAL_BACKTEST_RUNNER_RISK_REGISTER.md`
- `docs/quant_mvp/Q30_Q32_BACKTEST_TRANSITION_DESIGN_REPORT.md`
- `contracts/quant/future_real_backtest_runner_contract.yaml`
- `contracts/quant/future_human_approval_ux_contract.yaml`
- `contracts/quant/future_quant_command_surface_contract.yaml`

## 3. Design Decisions
- **Isolation:** The real backtest runner must be a standalone, deterministic Python module, strictly decoupled from live trading or external APIs.
- **Single-Run Policy:** The runner will only support one candidate and one dataset per execution to prevent unbounded optimization and resource sprawl.
- **Human-in-the-Loop:** A mandatory approval workflow with explicit operator signing and artifact hashing is required before any non-synthetic execution.
- **Resource Guard:** Execution is gated by 1MB CSV and 2GB RAM limits, enforced at the preflight stage.
- **Command Integration:** Standalone Quant CLIs will be grouped logically under `ws quant` subcommands, maintaining `scripts/ws` as the primary router.

## 4. What Remains Blocked
- **Real Backtesting:** Implementation and execution of non-synthetic logic are forbidden in this milestone.
- **Data Ingest:** Downloading or importing real-world market data remains unauthorized.
- **Approval:** No execution authorization has been granted for the R3 VWAP candidate.
- **Trading:** All broker, paper, and live trading logic remains strictly absent.

## 5. Recommended First Future Implementation Slice
The next phase should focus on the **Command Surface Integration Dry-Run**. This involves wrapping the existing standalone Quant CLIs into `ws` without changing their logic, and validating the updated safety registry.

## 6. Resource Review
- **RAM:** No change to baseline.
- **VRAM/GPU:** Not used.
- **CPU:** Standard Python execution for documentation and validation.

## 7. Safety Review
- **Validation:** All safety manifests and AST checks passed.
- **Posture:** 100% adherence to "No Signal, No Advice, No Execution" mandates.

## 8. Validation Results
- `python scripts/validate_ws_command_safety.py` -> **PASS**
- `python scripts/check_local_safety.py` -> **PASS**

## 9. Recommended Next Bundle
**Quant Q33-Q35: Command Surface Integration Dry-Run + Registry Plan Validation + No-Op ws Wrapper Prototype**
This bundle will focus on the technical plumbing required to expose the research lane through the unified `ws` command without unlocking real execution.
