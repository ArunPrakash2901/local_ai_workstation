# Hypothesis Contract Template

**Hypothesis ID:** {HYPOTHESIS_ID}
**Linked Idea ID:** {LINKED_IDEA_ID}
**Date Created:** {CREATED_AT}
**Review Status:** {REVIEW_STATUS}

---

## Safety Boundary
**WARNING:** This document outlines a falsifiable test plan. It is **not financial advice**, **not a trading signal**, **not a strategy**, **not approved for backtesting**, **not approved for paper trading**, and **not approved for live trading**.

Safety Flags:
- Financial Advice Generated: FALSE
- Trading Signal Generated: FALSE
- Bot Logic Generated: FALSE
- Live Trading Logic Generated: FALSE

---

## 1. The Claim
- **Hypothesis Statement:** {HYPOTHESIS_STATEMENT}
- **Falsifiable Claim:** (What exact metric or statistical result would prove this wrong?)
  - {FALSIFIABLE_CLAIM}
- **Expected Mechanism:** (Why does this inefficiency exist structurally?)
  - {EXPECTED_MECHANISM}
- **What is NOT being claimed:**
  - This does not claim predictive power outside of the defined structural constraint.

## 2. Evidence and Testing
- **Required Data:** {REQUIRED_DATA}
- **Data Availability Status:** {DATA_AVAILABILITY_STATUS}
- **Test Design:**
  - {TEST_DESIGN}

## 3. Validation and Risk Checklists
**Validation Checks:**
- {VALIDATION_CHECKS}

**Risk Checks:**
- {RISK_CHECKS}

**Execution Considerations:** (Slippage, spread, latency)
- {EXECUTION_CONSIDERATIONS}

## 4. Failure Modes
- **Failure Conditions:** (Under what market regimes does this break?)
  - {FAILURE_CONDITIONS}
- **Assumptions:**
  - {ASSUMPTIONS}
- **Unknowns:**
  - {UNKNOWNS}

---
## Human Review Checkpoint
- [ ] The claim is falsifiable and mathematically bound.
- [ ] Required data is accessible without look-ahead bias.
- [ ] Execution assumptions are realistic (slippage, fees accounted for).
- [ ] I approve promoting this Hypothesis Contract to research planning / out-of-sample backtest.
