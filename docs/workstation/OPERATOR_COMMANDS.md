# Operator Commands

This document outlines the intended short command surface for the Local AI Workstation. It focuses on lightweight, deterministic operations that stay within the 16GB RAM and strict 8GB VRAM limits. 

## Workstation Status

*   **User-facing command:** `ws status` (Current) / `/status` (Proposed)
*   **Underlying script:** `scripts/check_health.ps1` and `scripts/ai_model_current.sh`
*   **Read/write behavior:** Reads local processes and configurations; no writes.
*   **Default dry-run behavior:** N/A (Status check only)
*   **Safety class:** `PURE_READ`
*   **Expected RAM/GPU usage:** < 50MB RAM, 0GB VRAM.

## Quant Idea Intake

*   **User-facing command:** `ws quant idea new` (Proposed) / `/quant idea new` (Proposed)
*   **Underlying script:** `scripts/quant/idea_cli.py idea-intake` (Standalone Implementation)
*   **Read/write behavior:** Writes JSON/Markdown hypothesis contract under `reports/quant/research_ideas/`.
*   **Default dry-run behavior:** Renders preview of the contract without writing to disk.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Hypothesis Draft

*   **User-facing command:** `ws quant hypothesis draft` (Proposed) / `/quant hypothesis draft` (Proposed)
*   **Underlying script:** `scripts/quant/idea_cli.py hypothesis-draft` (Standalone Implementation)
*   **Read/write behavior:** Reads the idea record and writes a draft contract JSON.
*   **Default dry-run behavior:** Prints draft output to standard out.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Paper Intake

*   **User-facing command:** `ws quant paper intake` (Proposed) / `/quant paper intake` (Proposed)
*   **Underlying script:** `scripts/quant/paper_replication_cli.py paper-intake` (Standalone Implementation)
*   **Read/write behavior:** Writes JSON paper record under `reports/quant/paper_replications/`.
*   **Default dry-run behavior:** Renders preview of the record without writing.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Replication Plan

*   **User-facing command:** `ws quant replication plan` (Proposed) / `/quant replication plan` (Proposed)
*   **Underlying script:** `scripts/quant/paper_replication_cli.py replication-plan-draft` (Standalone Implementation)
*   **Read/write behavior:** Writes a JSON replication plan draft under `reports/quant/paper_replications/`.
*   **Default dry-run behavior:** Prints draft output to standard out.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

# Integrated Quant Lane Commands (Phase 6)

These commands are integrated into the unified `ws` tool and are safe, read-only status summaries.

**SAFETY NOTICE:** Real backtests, approvals, and data downloads are BLOCKED in `ws quant` and remain restricted to standalone research CLIs.

## Quant Dashboard

*   **User-facing command:** `ws quant dashboard`
*   **Underlying script:** `scripts/quant/ws_quant_summary.py dashboard`
*   **Read/write behavior:** Reads high-level status, tools, gates, and synthetic state. No writes.
*   **Safety class:** `PURE_READ`
*   **Expected RAM/GPU usage:** < 50MB RAM, 0GB VRAM.

## Quant Idea Intake Dry-Run

*   **User-facing command:** `ws quant idea-intake-dry-run --title <t> --source-type <s|human_note> --idea-file <f>`
*   **Underlying script:** `scripts/quant/idea_cli.py idea-intake ... --dry-run`
*   **Read/write behavior:** Reads input file and validates idea record. No writes.
*   **Safety class:** `DRY_RUN_ONLY`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Guarded Write Design (Q45-Q47)

*   **Status:** DESIGNED but BLOCKED.
*   **Planned Command:** `ws quant idea-intake-write --approval-file <approval_file>` (Not implemented)
*   **Safety Posture:** No `ws` write command exists. All mutation remains blocked.
*   **Approval Protocol:** Requires a Human Approval Form (HAF) matching `human_write_approval_schema.yaml`.
*   **Validation:** `scripts/quant/human_write_approval.py` verifies approvals but always blocks execution in this milestone.

## Quant Reports

*   **User-facing command:** `ws quant reports`
*   **Underlying script:** `scripts/quant/ws_quant_summary.py reports`
*   **Read/write behavior:** Lists files in `docs/quant_mvp/`. No writes.
*   **Safety class:** `PURE_READ`
*   **Expected RAM/GPU usage:** < 50MB RAM, 0GB VRAM.

## Quant Artifacts

