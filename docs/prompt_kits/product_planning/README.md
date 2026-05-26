# Product Planning Prompt Kit

## What This Is

This prompt kit is **manual and upstream**.

It is used in a **browser session** (ChatGPT or Gemini) before the local AI workstation starts. It does not run any local models. It does not call any APIs. It does not automate any browser. It does not create Discovery Lane packets. It does not execute anything on the workstation.

Its sole purpose is to produce **pristine, phase-wise Deep Research `.md` reports** — one per product phase — that are ready to enter the workstation's Discovery Lane.

Only those final Deep Research reports enter `discovery_lane/inbox/`.

---

## What This Is Not

- Not part of the automated workstation lane flow.
- Not a replacement for the Discovery Lane.
- Not a substitute for the Execution Lane, Exchange Lane, Runtime Lane, or Product Development Lane.
- Not automation tooling.
- Not a slash command or `ws` command.
- Not an HTML interface.
- Not a local model prompt.

---

## Full Upstream Flow

```
Vague idea
  │
  ▼
Standardised Prompt 1
(paste into ChatGPT / Gemini browser tab)
  │
  ▼
Question batches
(Intent → Product Behaviour → Workstation Execution)
  │
  ▼
Operator answers questions
  │
  ▼
Model outputs copyable Markdown files
  │
  ├── product_source_of_truth.md       ← manually saved locally (NOT in discovery_lane/inbox)
  ├── phase_00_phase_index.md          ← manually saved locally (NOT in discovery_lane/inbox)
  └── phase_NN_<slug>_context.md       ← manually saved locally (NOT in discovery_lane/inbox)
            (one file per phase)
  │
  ▼
For each phase:
  Open Deep Research mode in ChatGPT / Gemini
  Paste Standardised Prompt 2
  Insert product_source_of_truth.md + phase_NN context file
  Run Deep Research
  │
  ▼
Model outputs phase Deep Research report
  │
  ▼
Save as:
  discovery_lane/inbox/<set_id>/phase_NN_<slug>_research.md
  │
  ▼
Repeat Prompt 2 for each remaining phase
  │
  ▼
All phase research reports exist in discovery_lane/inbox/<set_id>/
  │
  ▼
────────────────────────────────────────────────
  WORKSTATION STARTS HERE
────────────────────────────────────────────────
  ws discovery intake-set discovery_lane/inbox/<set_id>
  ws discovery ingest-set <set_id>
  ws discovery approve-set <set_id> --dry-run --write-report
  ... (standard workstation flow continues)
```

---

## Key Boundary Rules

| Output | Where It Goes |
|---|---|
| `product_source_of_truth.md` | Saved locally, **NOT** placed in `discovery_lane/inbox/` |
| `phase_00_phase_index.md` | Saved locally, **NOT** placed in `discovery_lane/inbox/` |
| `phase_NN_<slug>_context.md` | Saved locally, **NOT** placed in `discovery_lane/inbox/` |
| `phase_NN_<slug>_research.md` (Prompt 2 output) | **Placed in** `discovery_lane/inbox/<set_id>/` |

Prompt 1 output is **planning material** — it feeds Prompt 2, not the workstation directly.

Prompt 2 output is **workstation-ready research** — it feeds `discovery_lane/inbox/`.

---

## Contents of This Prompt Kit

| File | Purpose |
|---|---|
| `README.md` | This file. Overview, flow, and boundaries. |
| `standardized_prompt_01_vague_idea_to_product_and_phases.md` | Copy-ready Prompt 1 for browser ChatGPT/Gemini. |
| `standardized_prompt_02_phase_context_to_deep_research_report.md` | Copy-ready Prompt 2 for Deep Research mode. |
| `output_file_contracts.md` | Naming conventions and source-of-truth hierarchy. |
| `no_digression_rules.md` | Reusable no-digression rule block for any prompt. |
| `example_manual_workflow.md` | Step-by-step operator walkthrough. |

---

## Design Principle

> Markdown first. Precision before automation. The workstation starts when the research is ready — not before.
