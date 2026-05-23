# Backtest Result Manifest Template

**Result Manifest ID:** {RESULT_MANIFEST_ID}
**Linked Plan ID:** {LINKED_BACKTEST_PLAN_ID}
**Status:** {RESULT_STATUS}
**Created At:** {CREATED_AT}

---

## Safety Boundary
**WARNING:** If marked as a synthetic smoke test, this is **not a strategy result, no real market data was used, no trading signal was generated, and no strategy was approved. No paper or live trading is allowed.**

Safety Flags:
- Financial Advice Generated: FALSE
- Trading Signal Generated: FALSE
- Bot Logic Generated: FALSE
- Live Trading Logic Generated: FALSE
- Synthetic Fixture Used: {SYNTHETIC_FIXTURE}

---

## 1. Run Summary
- **Data Source Type:** {DATA_SOURCE_TYPE}
- **Backtest Run:** {BACKTEST_RUN}
- **Strategy Logic Used:** {STRATEGY_LOGIC_USED}

## 2. Metrics & Artifacts
- **Metrics:** 
{METRICS}

- **Generated Artifacts:** 
{ARTIFACTS}

## 3. Limitations & Review
- **Limitations:** {LIMITATIONS}

---
## Human Review Checkpoint
- [ ] I confirm these results have been human-reviewed.
