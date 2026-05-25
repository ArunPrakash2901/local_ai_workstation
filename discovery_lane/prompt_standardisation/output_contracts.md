# Output Contracts

This document defines the expected outputs for each standardised prompt and their destination.

## Prompt 1: Discovery Interview

- **Primary Output:** Product Understanding Brief.
- **Format:** Structured text/Markdown.
- **Destination:** Manual review only. **Do NOT place into the workstation repository.**
- **Goal:** Align human and LLM understanding of the "what" and "why".

## Prompt 2: Phase Breakdown

- **Primary Output:** Phase Breakdown and Phase Summaries.
- **Format:** Structured text/Markdown.
- **Destination:** Manual review only. **Do NOT place into the workstation repository.**
- **Goal:** Logical decomposition of the product into manageable technical blocks.

## Prompt 3: Deep Research Report

- **Primary Output:** Phase-wise Research Report.
- **Format:** Markdown (`.md`) file.
- **Destination:** **Save as file and place in `discovery_lane/inbox/`.**
- **Recommended Filename:** `<phase_id>_<phase_slug>_research.md` (e.g., `phase_01_foundation_research.md`).
- **Goal:** Provide enough implementation detail for the Discovery Lane pipeline to ingest and create worker-ready packets.

## Pipeline Integration

Only the outputs of **Prompt 3** enter the Discovery Lane pipeline. 

| Prompt | Workstation Involvement | Pipeline Status |
| :--- | :--- | :--- |
| Prompt 1 | None | Pre-Pipeline |
| Prompt 2 | None | Pre-Pipeline |
| Prompt 3 | Final Output Only | Ingestion Trigger |
| `ws discovery ingest` | Automatic Processing | Pipeline Start |
