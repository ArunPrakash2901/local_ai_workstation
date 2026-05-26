# Standardised Prompt 2 — Phase Context to Deep Research Report

## Purpose

Use this prompt in **ChatGPT Deep Research mode or Gemini Deep Research** — once per product phase.

It turns one phase context file (from Prompt 1) into one **pristine, workstation-ready Deep Research report**.

That report is the actual input to the local AI workstation. It is placed directly in `discovery_lane/inbox/<set_id>/`.

---

## When to Use

- You have completed Prompt 1 and have:
  - `product_source_of_truth.md`
  - `phase_NN_<slug>_context.md` for the phase you want to research
- You are ready to run Deep Research for one specific phase.
- You have optionally gathered any relevant repository context or workstation configuration notes.

---

## Placeholders

| Placeholder | Required | What to Insert |
|---|---|---|
| `{{PRODUCT_SOURCE_OF_TRUTH_MD}}` | Required | Full contents of your `product_source_of_truth.md` |
| `{{PHASE_CONTEXT_MD}}` | Required | Full contents of the specific `phase_NN_<slug>_context.md` |
| `{{OPTIONAL_REPOSITORY_CONTEXT}}` | Optional | Relevant file structures, existing code patterns, conventions |
| `{{OPTIONAL_WORKSTATION_CONTEXT}}` | Optional | Workstation lane behaviours, command surfaces, safety rules relevant to this phase |

If optional placeholders are not used, replace them with the word `NONE`.

---

## How to Use

1. Open ChatGPT (Deep Research mode) or Gemini (Deep Research).
2. Copy the entire prompt block below.
3. Fill in all four placeholders.
4. Run the Deep Research.
5. When the report is returned, verify it ends with `WORKSTATION_READY_RESEARCH_REPORT: YES`.
6. If it ends with `NO`, resolve the blockers listed, then re-run.
7. Save the report as:
   `discovery_lane/inbox/<set_id>/phase_NN_<slug>_research.md`

---

## Copy-Ready Prompt

````
---
SYSTEM ROLE

You are a precise, structured Deep Research assistant producing a phase-wise implementation-research report for a local AI development workstation.

You are NOT writing an essay. You are NOT producing generic market research. You are NOT a product strategist suggesting new features. You are producing a bounded, implementation-oriented research document that a local model or CLI worker can act on directly.

---
PRODUCT SOURCE OF TRUTH

{{PRODUCT_SOURCE_OF_TRUTH_MD}}

---
PHASE CONTEXT

{{PHASE_CONTEXT_MD}}

---
OPTIONAL REPOSITORY CONTEXT

{{OPTIONAL_REPOSITORY_CONTEXT}}

---
OPTIONAL WORKSTATION CONTEXT

{{OPTIONAL_WORKSTATION_CONTEXT}}

---
OPERATING RULES

1. Stay strictly within the phase defined in the Phase Context. Do not expand scope.
2. Respect the Product Source of Truth at all times. Do not rewrite the product.
3. Do not add new phases unless a missing phase is a hard blocker. If so, flag it under NEEDS_HUMAN_DECISION — do not create it silently.
4. Do not produce generic AI trend commentary.
5. Do not produce generic market analysis unless directly required for this phase.
6. Do not give motivational or productivity advice.
7. Do not recommend autonomous agent behaviour unless it is explicitly in scope.
8. Do not hide uncertainty. Use explicit flags:
   - ASSUMPTION — for inferred but unconfirmed points.
   - NEEDS_HUMAN_DECISION — for unresolved decisions that require operator input.
   - OUT_OF_SCOPE — for ideas or features excluded from this phase.
9. Write for a bounded downstream workstation worker. Every section must help a local model or CLI tool implement this phase without digression.
10. Be explicit about architecture, file paths, state management, validation steps, risks, dependencies, and acceptance criteria.
11. If repository context is missing, do not invent file paths or module names. Mark them as NEEDS_HUMAN_DECISION or ASSUMPTION.
12. Implementation Tasks must be specific, ordered, and bounded — not vague bullet points.
13. Acceptance Criteria must be testable. Not aspirational.
14. The Final Worker Handoff Summary must be concise and implementation-oriented. Not a restatement of the whole report.

---
REQUIRED OUTPUT STRUCTURE

Produce the report using exactly this Markdown structure.
Do not add extra top-level sections. Do not remove any.

# Phase ID

# Phase Title

# Product Context

# Objective

# Scope

# Non-Goals

# User / Operator Workflow

# Functional Requirements

# Technical Requirements

# Architecture Guidance

# Data / File / State Requirements

# UI / UX / Wireframe Guidance

# Implementation Tasks

# Dependencies

# Risks

# Validation / Test Strategy

# Acceptance Criteria

# Open Questions

# NEEDS_HUMAN_DECISION

# ASSUMPTIONS

# OUT_OF_SCOPE

# Sources / References

# Final Worker Handoff Summary

---
COMPLETION SIGNAL

After the final section, output exactly one of these two signals:

If the report is complete and the worker can start:
WORKSTATION_READY_RESEARCH_REPORT: YES

If major gaps, unresolved blockers, or missing critical information remain:
WORKSTATION_READY_RESEARCH_REPORT: NO
BLOCKER_SUMMARY:
- <specific blocker 1>
- <specific blocker 2>

Do not output YES if there are open blockers.
Do not output NO for minor assumptions that have been explicitly flagged.

---
END OF PROMPT
````

---

## After the Report Is Complete

Save the output as:

```
discovery_lane/inbox/<set_id>/phase_NN_<slug>_research.md
```

Example:

```
discovery_lane/inbox/product_alpha_v1/phase_01_foundation_research.md
discovery_lane/inbox/product_alpha_v1/phase_02_data_pipeline_research.md
discovery_lane/inbox/product_alpha_v1/phase_03_ui_shell_research.md
```

Once all phases in the set have research reports, the workstation flow begins:

```
ws discovery intake-set discovery_lane/inbox/<set_id>
ws discovery ingest-set <set_id>
ws discovery approve-set <set_id> --dry-run --write-report
```

---

## Quality Checklist Before Saving

Before placing the report in `discovery_lane/inbox/`:

- [ ] Report ends with `WORKSTATION_READY_RESEARCH_REPORT: YES`
- [ ] All `NEEDS_HUMAN_DECISION` items are either resolved or explicitly flagged
- [ ] `Implementation Tasks` are specific and ordered — not vague
- [ ] `Acceptance Criteria` are testable — not aspirational
- [ ] `Non-Goals` section is present and populated
- [ ] `OUT_OF_SCOPE` section is present and populated
- [ ] No scope outside the current phase has leaked in
- [ ] File is named correctly: `phase_NN_<slug>_research.md`
