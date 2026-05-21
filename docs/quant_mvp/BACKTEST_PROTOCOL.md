# BACKTEST PROTOCOL: Quant Trading MVP

This protocol defines the mandatory steps and quality checks for any backtest to be considered valid for promotion.

---

## 1. Required Inputs
- **Strategy Spec:** A finalized `strategy_spec.md`.
- **Clean Data:** Data validated against `data_contracts.yaml`.
- **Code Version:** A specific Git commit hash of the strategy logic.
- **Risk Policy:** The version of `risk_policy.yaml` active during the run.

---

## 2. Data Quality & Bias Controls
- **Look-Ahead Bias:** Ensure no information from the "future" is used (e.g., using the day's close price to execute at that same day's open).
- **Survivorship Bias:** Use a universe definition that accounts for delisted assets (where possible) or acknowledge the bias in the manifest.
- **Data Freshness:** Backtests must be run on the most recent available data extract to ensure relevance.

---

## 3. Modeling Assumptions
- **Transaction Costs:** Default to $0.005 per share or 5bps (whichever is higher) unless justified otherwise.
- **Slippage:** Default to 1-2bps for liquid ETFs; higher for less liquid instruments.
- **Impact:** Assume no market impact for MVP-sized positions.

---

## 4. Validation Protocol (The "Battery")
A strategy must pass these four tests to move beyond the `backtested` status:

### A. Walk-Forward Validation
- Divide data into `In-Sample` (Train) and `Out-of-Sample` (Test).
- Optimize (if necessary) only on In-Sample.
- Verify performance holds on Out-of-Sample.

### B. Robustness / Sensitivity Analysis
- Vary parameters by +/- 10-20%.
- Performance should degrade gracefully, not collapse (no "knife-edge" parameters).

### C. Stress Testing
- Re-run the strategy specifically during known crash periods (e.g., 2008 GFC, 2020 COVID, 2022 Bear Market).
- Document behavior during liquidity crises.

### D. Multicollinearity & Factor Check
- (Inspired by GSP failure) Ensure signals are not highly collinear.
- Check if returns are simply explained by a broad market beta (SPY).

---

## 5. Required Metrics
Every manifest must report:
- **Total Return / CAGR**
- **Max Drawdown (MDD) & Duration**
- **Sharpe & Sortino Ratio**
- **Win Rate & Profit Factor**
- **Alpha & Beta to Benchmark**
- **Turnover & Total Cost**

---

## 6. Rejection Criteria
A strategy is automatically rejected if:
- It uses future information (Hallucination/Look-ahead).
- It exceeds the `risk_policy.yaml` limits.
- It has a "Knife-Edge" parameter dependency.
- It requires > 5x leverage to meet return targets.

---

## 7. Artifacts
Every backtest must produce:
- `backtest_metrics.json`
- `equity_curve.png`
- `trade_list.csv`
- `experiment_manifest.yaml`
