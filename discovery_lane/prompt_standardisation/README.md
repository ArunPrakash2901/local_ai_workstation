# Manual Pre-Workstation Prompt Kit

This directory contains manual documentation and standardised prompts for the product discovery and research phase.

## Purpose

Discovery Lane v1.3 standardises the thinking chain that happens **before** any workstation CLI commands are run.

- These prompts are for manual use in ChatGPT or Gemini.
- No workstation execution, local models, or CLI workers are involved at this stage.
- Only the final outputs of **Standardised Prompt 3** enter the workstation pipeline as `.md` reports in `discovery_lane/inbox/`.

## Manual Prompt Flow

1. **Standardised Prompt 1: Vague Idea Discovery Interview**
   - Input: Vague product idea.
   - Flow: Batch questioning to narrow ambiguity.
   - Output: **Product Understanding Brief** (Manual review/correction).

2. **Standardised Prompt 2: Product Understanding to Phase Breakdown**
   - Input: Corrected Product Understanding Brief.
   - Flow: Logical decomposition into bounded implementation phases.
   - Output: **Phase Breakdown** and **Phase Summaries**.

3. **Standardised Prompt 3: Phase Summary to Deep Research Report**
   - Input: Individual phase summary + Product Context.
   - Flow: Deep Research (manual) to produce technical implementation details.
   - Output: **Phase-wise Research Report Markdown** (Saved to `discovery_lane/inbox/`).

## Implementation Boundary

| Phase | Tooling | Workstation Involvement |
| :--- | :--- | :--- |
| **Discovery Interview** | ChatGPT / Gemini | None |
| **Phase Breakdown** | ChatGPT / Gemini | None |
| **Deep Research** | ChatGPT / Gemini | None |
| **Ingestion** | `ws discovery ingest` | Discovery Lane begins here |

For more details, see [Prompt Chain Overview](prompt_chain_overview.md).
