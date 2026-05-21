# AGENT OPERATING POLICY: Quant Trading

This policy defines the rules and boundaries for AI Agents (Gemini, Codex, etc.) operating in the Quant Trading lane.

---

## 1. General Principles
- **No Direct Execution:** Agents must NEVER be given tools to directly place, modify, or cancel orders.
- **Evidence-Based Claims:** Agents must ground every claim (e.g., "Strategy A is robust") in a specific artifact (e.g., `experiment_manifest_v1.yaml`).
- **Transparency:** Agents must disclose any uncertainty or "UNKNOWN" variables in their summaries.

---

## 2. Permitted Actions
- **Drafting:** Writing strategy specs, Python boilerplate, and research notes.
- **Analysis:** Summarizing backtest results and flagging anomalies.
- **Debugging:** Proposing fixes for code errors in the backtest engine.
- **Documentation:** Updating PRDs, Roadmaps, and Runbooks based on human directives.

---

## 3. Forbidden Actions
- **Modifying Risk Policy:** Agents are forbidden from changing `risk_policy.yaml` without explicit human confirmation for each specific line change.
- **Bypassing Gates:** Agents cannot mark a strategy as `approved_for_paper` themselves.
- **Inventing Data:** Agents must not simulate "fake" data to make a strategy look successful.
- **Live Trading:** Agents must not attempt to create or use broker API credentials.

---

## 4. Interaction Protocol
1. **Request Evidence:** If an agent claims a performance metric, it must link to the file.
2. **Report Uncertainty:** If a backtest fails due to "Cholesky decomposition failure" (GSP lesson), the agent must report the technical error, not guess a fix.
3. **Status Check:** Before proposing a next action, the agent must read `strategy_inventory.yaml` to verify the current status.

---

## 5. File Modification Boundaries
- Agents may modify files in `research/quant/` and `strategies/candidates/`.
- Agents must be extremely conservative when modifying `contracts/quant/`.
- Agents should NEVER touch `logs/quant/` except to append new entries if specifically tasked.

---

## 6. Uncertainty Handling
- If the agent is unsure about a market mechanic or a data bias, it must mark it as **[UNKNOWN]** or **[REASONING_ONLY]**.
- Do not attempt to "hallucinate" a backtest result. If the runner hasn't executed, state "BACKTEST NOT RUN".
