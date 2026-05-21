# INCIDENT PLAYBOOK: Quant Trading MVP

Standard Operating Procedures (SOP) for handling anomalies and failures.

---

## 1. Data Incidents

### Stale or Missing Data
- **Symptom:** Ingestion script returns `NULL` or 0 rows; data timestamp is $> 24h$ old.
- **Response:**
  1. **Block Orders:** The `risk_gateway` must automatically block any new orders for affected instruments.
  2. **Manual Check:** Operator checks the source API status (e.g., Alpaca/Yahoo Finance).
  3. **No Trade:** If data is not recovered by market close, the strategy skips the rebalance session.

---

## 2. Order & Risk Incidents

### Duplicate Order Proposal
- **Symptom:** Strategy proposes two identical orders within the same window.
- **Response:** `risk_gateway` deduplicates based on `duplicate_order_window` (default 5 mins). Log as WARNING.

### Daily Loss Breach
- **Symptom:** Simulated PnL drops below `max_daily_loss_pct_nav` in `risk_policy.yaml`.
- **Response:**
  1. **Auto-Pause:** Strategy status set to `paper_paused`.
  2. **Alert:** CLI/TUI prints CRITICAL alert.
  3. **Human Audit:** Human must investigate and manually reset the status to `paper_active` after review.

### Unexpected Fill / Slippage
- **Symptom:** Simulated fill price is outside the `price_collar_bps`.
- **Response:** Log as ERROR. Investigate data source or volatility regime.

---

## 3. AI & Agent Incidents

### AI Hallucinated Claim
- **Symptom:** Agent claims a strategy passed validation without a corresponding `experiment_manifest.yaml`.
- **Response:**
  1. **Reject Claim:** Human/System ignores the claim.
  2. **Trace:** Audit the agent's prompt/context to see where the hallucination originated.
  3. **Correct:** Re-run the validation script to generate ground-truth artifacts.

### Accidental Live-Mode Config
- **Symptom:** Config file shows `live_trading_allowed: true`.
- **Response:**
  1. **IMMEDIATE REVERSION:** Revert the file via Git.
  2. **Block Execution:** The system must hard-crash if `LIVE` mode is detected in MVP.

---

## 4. Emergency Procedures

### Full Kill-Switch
- **Action:** Delete or rename `contracts/quant/active_trading_token.lock`.
- **Effect:** Prevents the `execution_engine` from processing any orders, regardless of strategy status.

### Strategy-Specific Stop
- **Action:** Update `strategy_inventory.yaml` status to `rejected`.
- **Effect:** Stops all future signals for that specific ID.
