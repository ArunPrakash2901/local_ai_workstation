# Backtest Handoff Manifest Template

**Handoff ID:** {HANDOFF_ID}
**Linked Candidate ID:** {LINKED_STRATEGY_CANDIDATE_ID}
**Linked Readiness ID:** {LINKED_READINESS_ID}
**Date Created:** {CREATED_AT}
**Handoff Status:** {HANDOFF_STATUS}

---

## Safety Boundary
**WARNING:** This is a handoff manifest only. **No backtest has been run, no performance claim exists, human approval is required before future backtesting, and no trading or execution is approved.**

Safety Flags:
- Financial Advice Generated: FALSE
- Trading Signal Generated: FALSE
- Bot Logic Generated: FALSE
- Live Trading Logic Generated: FALSE

---

## 1. Scope and Requirements
- **Intended Backtest Scope:** {INTENDED_BACKTEST_SCOPE}
- **Required Datasets:** {REQUIRED_DATASETS}
- **Required Features:** {REQUIRED_FEATURES}
- **Cost Model:** {COST_MODEL}
- **Slippage Model:** {SLIPPAGE_MODEL}

## 2. Testing Protocols
- **Validation Protocol:** {VALIDATION_PROTOCOL}
- **Bias Checks:** {BIAS_CHECKS}
- **Risk Checks:** {RISK_CHECKS}
- **Expected Artifacts:** {EXPECTED_ARTIFACTS}

## 3. Allowed Actions
- **Allowed Next Actions:**
  - {ALLOWED_NEXT_ACTIONS}
- **Forbidden Next Actions:**
  - {FORBIDDEN_NEXT_ACTIONS}

---
## Human Review Checkpoint
- [ ] I confirm this handoff is fully defined.
- [ ] I authorize this handoff to be queued for future backtesting.