*   **User-facing command:** `ws quant artifacts`
*   **Underlying script:** `scripts/quant/ws_quant_summary.py artifacts`
*   **Read/write behavior:** Summarizes counts in `reports/quant/`. No writes.
*   **Safety class:** `PURE_READ`
*   **Expected RAM/GPU usage:** < 50MB RAM, 0GB VRAM.

## Quant Lineage

*   **User-facing command:** `ws quant lineage <id>`
*   **Underlying script:** `scripts/quant/ws_quant_summary.py lineage <id>`
*   **Read/write behavior:** Reads single JSON artifact to trace links. No writes.
*   **Safety class:** `PURE_READ`
*   **Expected RAM/GPU usage:** < 50MB RAM, 0GB VRAM.

## Quant Cheatsheet

*   **User-facing command:** `ws quant cheatsheet`
*   **Underlying script:** `scripts/quant/ws_quant_summary.py cheatsheet`
*   **Read/write behavior:** Reads and displays `docs/quant_mvp/QUANT_OPERATOR_CHEATSHEET.md`. No writes.
*   **Safety class:** `PURE_READ`
*   **Expected RAM/GPU usage:** < 50MB RAM, 0GB VRAM.

## Quant Status

*   **User-facing command:** `ws quant status`
*   **Underlying script:** `scripts/quant/ws_quant_summary.py status`
*   **Read/write behavior:** Reads high-level status from `reports/quant/` and `contracts/quant/`. No writes.
*   **Safety class:** `PURE_READ`
*   **Expected RAM/GPU usage:** < 50MB RAM, 0GB VRAM.

## Quant List Tools

*   **User-facing command:** `ws quant list-tools`
*   **Underlying script:** `scripts/quant/ws_quant_summary.py list-tools`
*   **Read/write behavior:** Lists files in `scripts/quant/`. No writes.
*   **Safety class:** `PURE_READ`
*   **Expected RAM/GPU usage:** < 50MB RAM, 0GB VRAM.

## Quant Synthetic Status

*   **User-facing command:** `ws quant synthetic-status`
*   **Underlying script:** `scripts/quant/ws_quant_summary.py synthetic-status`
*   **Read/write behavior:** Reads synthetic execution and review artifacts. No writes.
*   **Safety class:** `PURE_READ`
*   **Expected RAM/GPU usage:** < 50MB RAM, 0GB VRAM.

## Quant Gates Status

*   **User-facing command:** `ws quant gates-status`
*   **Underlying script:** `scripts/quant/ws_quant_summary.py gates-status`
*   **Read/write behavior:** Reads pre-backtest gate statuses (readiness, eligibility, preflight, approval). No writes.
*   **Safety class:** `PURE_READ`
*   **Expected RAM/GPU usage:** < 50MB RAM, 0GB VRAM.

## Quant Backlog

*   **User-facing command:** `ws quant backlog` (Proposed) / `/quant backlog` (Proposed)
*   **Underlying script:** TBD (`quant.cli` expansion for Phase 3)
*   **Read/write behavior:** Reads the `NEXT_IMPLEMENTATION_BACKLOG.md` and queue metrics.
*   **Default dry-run behavior:** N/A (Read-only)
*   **Safety class:** `PURE_READ`
*   **Expected RAM/GPU usage:** < 50MB RAM, 0GB VRAM.

## MatFinOg Overview

*   **User-facing command:** `ws matfinog overview` (Proposed) / `/matfinog overview` (Proposed)
*   **Underlying script:** `knowledge/matfinog_youtube/scripts/08_browse_knowledge_base.py overview`
*   **Read/write behavior:** Reads CSV/JSONL indices and renders summary.
*   **Default dry-run behavior:** N/A (Read-only)
*   **Safety class:** `PURE_READ`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## MatFinOg Prompt Browsing

*   **User-facing command:** `ws matfinog prompts` (Proposed) / `/matfinog prompts` (Proposed)
*   **Underlying script:** `knowledge/matfinog_youtube/scripts/08_browse_knowledge_base.py list-prompts`
*   **Read/write behavior:** Reads prompt JSONL library.
*   **Default dry-run behavior:** N/A (Read-only)
*   **Safety class:** `PURE_READ`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## MatFinOg Review Queue

*   **User-facing command:** `ws matfinog queue` (Proposed) / `/matfinog queue` (Proposed)
*   **Underlying script:** `knowledge/matfinog_youtube/scripts/08_browse_knowledge_base.py review-queue`
*   **Read/write behavior:** Reads review queue CSV.
*   **Default dry-run behavior:** N/A (Read-only)
*   **Safety class:** `PURE_READ`
*   **Expected RAM/GPU usage:** < 50MB RAM, 0GB VRAM.

