# Real Backtest Runner Design Review (Q30)

## 1. Purpose
This document reviews the proposed design for a future "Real Backtest Runner" in the Local AI Workstation. The goal is to define a safe, deterministic, and resource-bounded path for executing a single strategy candidate against a single local dataset, transitioning from the current synthetic-only simulation.

## 2. Current State
- **Synthetic Runner:** Validates plumbing using toy data and passive returns calculation.
- **Preflight Gate:** Correctly blocks execution if human approval or real data is missing.
- **Data Gate:** Limits manual imports to 1MB and performs basic header validation.
- **Real Backtesting:** **HARD-BLOCKED.** No engine for real historical data processing is currently implemented or authorized.

## 3. Why Real Backtesting Remains Blocked
1. **Safety:** Risk of accidental signal generation or misleading performance claims.
2. **Approval:** No formal mechanism exists to capture and verify explicit human-signed execution authorization.
3. **Engine Isolation:** The synthetic engine is not yet separated from the proposed real-data processing logic.
4. **Validation:** Multi-gate preflight requirements (Eligibility PASS) are not yet satisfied by current R3 candidates.

## 4. Proposed Runner Boundaries
The first implementation of the real backtest runner must adhere to the following "Single-Threaded Research" constraints:
- **Unit of Work:** Exactly **one** Strategy Candidate (`CAN`) and **one** Dataset Import (`IMP`) per run.
- **Forbidden:**
    - Batch backtesting (multiple strategies or symbols).
    - Parameter optimization / Grid search.
    - Strategy ranking or automatic selection.
    - Direct broker/paper/live trading integration.
- **Environment:** Local-only, CPU-only by default. No network access during execution.

## 5. Required Preconditions
Before the runner can execute, the following gates must return a **PASS** status for the specific candidate branch (e.g., R3):
1. **Backtest Eligibility:** `reports/quant/backtest_eligibility_reports/` shows `status: PASS`.
2. **Execution Preflight:** `reports/quant/backtest_execution_preflights/` shows `status: READY`.
3. **Human Approval:** A signed `reports/quant/backtest_approvals/` artifact must exist and be cryptographically or hash-linked to the Candidate, Plan, and Dataset.

## 6. Input/Output Specification
### Allowed Inputs
- **Strategy Logic:** Deterministic Python function/class implementing the strategy logic (already specified in `CAN`).
- **Data:** Validated local CSV import (`IMP`) meeting the `candidate_concrete_spec`.
- **Parameters:** Static values defined in the `BTP` (Backtest Plan).

### Forbidden Inputs
- Live market data streams.
- Unvalidated/Large (>1MB) CSV files.
- Credentials/API keys for brokers.

### Required Output Artifacts
- `backtest_metrics.json`: Standardized performance metrics (Sharpe, MDD, Returns).
- `equity_curve.png`: Static visual representation of capital over time.
- `trade_list.csv`: Detailed log of every simulated transaction for audit.
- `experiment_manifest.yaml`: Full provenance trace (Candidate ID, Data ID, Approval ID, Timestamp).

## 7. Resource Budget & Posture
- **RAM:** Peak usage must stay under 2GB.
- **CPU:** Default to single-core execution.
- **GPU:** **FORBIDDEN.** No CUDA or tensor-acceleration for backtesting logic.
- **VRAM:** 0GB.

## 8. Failure Modes
- **Resource Breach:** Immediate halt if RAM > 2GB or CSV > 1MB.
- **Logic Error:** Strategy runtime exceptions must be captured and reported without crashing the workstation.
- **Lookahead Detection:** Engine must raise alerts if strategy logic attempts to access future price data (index check).

## 9. Recommendation for First Implementation
The first "Real Runner" slice should be a **Deterministic Vectorized Engine** (using standard library or lightweight `math`/`statistics`) that implements the `BACKTEST_PROTOCOL.md` requirements. It should be implemented as a standalone script `scripts/quant/backtest_runner.py` that is only callable after all pre-execution gates are satisfied.
