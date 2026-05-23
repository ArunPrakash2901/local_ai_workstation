# Backtest Execution Preflight Template

**Preflight ID:** {PREFLIGHT_ID}
**Linked Eligibility ID:** {LINKED_ELIGIBILITY_REPORT_ID}
**Date Created:** {CREATED_AT}
**Status:** {PREFLIGHT_STATUS}

---

## Safety Boundary
**WARNING:** **This is not a backtest and does not execute code.** This is a final pre-run safety check. It does not approve trading. **Execution is allowed only if all gates pass.**

Safety Flags:
- Execution Allowed: {EXECUTION_ALLOWED}
- Financial Advice Generated: FALSE
- Trading Signal Generated: FALSE
- Bot Logic Generated: FALSE
- Live Trading Logic Generated: FALSE

---

## 1. Gate Validation Summary
- **All Gates Valid:** {ALL_GATES_VALID}
- **Dataset Import Valid:** {DATASET_IMPORT_VALID}
- **Approval Valid:** {APPROVAL_VALID}
- **Eligibility Valid:** {ELIGIBILITY_VALID}

## 2. Infrastructure Check
- **Backtest Runner Available:** {BACKTEST_RUNNER_AVAILABLE}

## 3. Issues
- **Blocking Issues:**
  - {BLOCKING_ISSUES}

## 4. Next Steps
- **Allowed Next Actions:** {ALLOWED_NEXT_ACTIONS}
- **Forbidden Next Actions:** {FORBIDDEN_NEXT_ACTIONS}

---
## Human Review Checkpoint
- [ ] I confirm this preflight is correct (Execution remains BLOCKED).
