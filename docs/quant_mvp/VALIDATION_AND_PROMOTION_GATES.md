# VALIDATION & PROMOTION GATES: Quant Trading MVP

This document defines the formal lifecycle of a strategy through the workstation's safety gates.

---

## Gate 1: Idea Intake
- **Status Change:** `none` -> `idea`
- **Required Inputs:** `hypothesis.md` (Research Notes)
- **Reviewer:** Human (Self)
- **Pass Criteria:** Hypothesis is logically sound and fits the workstation's focus (e.g., US ETFs).
- **Artifact:** `research/quant/hypothesis.md`

---

## Gate 2: Specification Approval
- **Status Change:** `idea` -> `approved_for_backtest`
- **Required Inputs:** `strategy_spec.md` (Measurable entry/exit/risk)
- **Reviewer:** Human (Self)
- **Pass Criteria:** No vague terms (e.g., "when price looks low"). Logic is implementable in code.
- **Artifact:** `contracts/quant/strategy_spec.md` entry in `strategy_inventory.yaml`.

---

## Gate 3: Backtest Approval
- **Status Change:** `approved_for_backtest` -> `backtested`
- **Required Inputs:** `backtest_metrics.json`, `equity_curve.png`
- **Reviewer:** Human (Self)
- **Pass Criteria:** Strategy meets minimum performance targets (e.g., Sharpe > 1.0) and uses correct transaction costs.
- **Artifact:** `experiments/quant/run_id_metrics.json`

---

## Gate 4: Robustness Approval
- **Status Change:** `backtested` -> `validation_review`
- **Required Inputs:** Walk-forward results, Stress test results, Sensitivity analysis.
- **Reviewer:** Human (Self)
- **Pass Criteria:** Strategy survives stress tests and is not hyper-sensitive to parameter changes.
- **Artifact:** `experiment_manifest.yaml` with `pass_fail_status: PASS`.

---

## Gate 5: Paper-Trading Approval
- **Status Change:** `validation_review` -> `approved_for_paper`
- **Required Inputs:** Final promotion memo (AI-assisted summary of Gate 1-4 evidence).
- **Reviewer:** Human (Self)
- **Pass Criteria:** Absolute human confidence in the strategy's safety and research integrity.
- **Artifact:** `strategy_inventory.yaml` update to `approved_for_paper`.

---

## Gate 6: Paper Performance Review
- **Status Change:** `paper_active` -> `paper_retired` or `paper_paused`
- **Required Inputs:** 30+ days of paper trading logs and daily reconciliation reports.
- **Reviewer:** Human (Self)
- **Pass Criteria:** (For continuing) Realized tracking error vs backtest is within acceptable bounds.
- **Artifact:** `paper_trade_review_template.md`

---

## Gate 7: Live-Readiness Review (OUTSIDE MVP)
- **Status Change:** `approved_for_paper` -> `live_blocked_mvp`
- **Note:** This gate is purely theoretical for the MVP to identify gaps. Live trading is forbidden.
- **Required Inputs:** Execution quality analysis, infrastructure redundancy audit, legal/compliance check.
- **Artifact:** `LIVE_READINESS_AUDIT.md` (Research only).
