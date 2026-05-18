# Phase 4.13: Local Model Feature Review MVP Implementation

## Overview
Phase 4.13 implements the `ws feature-local-review` command, integrating local Ollama-hosted models as the primary qualitative reasoning gate within the Feature Stronghold workflow. This command allows for high-speed, cost-effective plan refinement and contract alignment checks before escalating to cloud-based reasoning or execution.

## Files Changed
- **`scripts/ws`**: Added `feature-local-review` to the help menu and dispatcher.
- **`scripts/ws_feature_local_review.sh`** (New): Created the shell script to orchestrate the local review process. It handles feature resolution, artifact collection, Ollama reachability checks, prompt construction, and state updates.
- **`WORKSTATION_MANUAL.md`**: Updated the Feature Strongholds section to document the new `ws feature-local-review` command and its role as a qualitative reasoning gate.

## Command Behavior
The command `ws feature-local-review <feature_id_or_path> --model hermes3:8b` performs the following:
1. **Resolves Feature**: Supports both absolute paths and feature slugs under `D:\_ai_brain\features`.
2. **Preflight Checks**: Verifies required artifacts (`state.json`, `feature_contract.md`, `current_plan.md`) and ensures Ollama is reachable with the requested model available.
3. **Artifact Aggregation**: Packages the feature contract, current plan, latest validation evidence, final report, handoff reviews, and run reports into a comprehensive "Local Context Packet."
4. **Local Model Query**: Invokes the `scripts/ollama_call.py` utility with a specialized "Senior Technical Architect" system prompt to assess implementation readiness.
5. **Durable Evidence**: 
   - Writes the model's full response to `<feature>/responses/local_review_<timestamp>.md`.
   - Records the complete transcript (including prompts) to `<feature>/evidence/local_model_<timestamp>.md`.
6. **State & Log Updates**:
   - Updates `state.json` with the latest review timestamp, model, and classification.
   - Appends a summary entry to `loop_log.md`.
7. **Conservative Classification**: Classifies the response into one of four states: `LOCAL_REVIEW_ACCEPTED`, `LOCAL_REVIEW_NEEDS_FIX`, `LOCAL_REVIEW_RECOMMENDS_CLOUD`, or `LOCAL_REVIEW_BLOCKED`.

## Validation Run
All implemented behavior was verified against the `stabilize-ws-command-documentation` feature:
- **Syntax Checks**: `bash -n` confirmed script integrity.
- **Ollama Check**: Verified `hermes3:8b` was available and responsive.
- **Execution**: Successfully ran `ws feature-local-review` against the target feature.
- **Outcome**: The local model returned `LOCAL_REVIEW_ACCEPTED`, and the orchestrator correctly updated the state and logs.
- **Artifact Inspection**: Confirmed that response and evidence files were correctly written and contained the expected reasoning.

## Limitations
- **Context Size**: Currently uses a fixed context size (8192) in `ollama_call.py`. Future iterations may need dynamic context handling for very large feature strongholds.
- **Model Specialization**: While `hermes3:8b` is the default, specialized technical review models like `qwen2.5-coder:7b` are supported but require manual selection via the `--model` flag.

## Next Steps
- Implement automated escalation patterns based on `LOCAL_REVIEW_RECOMMENDS_CLOUD`.
- Refine the "Failure Analysis" mode for summarizing provider errors from worktree agent runs.
