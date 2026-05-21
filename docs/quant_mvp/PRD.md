# PRD: Quant Trading MVP (Local AI Workstation)

**Version:** 1.0.0  
**Status:** DRAFT  
**Owner:** Human Operator / Senior Quant Architect  
**Scope:** Research and Paper-Trading Factory

---

## 1. Executive Summary
The Quant Trading MVP is a specialized lane within the **D:\_ai_brain** workstation control plane, designed for rigorous, human-supervised quantitative research and paper trading. 

**Current Status:** Documentation and Contracts phase (Wave 0). No implementation code or data fetchers are active.
**Future State:** A strategy factory where AI assists in ideation, specification, and interpretation, while deterministic systems enforce data integrity, risk limits, and execution safety.

**Core Principle:** AI proposes, Human approves, Software executes.

---

## 2. Product Vision
To provide a local, transparent, and safe environment for developing institutional-grade quantitative strategies without the risk of autonomous live capital deployment.

---

## 3. Problem Statement
Quant trading is often seen as a "black box" where strategy logic, data assumptions, and risk controls are opaque. Existing retail tools often skip rigorous validation, leading to overfitting and look-ahead bias. Conversely, professional systems are too complex for a single-operator local workstation.

---

## 4. Target User
The **Workstation Operator**, acting as a Quant Researcher and Portfolio Manager, who requires AI assistance to accelerate the research-to-paper-trading pipeline while maintaining absolute control over risk.

---

## 5. MVP Goals
- **Strategy Factory:** A repeatable process for taking a hypothesis to a validated paper-trading strategy.
- **Split-Brain Architecture:** Strict separation between generative AI reasoning and deterministic backtesting/execution.
- **Data Lineage:** Traceable data from source to signal.
- **Safety Gates:** Hard human approval points for every promotion level.
- **Local Analytics:** Efficient use of local hardware (DuckDB/Parquet) for research.

---

## 6. Non-Goals
- **Autonomous Live Trading:** No capital will be deployed by the MVP.
- **High-Frequency Trading (HFT):** The system is not designed for low-latency execution.
- **Heavy Local Training:** No reliance on massive GPU-bound model training for the MVP.
- **Multi-Asset Complexity:** Initial scope is limited to US ETFs/Equities.

---

## 7. Supported Use Cases
1. **Hypothesis Testing:** Testing if a market anomaly (e.g., trend following) exists in a specific universe.
2. **Strategy Specification:** Using AI to draft precise Markdown/YAML specs for a strategy.
3. **Walk-Forward Validation:** Testing strategy robustness across different time periods.
4. **Paper Trading:** Simulating live execution in a risk-gated environment.

---

## 8. Core Workflow
1. **Research:** Human + AI ideation.
2. **Specification:** Draft strategy contract (YAML/MD).
3. **Ingestion:** Deterministic data fetch (Parquet/DuckDB).
4. **Backtest:** Execution of the strategy logic against historical data.
5. **Validation:** Robustness, stress, and sensitivity testing.
6. **Promotion:** Human approval to move to Paper Trading.
7. **Paper Run:** Real-time simulation with daily reconciliation.

---

## 9. Roles & Responsibilities

### AI Responsibilities (Generative)
- Ideation and hypothesis drafting.
- Converting human intuition into technical specs.
- Interpreting backtest results and proposing optimizations.
- Summarizing risk reports.
- Drafting post-trade review memos.

### Deterministic System Responsibilities (Safety-Critical)
- Data ingestion and validation (Data Contracts).
- Backtest engine execution.
- Risk limit enforcement (Risk Policy).
- Order validation and pricing collars.
- Reconciliation and audit logging.

### Human Responsibilities (Governance)
- Setting the overarching Investment Policy.
- Approving strategy specifications.
- Approving promotion to backtest/paper/live (future).
- Final review of all AI-generated interpretations.
- Manual kill-switch authority.

---

## 10. Success Metrics
- **Reproducibility:** 100% of backtests can be reproduced from the experiment manifest.
- **Safety:** Zero orders placed that violate the Risk Policy.
- **Efficiency:** AI reduces the time from "idea" to "validated spec" by >50%.
- **Transparency:** All strategy decisions are documented in a Git-traceable audit trail.

---

## 11. MVP Risks
- **Overfitting:** AI may propose overly complex strategies that look great in backtests but fail in paper trading. (Mitigation: Rigorous Backtest Protocol).
- **Data Quality:** Look-ahead or survivorship bias in local datasets. (Mitigation: Data Contracts).
- **Hardware Limits:** 16GB RAM may limit large-scale simulations. (Mitigation: Efficient DuckDB/Parquet usage).

---

## 12. Assumptions
- US ETF/Equity data is accessible (e.g., via Alpaca, Yahoo Finance, or local CSV/Parquet).
- The Workstation Operator understands basic quant concepts.
- Git is the primary versioning tool for all strategy artifacts.

---

## 13. Open Questions
- Should we prioritize a specific backtesting engine (e.g., Backtrader, VectorBT, or custom) for Wave 1?
- How frequently should the AI interpret paper-trading results (real-time vs. EOD)?
- What is the preferred method for local storage of tick-level vs. OHLCV data?
