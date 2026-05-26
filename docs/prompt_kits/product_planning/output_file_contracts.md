# Output File Contracts

This document defines the expected outputs from each prompt, their naming conventions, where they are saved, and the source-of-truth hierarchy that governs the entire planning-to-execution pipeline.

---

## Prompt 1 Outputs

Prompt 1 produces planning files only. These are **not workstation inputs**.

| File | Description | Destination |
|---|---|---|
| `product_source_of_truth.md` | Complete, deeply clarified product definition. | Saved locally. Do **not** place in `discovery_lane/inbox/`. |
| `phase_00_phase_index.md` | Master list of all phases with objectives, order, and dependencies. | Saved locally. Do **not** place in `discovery_lane/inbox/`. |
| `phase_NN_<slug>_context.md` | Per-phase scoping file. One file per phase. | Saved locally. Do **not** place in `discovery_lane/inbox/`. |

These files are **manual planning material**. They feed Prompt 2. They do not go to the workstation directly.

---

## Prompt 2 Outputs

Prompt 2 produces one Deep Research report per phase. These **are** workstation inputs.

| File | Description | Destination |
|---|---|---|
| `phase_NN_<slug>_research.md` | Phase-wise Deep Research report, workstation-ready. | **Place in** `discovery_lane/inbox/<set_id>/` |

---

## Naming Conventions

### Planning Files (Prompt 1 outputs — saved locally)

```
product_source_of_truth.md
phase_00_phase_index.md
phase_01_<slug>_context.md
phase_02_<slug>_context.md
phase_03_<slug>_context.md
...
```

### Research Reports (Prompt 2 outputs — placed in discovery_lane/inbox)

```
discovery_lane/inbox/<set_id>/phase_01_<slug>_research.md
discovery_lane/inbox/<set_id>/phase_02_<slug>_research.md
discovery_lane/inbox/<set_id>/phase_03_<slug>_research.md
...
```

### Slug Rules

- Use lowercase, underscored words only.
- Be descriptive but brief.
- Match the phase slug consistently between context and research files.

**Examples:**

| Phase | Context File | Research File |
|---|---|---|
| Phase 1 — Foundation | `phase_01_foundation_context.md` | `phase_01_foundation_research.md` |
| Phase 2 — Data Pipeline | `phase_02_data_pipeline_context.md` | `phase_02_data_pipeline_research.md` |
| Phase 3 — UI Shell | `phase_03_ui_shell_context.md` | `phase_03_ui_shell_research.md` |

### Set ID Rules

The `<set_id>` is a short, human-readable folder name for a product planning run.

**Examples:**

```
discovery_lane/inbox/product_alpha_v1/
discovery_lane/inbox/quant_dashboard_v2/
discovery_lane/inbox/portfolio_tracker_mvp/
```

Use a new `<set_id>` folder for each distinct product or major revision.

---

## Source-of-Truth Hierarchy

The following hierarchy governs which document takes precedence when conflicts arise.

| Level | Document | Notes |
|---|---|---|
| 1 | `product_source_of_truth.md` | Manual upstream spine. The canonical product definition. Governs all downstream documents. |
| 2 | `phase_00_phase_index.md` | Defines phase order, dependencies, and research requirements. |
| 3 | `phase_NN_<slug>_context.md` | Per-phase scoping document. Must not contradict Level 1 or 2. |
| 4 | `phase_NN_<slug>_research.md` | Deep Research report. Must not contradict Levels 1–3. |
| 5 | Discovery Lane–generated packets | Workstation manifests and packets produced after ingestion. |
| 6 | Execution / Exchange artifacts | Implementation artifacts and handoff artifacts produced during workstation execution. |

**Key principle:** The `product_source_of_truth.md` is the **manual upstream spine**. It does not change unless the operator explicitly decides to update it. Discovery Lane manifests become the workstation spine after ingestion, but they inherit their authority from the Source of Truth.

If a Deep Research report contradicts the Source of Truth, the Source of Truth wins. The report must be corrected before ingestion.

---

## Ingestion Trigger

The workstation ingestion starts only when **all required phase research reports** for a set are present in `discovery_lane/inbox/<set_id>/`.

```
ws discovery intake-set discovery_lane/inbox/<set_id>
ws discovery ingest-set <set_id>
ws discovery approve-set <set_id> --dry-run --write-report
```

Incomplete sets should not be ingested. If a phase is missing its research report, the operator should complete Prompt 2 for that phase before triggering intake.
