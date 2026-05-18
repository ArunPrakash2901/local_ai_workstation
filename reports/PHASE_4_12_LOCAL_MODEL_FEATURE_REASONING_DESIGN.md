# Phase 4.12: Local Model Feature Reasoning Design

## Executive Summary
The workstation has matured significantly in its orchestration of Feature Strongholds, worktree isolation, and supervised agent execution. However, local reasoning remains underutilized. This design document establishes local Ollama-hosted models as the primary "Reasoning Gate" within the Feature Stronghold loop. By inserting a local reasoning layer before cloud escalation (Browser/Codex), the workstation can refine plans, catch logic errors early, and reduce token costs and manual copy-paste friction.

## 1. Loop Integration
Local models will serve as the **first reasoning layer** after local validation.

**Workflow Position:**
1. `ws feature-new` (Initiate)
2. `ws feature-plan` (Draft)
3. `ws feature-validate` (Deterministic Preflight)
4. **`ws feature-local-review` (Local Model Reasoning Gate) <-- NEW**
5. `ws feature-handoff` (High-Context Cloud Escalation - Optional)
6. `ws feature-run --dry-run` (Execution Preflight)
7. `ws agent-run-worktree --apply` (Supervised Mutation)

## 2. Default Models
The workstation will support multiple model profiles based on the task type:
- **`hermes3:8b` (Default)**: General reasoning, plan refinement, and contract alignment.
- **`qwen2.5-coder:7b`**: Specialized code review, diff analysis, and technical feasibility checks.
- **`deepseek-coder-v2:lite`**: High-performance code reasoning (if VRAM/Memory allows).

## 3. Command Surface
**Primary Command:**
```bash
ws feature-local-review <feature_id_or_path> --model <model_name> [--purpose <p>]
```
- `<feature_id_or_path>`: Resolves to the feature stronghold folder.
- `--model`: Optional override (defaults to `hermes3:8b`).
- `--purpose`: Optional hint (e.g., `refine-plan`, `check-security`, `summarize-failure`).

## 4. Reasoning Timing
Local review should occur:
- **Pre-Handoff**: To ensure the prompt/context being sent to ChatGPT/Gemini is high-quality.
- **Pre-Apply**: To double-check the final implementation plan against the feature contract.
- **Post-Failure**: To analyze provider errors (e.g., Codex timeouts or diff violations) and suggest corrective actions for the human operator.

## 5. Feature Artifacts Ingested
The local model will ingest a "Local Context Packet" including:
- `feature_contract.md`: The core requirements and constraints.
- `current_plan.md`: The intended implementation steps.
- `evidence/validation_*.md`: The latest deterministic validation pass results.
- `final_report.md`: The summarized feature state (if generated).
- `loop_log.md`: Historical activity and state transitions.
- Latest `auto_runs/` metadata (if a provider failure needs analysis).

## 6. Security & Exclusions
To maintain workstation integrity, the following must **never** be sent to local models (even though they are local):
- `.env` files or hardcoded credentials.
- `credentials/` or `secrets/` folders.
- Large raw datasets (to avoid context window overflow).
- Binary model files.
- `.git` internal metadata.

## 7. Output & Evidence
Local model reasoning must be durable and auditable.
- **Transcript**: `<feature>/evidence/local_model_<timestamp>_transcript.md`
- **Report**: `<feature>/responses/local_review_<timestamp>.md`
- **Metadata**: Linked in `state.json` under `latest_local_review`.

## 8. Reasoning Classifications
The output must include a deterministic classification line:
- `LOCAL_REVIEW_ACCEPTED`: The plan is robust and aligns with the contract.
- `LOCAL_REVIEW_NEEDS_FIX`: Specific logic or safety gaps detected; identifies "Refinement Actions."
- `LOCAL_REVIEW_RECOMMENDS_CLOUD`: The task is too complex for local reasoning; recommends escalation to ChatGPT/Gemini.
- `LOCAL_REVIEW_BLOCKED`: Major contract violations or missing information.

## 9. Automation Policy
**Local models shall NOT automatically approve apply runs.**
Local reasoning is a decision-support tool. The final authority to transition to `feature-run --apply` remains with the human operator after reviewing both the deterministic validation (`feature-validate`) and the local model's qualitative review.

## 10. Resilience & Fallback
If Ollama is unavailable or the model fails to load:
- The command should exit with `LOCAL_REASONING_UNAVAILABLE`.
- The workstation will advise the operator to proceed with manual review or standard browser handoff.
- The workflow remains unblocked but "un-refined."

## 11. Efficiency Gains
- **Reduced Copy-Paste**: Local models can pre-summarize complex issues, reducing the amount of text a human needs to manually move to the browser.
- **Reduced Cloud Usage**: Catching "hallucinated" plans or simple syntax errors locally prevents wasted Codex/Gemini tokens.
- **Faster Iteration**: Local feedback loops take seconds, compared to the minute-long round trips of browser-based prompting.

## 12. Provider Failure Analysis
If an `agent-run-worktree` execution fails (e.g., `CODEX_FAILED_PROVIDER`), `ws feature-local-review` will have a specialized mode (`--purpose failure-analysis`) to:
1. Ingest `codex_stderr.md` and `changed_files.md`.
2. Compare the failed output against `current_plan.md`.
3. Output a "Correction Plan" to help the operator recover.

## 13. Recommended MVP Implementation
The MVP will focus on the read-only review of a plan against a contract.
**Command:** `ws feature-local-review <id> --model hermes3:8b`
**Behavior:**
1. Package contract + plan + validation status.
2. Call Ollama with a specialized "Feature Auditor" system prompt.
3. Classify and save the response into the feature folder.
4. Update the `loop_log.md`.

## Next Steps
1. Create `scripts/ws_feature_local_review.sh`.
2. Implement the "Feature Auditor" system prompt.
3. Integrate with the existing `scripts/ollama_call.py`.
4. Validate against a real feature plan.
