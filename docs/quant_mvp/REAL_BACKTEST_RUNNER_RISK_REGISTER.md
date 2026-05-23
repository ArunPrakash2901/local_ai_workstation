# Real Backtest Runner Risk Register (Q30-Q32)

## 1. Purpose
This document identifies and tracks the technical, operational, and safety risks associated with transitioning the Quant Research Lane from synthetic simulations to real backtest execution.

## 2. Risk Register

| Risk ID | Description | Severity | Mitigation | Required Gate | Status |
|---|---|---|---|---|---|
| **R-01** | **Accidental Execution:** Strategy logic executes before explicit human approval. | CRITICAL | Hard-link execution script to approval file existence and hash. | Preflight | OPEN |
| **R-02** | **Lookahead Bias:** Strategy logic accesses future price data, invalidating research results. | HIGH | Implement index-guards in the data provider/iterator. | Backtest Engine | OPEN |
| **R-03** | **Data Leakage:** In-sample data contaminates out-of-sample testing during manual partitioning. | HIGH | Use automated partitioning scripts with strict seed/date guards. | Plan Draft | OPEN |
| **R-04** | **Resource Exhaustion:** Large dataset load or complex logic triggers OOM or system freeze. | MEDIUM | Enforce 1MB CSV limit and stream data row-by-row; set peak RAM guard to 2GB. | Preflight | OPEN |
| **R-05** | **Overfitting:** Human operator manually optimizes parameters until results "look good." | MEDIUM | Enforce "Single Candidate / Single Plan" rule; forbid grid-search CLIs. | Eligibility | OPEN |
| **R-06** | **Stale Data:** Research is conducted on outdated snapshots without the operator knowing. | LOW | Implement "Freshness Check" in preflight against `last_modified` metadata. | Preflight | OPEN |
| **R-07** | **Malformed CSV:** Improper column headers or data types lead to silent logic errors. | LOW | Strict schema validation during dataset import gate. | Dataset Import | OPEN |
| **R-08** | **Performance Overinterpretation:** Operator assumes historical performance implies future profit. | MEDIUM | Mandatory safety labels and "Research-Only" watermarks on all artifacts. | Result Review | OPEN |
| **R-09** | **Artifact Lineage Loss:** Losing the link between specific code version, data version, and results. | LOW | Content-addressable hashing for all manifests and strategy files. | Persistence | OPEN |
| **R-10** | **Approval Ambiguity:** Human approval form is filled out but intent is vague or unauthorized. | MEDIUM | Regex guards on intent field; explicit HITL signature text required. | Approval | OPEN |
| **R-11** | **Command Surface Drift:** `ws` commands and the safety registry become desynchronized. | LOW | Automated registry validation in `check_local_safety.py`. | Workstation CI | CLOSED |

## 3. Risk Posture Summary
The transition to real backtesting introduces significant safety and integrity risks. The current architecture mitigates these primarily through **Isolation** (local-only, no-trading) and **Sequential Gates** (technical validation before human approval).

No risk is considered "Resolved" until the first real backtest runner is implemented and verified against these mitigations in a future milestone.
