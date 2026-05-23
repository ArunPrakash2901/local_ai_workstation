# Product Design Adapter Specification

## 1. Overview

This specification defines the interface and lifecycle for a **Product Design Adapter** (e.g., Open Design) within the Local AI Workstation. The adapter is responsible for transforming deterministic text-based UI specifications into visual designs, prototypes, and layout exports.

## 2. Adapter Inputs

The adapter consumes a **Design Prompt Packet** generated from the Product Lane artifacts.

**Required Source Artifacts:**
- `product.yaml`: For product type, label, and metadata.
- `scope_lock.md`: For functional boundaries.
- `prd.md`: For goals, target users, and detailed requirements.
- `wireframes/wireframe_v1.md`: For screen mapping, content hierarchy, and ASCII/Text layouts.

**Generated Input Artifacts (Design Packet):**
- `design_input.yaml`: Combined metadata for the design run.
- `design_prompt.md`: A structured prompt optimized for the target design tool (Open Design).

## 3. Adapter Outputs

The adapter must write all outputs into a dedicated sandbox directory.

**Target Directory:**
`products/<product_id>/design_runs/<tool_id>/<run_id>/`

**Expected Directory Structure:**
```text
products/<product_id>/design_runs/open_design/<run_id>/
  design_input.yaml     # Copy of inputs
  design_prompt.md      # Copy of inputs
  raw_output/           # Raw tool logs and diagnostic data
  prototype/            # Interactive HTML/CSS/JS or tool-specific prototype
  screenshots/          # Image captures of the design
  export/               # Structured exports (layout_spec.json, component_library.css)
  design_run.yaml       # Run metadata (duration, success/failure, tool version)
  validation.md         # Automated validation report
  operator_report.md    # Summary for human review
```

## 4. Run Lifecycle

1.  **Preparation:** Workstation verifies that the product has an approved PRD and confirmed Wireframe Spec.
2.  **Packaging:** Workstation creates the `design_input.yaml` and `design_prompt.md`.
3.  **Dispatch:** Workstation launches the Design Adapter (Open Design) process, passing the input paths and the sandboxed output root.
4.  **Execution:** The adapter processes the prompt and generates visual artifacts.
5.  **Completion:** The adapter writes `design_run.yaml` and exits.
6.  **Validation:** Workstation runs local checks on the output directory (presence of files, size limits, syntax validation).
7.  **Import:** The operator reviews the output and marks it as APPROVED via `ws product-design-approve`.

## 5. Allowed and Forbidden Actions

**Allowed Actions:**
- Reading the specified product artifacts.
- Writing to the product's `design_runs/` sandbox.
- Spawning local rendering processes (e.g., headless browser for screenshots).
- Calling local LLMs for design reasoning (if configured).

**Forbidden Actions:**
- Writing to `src/`, `app/`, `public/`, or other source directories.
- Modifying project dependencies (`package.json`, `requirements.txt`).
- Accessing secrets, `.env` files, or unrelated project files.
- Communicating with external domains unless explicitly allowlisted for design asset retrieval (e.g., font providers).

## 6. Output Validation

Automated validation must confirm:
- **Presence:** `prototype/index.html` (or equivalent) and `export/layout_spec.json` exist.
- **Safety:** No script tags in `export/` artifacts that escape the sandbox.
- **Integrity:** `design_run.yaml` contains valid timestamps and exit codes.
- **Size:** Individual artifacts do not exceed established limits (e.g., 5MB per screenshot).

## 7. Future MCP / Browser Integration

- **MCP Integration:** A dedicated Design MCP server could expose the Design Packet as a resource and provide tools for "render", "screenshot", and "export".
- **Browser Transport:** If the design tool requires a browser UI, the **Browser Transport Adapter** can be used to move the `design_prompt.md` to the tool and capture the resulting visual artifacts back into the sandbox.

## 8. Test Plan

- **Dry-run Test:** Verify `product-design-adapter-preview` generates the correct prompt text.
- **Sandbox Boundary Test:** Verify the adapter refuses to write to a path outside `design_runs/`.
- **Import Validation Test:** Verify `product-design-approve` only accepts validated design runs.
- **Artifact Freshness Test:** Verify the adapter refuses to run if the source PRD or Wireframe Spec is stale.
