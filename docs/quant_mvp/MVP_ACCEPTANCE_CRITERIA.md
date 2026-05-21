# MVP ACCEPTANCE CRITERIA: Quant Trading

The Quant Trading MVP is considered "Accepted" when it meets the following criteria across functional, safety, and documentation domains.

---

## 1. Functional Acceptance
- [ ] **Data Pipeline:** Can fetch US ETF OHLCV data and store it locally in Parquet/DuckDB without manual intervention.
- [ ] **Backtesting:** Can execute a strategy script against historical data and produce a reproducible metrics report.
- [ ] **Validation Battery:** Can run walk-forward and stress tests automatically on a candidate strategy.
- [ ] **Paper Engine:** Can simulate orders and fills based on daily rebalancing logic.
- [ ] **Reconciliation:** Can produce a report showing the delta between intended and simulated positions.

---

## 2. Safety Acceptance
- [ ] **No Live Code:** Repository contains zero code for live broker execution or capital deployment.
- [ ] **Risk Gateway:** A deterministic module blocks any order proposal that violates `risk_policy.yaml`.
- [ ] **Human Gates:** Promotion of a strategy requires a manual update to a Git-tracked file (`strategy_inventory.yaml`).
- [ ] **Mode Lock:** The system hard-fails if an attempt is made to bypass the `PAPER` or `RESEARCH` mode constraints.
- [ ] **Live-Trading Forbidden:** Absolute policy that no live capital is ever deployed by this MVP.

---

## 3. Documentation Acceptance
- [ ] **Complete Doc Pack:** All 17 requested planning and contract documents are present in the repository.
- [ ] **Agent Policy:** The `AGENT_OPERATING_POLICY.md` is active and followed by all AI-assisted workflows.
- [ ] **Runbooks:** A human can follow the `PAPER_TRADING_RUNBOOK.md` to manage a session without external help.

---

## 4. Agent-Behavior Acceptance
- [ ] **Evidence Grounding:** AI agents cite `experiments/quant/` manifest files when discussing strategy performance.
- [ ] **Uncertainty Reporting:** AI agents use the **[UNKNOWN]** tag for any missing data or ambiguous backtest results.
- [ ] **No Policy Modification:** AI agents never propose changes to `risk_policy.yaml` without a high-signal human directive.

---

## 5. Reproducibility Acceptance
- [ ] **Manifest Integrity:** A third party (or another agent) can reconstruct a backtest result using only the `experiment_manifest.yaml` and the referenced code/data versions.

---

## 6. Final Disclaimer
**LIVE TRADING IS NOT ACCEPTED IN MVP.** Any functionality resembling autonomous live capital deployment is grounds for rejection of the MVP state. All `ws quant` commands in this phase are proposed specifications, not implemented tools.
