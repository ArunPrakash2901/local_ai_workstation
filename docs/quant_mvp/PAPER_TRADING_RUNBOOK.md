# PAPER TRADING RUNBOOK: Quant Trading MVP

This document provides the operational steps for the Human Operator to manage the paper trading session.

---

## 1. Pre-Session Checklist (Start of Day - [FUTURE])
- [ ] **Data Freshness:** Run `ws quant fetch-data`. Verify latest OHLCV is in `data/quant/raw/`.
- [ ] **Strategy Status:** Verify intended strategies are marked `paper_active` in `strategy_inventory.yaml`.
- [ ] **Risk Policy:** Verify `risk_policy.yaml` has not been modified unintentionally.
- [ ] **Environment:** Check `STATION_MODE` is set to `PAPER`.
- [ ] **Audit:** Verify previous day's reconciliation is complete.

---

## 2. Session Monitoring (Intraday - [FUTURE])
*Note: MVP focuses on daily/EOD rebalancing, but intraday checks are recommended.*
- **System Health:** Check logs for any data-ingestion errors or risk breaches.
- **Order Proposals:** Review any generated orders in `logs/quant/proposed_orders.json`.
- **Human Approval:** If policy requires, approve order proposals via the CLI/TUI.

---

## 3. Post-Session Tasks (End of Day - [FUTURE])
- [ ] **Fetch Fills:** Simulate fills based on the day's closing prices (or VWAP if available).
- [ ] **Reconcile:** Run `ws quant reconcile`. Compare `intended_positions` vs `actual_simulated_positions`.
- [ ] **Generate Review:** Use `ws quant review-memo` to have AI summarize the day's performance.
- [ ] **Check Kill-Switches:** Verify no strategies hit their "Max Daily Loss" or "Max Drawdown" triggers.

---

## 4. Promotion/Demotion Checklist
- **Demote to `paper_paused` if:**
  - Tracking error vs backtest exceeds 20% for 5 consecutive days.
  - Data feed is consistently stale.
  - Unexpected behavior (e.g., over-trading).
- **Retire if:**
  - Strategy hits its pre-defined "Kill Level" drawdown.
  - Market regime has fundamentally shifted (Human judgment).

---

## 5. Command Reference ([PROPOSED/FUTURE ONLY])
*The following commands are specifications for future implementation.*
- `ws quant status` - Summary of active paper strategies.
- `ws quant run` - Process signals and propose orders.
- `ws quant approve <id>` - Manually approve a proposed order.
- `ws quant reconcile` - Run EOD reconciliation.
- `ws quant stop <id>` - Emergency stop for a specific strategy.
