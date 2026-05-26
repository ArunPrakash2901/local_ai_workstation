# Example Manual Workflow

This document walks through a complete end-to-end operator session using both standardised prompts. It shows exactly what happens at each step, what is saved, and where.

The workstation automation starts only at **Step 12**.

---

## Assumed Starting Point

- You have a vague product idea.
- You have this prompt kit open.
- You have a ChatGPT or Gemini browser session ready.
- Your local AI workstation repository (`D:\_ai_brain`) is available.
- The `discovery_lane/inbox/` folder exists and is writeable.

---

## Step-by-Step Walkthrough

---

### Step 1 — Open a browser session

Open [ChatGPT](https://chat.openai.com) or [Gemini](https://gemini.google.com) in your browser.

Use a fresh conversation. Do not carry over context from unrelated sessions.

---

### Step 2 — Paste Standardised Prompt 1

Open `standardized_prompt_01_vague_idea_to_product_and_phases.md`.

Copy the entire prompt block from the `Copy-Ready Prompt` section.

Paste it into the browser session.

---

### Step 3 — Insert your vague idea

Replace `{{VAGUE_IDEA}}` with your actual idea. Keep it honest and rough — do not over-refine it at this stage.

**Example:**

> I want to build something that helps me track and compare different quant trading strategies I am running. I keep losing track of which ones are active, which ones are in paper trading, and what their performance looks like.

Send the message.

---

### Step 4 — Answer question batches

The model will return structured question batches across three layers:

- **Intent Layer** — Why this product? Who is it for? What does success look like?
- **Product Behaviour Layer** — What does the product actually do? What data? What workflows?
- **Workstation Execution Layer** — How should it be phased? What does each phase prove?

Answer each batch honestly. It is acceptable to say "I don't know yet" — the model will flag it under `NEEDS_HUMAN_DECISION`.

After each batch, the model will output a summary block:

```
UNDERSTOOD SO FAR: ...
STILL UNCLEAR: ...
FORMING ASSUMPTIONS: ...
NEEDS HUMAN DECISION: ...
```

Read the summary. Correct anything that is wrong. Continue until you are satisfied.

---

### Step 5 — Trigger output generation

When the questioning feels complete and the product intent is stable, say:

> **Generate the product and phase files.**

The model will output copyable Markdown file blocks.

If the product has many phases, the model may split output across multiple turns. Follow its instructions (e.g., "Say CONTINUE PHASE FILES 1-3").

---

### Step 6 — Save the planning files locally

Copy each output file and save it. These files go to a local folder of your choice — **not** inside `discovery_lane/inbox/`.

**Suggested local save location:**

```
D:\_ai_brain\docs\prompt_kits\product_planning\sessions\<product_name>\
```

**Files to save:**

```
product_source_of_truth.md
phase_00_phase_index.md
phase_01_<slug>_context.md
phase_02_<slug>_context.md
phase_03_<slug>_context.md
...
```

None of these go into `discovery_lane/inbox/`.

---

### Step 7 — Open a Deep Research session for Phase 1

Open a new session in **ChatGPT (Deep Research mode)** or **Gemini (Deep Research)**.

Do not use a standard chat session for this step. Deep Research mode is required.

---

### Step 8 — Paste Standardised Prompt 2

Open `standardized_prompt_02_phase_context_to_deep_research_report.md`.

Copy the entire prompt block from the `Copy-Ready Prompt` section.

Paste it into the Deep Research session.

---

### Step 9 — Fill in the placeholders

Replace each placeholder with the appropriate content:

| Placeholder | Insert |
|---|---|
| `{{PRODUCT_SOURCE_OF_TRUTH_MD}}` | Full contents of `product_source_of_truth.md` |
| `{{PHASE_CONTEXT_MD}}` | Full contents of `phase_01_<slug>_context.md` |
| `{{OPTIONAL_REPOSITORY_CONTEXT}}` | Any relevant file structure, patterns, or conventions from your repo. Replace with `NONE` if not applicable. |
| `{{OPTIONAL_WORKSTATION_CONTEXT}}` | Any relevant workstation lane rules, command surfaces, or safety notes. Replace with `NONE` if not applicable. |

Send the message and start the Deep Research run.

---

### Step 10 — Run Deep Research and review the report

The model will conduct Deep Research and return a structured report.

**Before saving, check:**

- [ ] The report ends with `WORKSTATION_READY_RESEARCH_REPORT: YES`
- [ ] All `NEEDS_HUMAN_DECISION` items are either resolved or explicitly flagged for later
- [ ] `Implementation Tasks` are specific and ordered — not vague
- [ ] `Acceptance Criteria` are testable — not aspirational
- [ ] The report scope has not leaked outside Phase 1
- [ ] `Non-Goals` and `OUT_OF_SCOPE` sections are present and populated

If the report ends with `WORKSTATION_READY_RESEARCH_REPORT: NO`, resolve the listed blockers and re-run.

---

### Step 11 — Save the research report to discovery_lane/inbox

Create a set folder if it does not yet exist:

```
discovery_lane/inbox/<set_id>/
```

**Example:**

```
discovery_lane/inbox/quant_strategy_tracker_v1/
```

Save the report as:

```
discovery_lane/inbox/quant_strategy_tracker_v1/phase_01_<slug>_research.md
```

**Repeat Steps 7–11 for every remaining phase.**

For Phase 2, use `phase_02_<slug>_context.md` as the `{{PHASE_CONTEXT_MD}}` input. And so on.

---

### Step 12 — Trigger workstation flow

> **This is where the workstation automation begins. Nothing before this step involves the workstation.**

Once all required phase research reports are saved in `discovery_lane/inbox/<set_id>/`, start the workstation flow:

```
ws discovery intake-set discovery_lane/inbox/<set_id>
```

Then continue with the standard Discovery Lane sequence:

```
ws discovery ingest-set <set_id>
ws discovery approve-set <set_id> --dry-run --write-report
```

From this point, Discovery Lane, Execution Lane, Exchange Lane, and the rest of the workstation pipeline operate normally.

---

## Summary of What Goes Where

| Output | Saved Where | Enters Workstation? |
|---|---|---|
| `product_source_of_truth.md` | Local planning folder | No |
| `phase_00_phase_index.md` | Local planning folder | No |
| `phase_NN_<slug>_context.md` | Local planning folder | No |
| `phase_NN_<slug>_research.md` | `discovery_lane/inbox/<set_id>/` | **Yes — via `ws discovery intake-set`** |

---

## Notes

- You can run Prompt 2 for phases in any order, but ensure all required phases for a set are complete before running `ws discovery intake-set`.
- If you revise the product mid-planning, update `product_source_of_truth.md` first, then regenerate affected phase context files, then re-run Prompt 2 for affected phases.
- Do not ingest a partial set unless the Discovery Lane explicitly supports partial ingestion for your workflow.
- Keep your planning files versioned or dated if you run multiple iterations of the same product.
