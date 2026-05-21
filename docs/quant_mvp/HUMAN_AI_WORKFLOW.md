# HUMAN-AI WORKFLOW: Quant Trading

This document outlines the collaborative workflow between the Human Operator, AI Agents, and Deterministic Systems.

---

## 1. Principles of Collaboration
- **AI as Accelerator:** Use AI to handle boilerplate, search for patterns, and draft complex specifications.
- **Human as Governor:** The human operator is the only entity permitted to "promote" a strategy to the next stage.
- **Software as Guardrail:** The deterministic engine enforces rules that neither the Human nor the AI can bypass without a material change to the `risk_policy.yaml`.

---

## 2. The 13-Step Workflow

### Phase A: Research & Ideation
1. **Human Hypothesis:** Operator defines a market intuition (e.g., "Small-cap ETFs outperform after a specific Fed signal").
2. **AI-Assisted Strategy Spec:** AI drafts a detailed `strategy_spec.md` based on the hypothesis, defining entry/exit/risk.
3. **Human Approval of Spec:** Operator reviews the spec for logic errors, look-ahead bias, or excessive complexity.

### Phase B: Implementation & Backtesting
4. **Deterministic Data Ingestion:** System fetches data according to `data_contracts.yaml`. No manual CSV manipulation.
5. **Deterministic Backtest:** System runs the backtest. AI may assist in writing the code, but the execution is deterministic.
6. **Walk-Forward / Stress Testing:** System tests the strategy on out-of-sample data and stress periods (e.g., 2008, 2020).

### Phase C: Validation & Promotion
7. **AI-Assisted Result Interpretation:** AI summarizes metrics (Sharpe, Drawdown, Calmar) and flags anomalies.
8. **Human Promotion Decision:** Operator reviews the `experiment_manifest.yaml` and decides to promote to "Approved for Paper".

### Phase D: Paper Trading
9. **Paper-Trading Activation:** Strategy status is updated to `paper_active`.
10. **Risk-Gated Order Proposal:** Strategy proposes an order. The `risk_gateway` checks against `risk_policy.yaml`.
11. **Human Approval (Optional/Policy-based):** Depending on the policy, the human may need to approve every paper order or just review the batch.

### Phase E: Post-Trade & Review
12. **Reconciliation:** Daily audit of intended vs. simulated filled positions.
13. **Post-Trade Review:** AI summarizes the day's performance; Human decides to continue, pause, or retire the strategy.

---

## 3. MatFinOg Principles Applied
- **Baby-Step Development:** Start with a single ETF trend-follower before moving to multi-asset portfolios.
- **Simplicity over Complexity:** If a strategy cannot be explained in a 1-page spec, it is too complex for the MVP.
- **Pre-defined Levels:** Every strategy must have a "Kill Level" (Max Drawdown) defined before it starts.
- **Portfolio over Holy Grail:** The system is designed to run a factory of small, uncorrelated strategies rather than one "perfect" bot.

---

## 4. Handoff Points
| From | To | Artifact |
|---|---|---|
| Human (Intuition) | AI (Specs) | `research/quant/hypothesis.md` |
| AI (Draft Spec) | Human (Review) | `contracts/quant/strategy_spec_template.md` |
| Human (Approval) | System (Runner) | `contracts/quant/strategy_inventory.yaml` |
| System (Backtest) | AI (Report) | `experiments/quant/run_result.json` |
| AI (Summary) | Human (Decision) | `contracts/quant/experiment_manifest_template.yaml` |
