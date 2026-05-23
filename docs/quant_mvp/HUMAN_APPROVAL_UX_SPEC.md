# Human Approval UX Specification (Q31)

## 1. Purpose
This document specifies the mandatory Human-in-the-Loop (HITL) approval workflow required before any single "Real Backtest" can be executed. This ensures explicit operator accountability and prevents automated or accidental execution of financial research logic.

## 2. Approval Flow
The approval process follows a strict linear sequence:
1. **Pre-requisite:** `ws quant backtest preflight` must return `READY` (all technical gates passed).
2. **Drafting:** The system generates an `APPROVAL_INPUT_DRAFT.md` containing the IDs of all linked research artifacts.
3. **Operator Signing:** The human operator reviews the draft and provides a "Signature" (explicit confirmation text/token).
4. **Validation:** The system verifies the signature and writes a permanent, hashed `BACKTEST_APPROVAL.json` artifact.
5. **Unlock:** The Backtest Runner detects the valid approval and allows a **single** execution run.

## 3. Required Fields for Human Completion
The operator must explicitly confirm and/or provide the following fields in the approval form:

| Field | Description | Requirement |
|---|---|---|
| `candidate_id` | The ID of the strategy logic to be tested (e.g., `CAN-951be4d5c93a-R3`). | Mandatory |
| `backtest_plan_id` | The ID of the specific plan defining parameters and universe. | Mandatory |
| `dataset_import_id` | The ID of the validated local CSV dataset. | Mandatory |
| `approval_expiry` | ISO timestamp after which this approval is void (default 24h). | Mandatory |
| `execution_intent` | One-sentence statement of why this backtest is being run. | Mandatory |
| `operator_signature` | A specific string confirming "I authorize this research-only backtest". | Mandatory |

## 4. Mandatory Explicit Confirmations
The approval document must contain checkboxes or statements that the user must "sign" by leaving them in the document:
- [ ] I confirm this is for **Research Purposes Only**.
- [ ] I confirm **No Financial Advice** is being generated.
- [ ] I confirm **No Broker/Trading Authorization** is granted.
- [ ] I acknowledge results are based on historical data and do not guarantee future performance.
- [ ] I confirm no paper or live trading logic is active.

## 5. System Refusal Criteria
The system must automatically refuse to generate or validate an approval if:
- Any technical gate (Readiness, Eligibility, Data) is `FAIL` or `BLOCKED`.
- The operator attempts to authorize more than one candidate or dataset at once.
- The approval document contains keywords like "live", "trade", "broker", or "profit guarantee" in the intent field (Regex Guard).
- The `candidate_id` hash does not match the current local file state.

## 6. Audit Trail & Expiry
- **Audit:** Every approval is recorded in `reports/quant/backtest_approvals/` with a timestamp and a hash of the entire approval state.
- **Revocation:** An operator can revoke an approval by deleting the file or moving it to `archive/`.
- **Expiry:** The runner must check `approval_expiry` and refuse execution if the current system time exceeds the limit.

## 7. Sample Approval Form (`APPROVAL_INPUT_DRAFT.md`)
```markdown
# BACKTEST EXECUTION APPROVAL DRAFT
Status: PENDING SIGNATURE
Generated: 2026-05-23T10:00:00Z

## 1. Traceability
- Candidate: CAN-951be4d5c93a-R3
- Plan: BTP-951be4d5c93a-R3
- Dataset: IMP-e948cb959f40

## 2. Authorization Scope
- Execution Mode: LOCAL_SINGLE_RUN
- Max Data Rows: 5000
- Expiry: 2026-05-24T10:00:00Z

## 3. Operator Statement
Intent: Validating VWAP mean reversion on SPY daily synthetic data to confirm signal timing.

## 4. Safety Acknowledgement
[SIGNATURE_REQUIRED] I, the operator, authorize this single research backtest. I acknowledge that no trading authorization is granted and no financial advice is generated.

Signature: [Type Full Name or Token Here]
```

## 8. Difference from Other Approvals
- **Strategy Approval:** Approves the *logic* for research candidacy.
- **Backtest Approval:** Authorizes the *compute* and *data usage* for a specific run.
- **Trading Approval:** **STRICTLY FORBIDDEN.** The workstation does not support this.