## Safety Validation

*   **User-facing command:** `ws safety check` (Proposed) / `/safety check` (Proposed)
*   **Underlying script:** `scripts/check_local_safety.py` and `scripts/validate_ws_command_safety.py`
*   **Read/write behavior:** Reads Python scripts, bash scripts, and YAML manifests. No writes.
*   **Default dry-run behavior:** N/A (Check execution)
*   **Safety class:** `PURE_READ`
*   **Expected RAM/GPU usage:** < 150MB RAM, 0GB VRAM.

## Quant Candidate Draft

*   **User-facing command:** `ws quant candidate draft` (Proposed) / `/quant candidate draft` (Proposed)
*   **Underlying script:** `scripts/quant/strategy_candidate_cli.py candidate-draft` (Standalone Implementation)
*   **Read/write behavior:** Writes JSON candidate record under `reports/quant/strategy_candidates/`.
*   **Default dry-run behavior:** Renders preview of the record without writing.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Readiness Check

*   **User-facing command:** `ws quant readiness check` (Proposed) / `/quant readiness check` (Proposed)
*   **Underlying script:** `scripts/quant/strategy_candidate_cli.py readiness-check` (Standalone Implementation)
*   **Read/write behavior:** Writes JSON readiness record under `reports/quant/pre_backtest_readiness/`.
*   **Default dry-run behavior:** Prints evaluation to standard out.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Backtest Handoff

*   **User-facing command:** `ws quant backtest handoff` (Proposed) / `/quant backtest handoff` (Proposed)
*   **Underlying script:** `scripts/quant/strategy_candidate_cli.py backtest-handoff-draft` (Standalone Implementation)
*   **Read/write behavior:** Writes JSON handoff manifest under `reports/quant/backtest_handoffs/`.
*   **Default dry-run behavior:** Prints manifest draft to standard out.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Backtest Schema Check

*   **User-facing command:** `ws quant backtest schema-check` (Proposed) / `/quant backtest schema check` (Proposed)
*   **Underlying script:** `scripts/quant/backtest_cli.py schema-check`
*   **Read/write behavior:** Reads YAML schemas. No writes.
*   **Default dry-run behavior:** Standard output validation.
*   **Safety class:** `PURE_READ`
*   **Expected RAM/GPU usage:** < 50MB RAM, 0GB VRAM.

## Quant Backtest Plan Draft

*   **User-facing command:** `ws quant backtest plan-draft` (Proposed) / `/quant backtest plan draft` (Proposed)
*   **Underlying script:** `scripts/quant/backtest_cli.py plan-draft`
*   **Read/write behavior:** Writes JSON plan record under `reports/quant/backtest_plans/`.
*   **Default dry-run behavior:** Prints plan evaluation.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Backtest Synthetic Smoke

*   **User-facing command:** `ws quant backtest synthetic-smoke` (Proposed) / `/quant backtest synthetic smoke` (Proposed)
*   **Underlying script:** `scripts/quant/backtest_cli.py synthetic-smoke`
*   **Read/write behavior:** Reads synthetic JSON fixtures and writes JSON results manifest.
*   **Default dry-run behavior:** Prints output without writing.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Readiness Gap Report

*   **User-facing command:** `ws quant readiness gap-report` (Proposed) / `/quant readiness gap-report` (Proposed)
*   **Underlying script:** `scripts/quant/readiness_remediation_cli.py gap-report`
*   **Read/write behavior:** Writes JSON gap report under `reports/quant/readiness_gap_reports/`.
*   **Default dry-run behavior:** Prints gap report without writing.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Revise Candidate

*   **User-facing command:** `ws quant candidate revise` (Proposed) / `/quant candidate revise` (Proposed)
*   **Underlying script:** `scripts/quant/readiness_remediation_cli.py revise-candidate`
*   **Read/write behavior:** Writes JSON revision and new candidate under `reports/quant/strategy_candidate_revisions/` and `reports/quant/strategy_candidates/`.
*   **Default dry-run behavior:** Prints revision draft.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Readiness Recheck

*   **User-facing command:** `ws quant readiness recheck` (Proposed) / `/quant readiness recheck` (Proposed)
*   **Underlying script:** `scripts/quant/backtest_preparation_cli.py readiness-recheck` (and `backtest_eligibility_cli.py` for R2+)
*   **Read/write behavior:** Writes JSON readiness record under `reports/quant/pre_backtest_readiness/`.
*   **Default dry-run behavior:** Prints evaluation.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Plan Rebuild

