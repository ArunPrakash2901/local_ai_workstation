# ROADMAP: Quant Trading MVP

**Wave Structure for Sequential Delivery**

---

## Wave 0: The Blueprint (Current)
- **Objective:** Establish the governance, architecture, and safety contracts.
- **Deliverables:** PRD, Architecture, Workflow, Protocols, and YAML Templates.
- **Exit Criteria:** All 17 planning documents created and reviewed.

---

## Wave 1: The Foundation (Data & Tooling)
- **Objective:** Build the local data layer and backtesting skeleton.
- **Deliverables:**
  - `data_fetcher.py` (fetching US ETF OHLCV to Parquet).
  - `data_contracts.yaml` implementation.
  - DuckDB integration for fast feature calculation.
- **Dependencies:** Access to a reliable free or low-cost data API (e.g., Alpaca/YFinance).
- **Non-Goals:** Real-time data, strategy implementation.

---

## Wave 2: The First Candidate (Backtesting)
- **Objective:** Implement and backtest the first "Gold Standard" strategy.
- **Deliverables:**
  - `etf_trend_following_v1.py`
  - Event-driven backtesting engine (or Vectorized for v1).
  - First `experiment_manifest.yaml` generated.
- **Exit Criteria:** Reproducible backtest results for one strategy.

---

## Wave 3: The Stress Test (Validation)
- **Objective:** Implement the validation battery.
- **Deliverables:**
  - Monte Carlo simulation scripts.
  - Stress test suite (historical crash re-runs).
  - Multi-variate sensitivity analysis (parameter sensitivity).
- **Non-Goals:** Optimization/Curve-fitting (we focus on robustness).

---

## Wave 4: The Simulator (Paper Trading)
- **Objective:** Bridge the gap between backtesting and real-time data.
- **Deliverables:**
  - `paper_trading_engine.py` (simulated order book).
  - `risk_gateway.py` (enforcing `risk_policy.yaml`).
  - Daily "Order Proposal" workflow.
- **Dependencies:** Daily data ingestion.

---

## Wave 5: The Cockpit (Monitoring & Reconciliation)
- **Objective:** Provide visibility and auditability.
- **Deliverables:**
  - `reconciliation_report.py` (Simulated fills vs. Intended orders).
  - TUI integration (Strategy status and Risk dashboard).
  - Incident logs.

---

## Wave 6: Future Readiness (Review)
- **Objective:** Audit the system for potential live readiness.
- **Deliverables:**
  - Gap analysis report (what's missing for live capital).
  - Execution quality report (slippage/latency modeling).
- **Non-Goals:** Actual live trading. This wave is for *readiness review only*.
