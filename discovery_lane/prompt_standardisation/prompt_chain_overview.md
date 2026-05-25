# Prompt Chain Overview

This document explains the manual flow from a vague idea to actionable research reports.

## The Flow

```text
[ Vague Product Idea ]
         |
         v
[ Standardised Prompt 1 ]  <-- Discovery Interview
         |
         v
[ Batch Questioning ]      <-- Manual Interaction
         |
         v
[ Product Understanding Brief ]
         |
         v
[ Manual Review/Correction ]
         |
         v
[ Standardised Prompt 2 ]  <-- Phase Breakdown
         |
         v
[ Phase Map & Summaries ]
         |
         v
[ Manual Review/Correction ]
         |
         v
[ Standardised Prompt 3 ]  <-- Deep Research (Per Phase)
         |
         v
[ Deep Research Report ]   <-- Markdown Output
         |
         v
[ Save to discovery_lane/inbox/ ]
         |
         v
[ ws discovery ingest ]    <-- Workstation Discovery Lane Begins
```

## Explicit Boundaries

### Before Phase-wise Research Reports
- Human-led discovery in browser-based ChatGPT or Gemini.
- Manual correction of briefs and breakdowns.
- Deep Research is run manually (using LLM browser features).
- **No Workstation involvement.**

### After Phase-wise Research Reports
- `.md` files are placed into `discovery_lane/inbox/`.
- `ws discovery ingest` is run.
- Workstation generates phase packets and worker prompts.
- Discovery Lane pipeline proceeds through approval, handoff, and branch planning.

## Prompt Roles

| Prompt | Role | Key Output |
| :--- | :--- | :--- |
| **1** | Consultant / Analyst | Product Understanding Brief |
| **2** | Solution Architect | Phase Breakdown |
| **3** | Lead Researcher | Technical Research Report (.md) |

## Standardisation Goals

The goal of this kit is to ensure that the "thinking" stage is grounded, structured, and consistent before it ever reaches the local repository. This prevents scope creep, vague implementation plans, and architectural digressions.
