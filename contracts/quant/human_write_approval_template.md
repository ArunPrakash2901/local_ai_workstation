# Human Write Approval Form: {{ approval_id }}

## 1. Approval Metadata
- **Approval ID:** {{ approval_id }}
- **Approval Type:** {{ approval_type }}
- **Status:** {{ approval_status }}
- **Created At:** {{ created_at }}
- **Expires At:** {{ expires_at }}
- **Operator:** {{ operator_name }}

## 2. Target Command
- **Command:** `{{ target_command }}`
- **Safety Class:** {{ target_command_safety_class }}
- **Reason:** {{ reason_for_write }}

## 3. Evidence and Artifacts
- **Source Input File:** `{{ source_input_file }}`
- **Source Input Hash:** `{{ source_input_hash }}`
- **Dry-Run Command:** `{{ dry_run_command }}`
- **Dry-Run Output Hash:** `{{ dry_run_output_hash }}`
- **Intended Output Directory:** `{{ intended_output_directory }}`
- **Intended Output Filename:** `{{ intended_output_filename }}`
- **Artifact Type:** {{ intended_artifact_type }}

## 4. Operator Statement
I, {{ operator_name }}, confirm that:
- I have reviewed the dry-run output and verified it matches the intended research goal.
- The source input file hash is correct and the file has not been tampered with since dry-run.
- I understand that this approval is for a single local write operation only.
- **Operator Confirmation:** {{ operator_confirmation }}

## 5. Explicit Limits and Scope
- **Approval Scope:** {{ approval_scope }}
- This approval does NOT authorize any trading, signal generation, or backtest execution.
- This approval does NOT constitute financial advice.

## 6. Forbidden Actions
The following actions are STRICTLY FORBIDDEN under this approval:
{% for action in forbidden_actions %}
- {{ action }}
{% endfor %}

## 7. Safety Boundary Confirmation
- `safety_financial_advice_generated`: {{ safety_financial_advice_generated }}
- `safety_trading_signal_generated`: {{ safety_trading_signal_generated }}
- `safety_bot_logic_generated`: {{ safety_bot_logic_generated }}
- `safety_live_trading_logic_generated`: {{ safety_live_trading_logic_generated }}
- `safety_backtest_run`: {{ safety_backtest_run }}
- `safety_broker_logic_generated`: {{ safety_broker_logic_generated }}
- `safety_live_trading_authorized`: {{ safety_live_trading_authorized }}
