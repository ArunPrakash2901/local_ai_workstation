# Human Approval Form Dry-Run Review (Q43)

## 1. Purpose
This document specifies the requirements for a future Human Approval Form (HAF) that must be satisfied before any write-mode command is executed through the unified `ws` workstation interface. This review focuses on the *structure* and *policy* of approval, not its implementation.

## 2. Core Approval Policies
- **Per-Command Approval:** Approval is granted for exactly one specific command execution.
- **Per-Run Expiry:** Approvals are transient and should expire after a short duration (e.g., 1 hour) or after the first successful execution.
- **Dry-Run Precondition:** An approval form can only be generated *after* a successful dry-run has been reviewed by the operator.
- **No Implicit Strategy Approval:** Approving a "write" action does NOT imply approval of the underlying trading strategy or backtest results.
- **No Financial Advice:** The approval form must explicitly disclaim financial advice.

## 3. Required Fields for Future Approval Artifacts
| Field | Description |
|---|---|
| `command_name` | The full `ws` command string approved. |
| `intended_artifact_path` | The specific file path allowed to be written. |
| `source_input_hash` | Hash of the input file (e.g., the idea markdown) to ensure no tampering. |
| `operator_signature` | Human-readable name or identifier of the operator. |
| `timestamp` | ISO timestamp of the approval. |
| `reason` | Brief justification for the write action. |
| `dry_run_artifact_id` | Reference to the dry-run output reviewed. |
| `explicit_write_confirm` | Boolean flag (MUST be True). |

## 4. Forbidden Approvals (Hard Gates)
The following actions can NEVER be approved through the standard workstation HAF:
- **Live Trading:** No connection to real brokers or exchange order entry.
- **Broker Execution:** No "send order" or "cancel order" logic.
- **Signal Generation:** No real-time buy/sell signal generation.
- **Unvalidated Backtests:** No real backtests unless all pre-flight gates (`readiness`, `eligibility`, `preflight`) report PASS.

## 5. Sample Approval Form (Conceptual)
```yaml
approval_id: HAF-RI-20260523-001
status: SIGNED
command: ws quant idea-intake --title "VWAP" --idea-file scratch/quant_ideas/vwap.md --write
artifact_target: reports/quant/research_ideas/RI-abc123.json
input_hash: sha256:7f83...
operator: Operator-01
intent: Intake validated VWAP research idea from file.
safety_disclaimer:
  financial_advice_generated: false
  trading_signals_allowed: false
  real_backtest_authorized: false
```

## 6. Current Implementation Scope
For milestone Q42-Q44, no approval forms are generated or required, as **write mode remains strictly blocked**. The `idea-intake-dry-run` command serves as the proof-of-concept for the "Dry-Run Precondition" stage.