*   **User-facing command:** `ws quant plan rebuild` (Proposed) / `/quant plan rebuild` (Proposed)
*   **Underlying script:** `scripts/quant/backtest_eligibility_cli.py plan-rebuild`
*   **Read/write behavior:** Writes JSON plan record under `reports/quant/backtest_plans/`.
*   **Default dry-run behavior:** Prints evaluation.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Approval Validate

*   **User-facing command:** `ws quant approval validate` (Proposed) / `/quant approval validate` (Proposed)
*   **Underlying script:** `scripts/quant/backtest_eligibility_cli.py approval-validate`
*   **Read/write behavior:** Writes JSON validation record under `reports/quant/backtest_approval_validations/`.
*   **Default dry-run behavior:** Prints evaluation.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Eligibility Report

*   **User-facing command:** `ws quant eligibility report` (Proposed) / `/quant eligibility report` (Proposed)
*   **Underlying script:** `scripts/quant/backtest_eligibility_cli.py eligibility-report`
*   **Read/write behavior:** Writes JSON eligibility record under `reports/quant/backtest_eligibility_reports/`.
*   **Default dry-run behavior:** Prints evaluation.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Concrete Spec

*   **User-facing command:** `ws quant candidate concretize` (Proposed) / `/quant candidate concretize` (Proposed)
*   **Underlying script:** `scripts/quant/backtest_execution_gate_cli.py concrete-spec`
*   **Read/write behavior:** Writes JSON spec and R3 candidate record under `reports/quant/candidate_concrete_specs/` and `reports/quant/strategy_candidates/`.
*   **Default dry-run behavior:** Prints spec draft.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Dataset Import

*   **User-facing command:** `ws quant dataset import` (Proposed) / `/quant dataset import` (Proposed)
*   **Underlying script:** `scripts/quant/backtest_execution_gate_cli.py dataset-import`
*   **Read/write behavior:** Writes JSON import record under `reports/quant/manual_dataset_imports/`.
*   **Default dry-run behavior:** Prints evaluation.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Backtest Preflight

*   **User-facing command:** `ws quant backtest preflight` (Proposed) / `/quant backtest preflight` (Proposed)
*   **Underlying script:** `scripts/quant/backtest_execution_gate_cli.py preflight`
*   **Read/write behavior:** Writes JSON preflight record under `reports/quant/backtest_execution_preflights/`.
*   **Default dry-run behavior:** Prints evaluation.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Synthetic Run

*   **User-facing command:** `ws quant backtest synthetic-run` (Proposed) / `/quant backtest synthetic run` (Proposed)
*   **Underlying script:** `scripts/quant/synthetic_execution_cli.py run-synthetic`
*   **Read/write behavior:** Reads CSV fixtures and writes JSON execution run under `reports/quant/synthetic_execution_runs/`.
*   **Default dry-run behavior:** Prints evaluation and metrics.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Synthetic Review

*   **User-facing command:** `ws quant backtest synthetic-review` (Proposed) / `/quant backtest synthetic review` (Proposed)
*   **Underlying script:** `scripts/quant/synthetic_execution_cli.py review-synthetic`
*   **Read/write behavior:** Writes JSON review gate under `reports/quant/synthetic_result_reviews/`.
*   **Default dry-run behavior:** Prints evaluation.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Data Requirements

*   **User-facing command:** `ws quant data requirements` (Proposed) / `/quant data requirements` (Proposed)
*   **Underlying script:** `scripts/quant/backtest_preparation_cli.py data-requirements`
*   **Read/write behavior:** Writes JSON data req record under `reports/quant/backtest_data_requirements/`.
*   **Default dry-run behavior:** Prints draft.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Dataset Mapping

*   **User-facing command:** `ws quant dataset mapping` (Proposed) / `/quant dataset mapping` (Proposed)
*   **Underlying script:** `scripts/quant/backtest_preparation_cli.py dataset-mapping`
*   **Read/write behavior:** Writes JSON mapping stub under `reports/quant/dataset_mapping_stubs/`.
*   **Default dry-run behavior:** Prints stub draft.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.

## Quant Decision Packet

*   **User-facing command:** `ws quant decision packet` (Proposed) / `/quant decision packet` (Proposed)
*   **Underlying script:** `scripts/quant/backtest_preparation_cli.py decision-packet`
*   **Read/write behavior:** Writes JSON decision packet under `reports/quant/human_backtest_decisions/`.
*   **Default dry-run behavior:** Prints decision draft.
*   **Safety class:** `GUARDED_WRITE`
*   **Expected RAM/GPU usage:** < 100MB RAM, 0GB VRAM.
