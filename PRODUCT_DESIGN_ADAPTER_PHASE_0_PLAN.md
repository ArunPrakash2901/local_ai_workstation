# Product Design Adapter: Phase 0 Implementation Plan

## 1. Rationale: Post-Wireframe Visual Bridge

The **Product Lane** is responsible for the deterministic definition of the product. By the time a wireframe is confirmed, the system has established:
- **Functional Scope:** What the product does (Scope Lock).
- **Core Requirements:** User goals and features (PRD).
- **Structural Layout:** Screen maps and component hierarchy (Wireframe).

The **Product Design Adapter** (specifically integrating **Open Design**) acts as a downstream visual adapter. It translates these deterministic specifications into high-fidelity visual prototypes. This separation ensures that the core product logic remains tool-agnostic and safe, while allowing specialized design tools to handle visual aesthetics, CSS generation, and interactive feedback within a strictly controlled sandbox.

## 2. Phase 0 Implementation Scope

Phase 0 is a **documentation and dry-run-only** slice. It focuses on the bridge logic and verification of source artifacts without executing external design tools.

**Primary Command Target:**
`ws product-design-adapter-preview --product <id> --tool open-design --dry-run`

**Constraints for Phase 0:**
- **NO** design rendering or visual generation.
- **NO** execution of the Open Design tool.
- **NO** external tool or model execution.
- **NO** browser automation or MCP interaction.
- **NO** mutation of any product artifacts (read-only).
- **NO** filesystem writes outside of the command's own logging/stdout.

## 3. Required Inputs for Design Generation

Before a design run can be simulated or previewed, the following artifacts and states must be validated:

| Artifact | Status / Property | Rationale |
| :--- | :--- | :--- |
| **Active Scope Lock** | Path & SHA-256 Hash | Ensures design is bound by the locked scope. |
| **Active PRD** | `status: APPROVED` | Ensures the design aligns with approved requirements. |
| **Active Wireframe** | `review: PASS` | Ensures the design follows the structural blueprint. |
| **Product Metadata** | `product.yaml` | Provides the product ID, label, and type. |
| **Technical Plan** | (Optional) | If available, provides implementation constraints. |

## 4. Phase 0 Preview Output (Dry-Run)

The `product-design-adapter-preview --dry-run` command must output a structured summary:

- **Product Identity:** `product_id`, `product_label`.
- **Tool Selection:** `tool=open-design`.
- **Artifact Audit:**
    - `active_scope_lock`: Path, Hash, Status.
    - `active_prd`: Path, Hash, Status (MUST be APPROVED).
    - `active_wireframe`: Path, Hash, Status (MUST be PASS).
- **Target Sandbox:** `products/<product_id>/design_runs/open_design/<run_id>/`.
- **Simulated Input Files:**
    - `design_input.yaml`: Serialized metadata for the adapter.
    - `design_prompt.md`: Structured markdown prompt for Open Design.
    - `design_run.yaml`: Initial metadata for the run (pending).
- **Policy Enforcement:**
    - **Allowed Writes:** List of expected files in the sandbox.
    - **Forbidden Actions:** Writing to `src/`, `app/`, `package.json`, etc.
- **Next Step Instructions:** `ws product-design-render --product <id> --confirm`.

## 5. Safety Classification Proposal

| Command | Classification | Rationale |
| :--- | :--- | :--- |
| `ws product-design-adapter-preview --dry-run` | `DRY_RUN_ONLY` | Purely informational; validates state and prints intent. |
| `ws product-design-render --confirm` | `GUARDED_WRITE` | Writes to a sandboxed directory; potentially calls external tools. |
| `ws product-design-review --dry-run` | `DRY_RUN_ONLY` | Summarizes contents of a design run for human review. |
| `ws product-design-approve --confirm` | `GUARDED_WRITE` | Updates `product.yaml` to promote a design run to "Active". |

## 6. Sandbox Policy

To maintain workstation integrity, the **Design Sandbox** is strictly enforced:

- **Root:** `products/<product_id>/design_runs/open_design/<run_id>/`
- **Isolation:** The adapter must NOT have write access to any directory outside its assigned `<run_id>` folder.
- **No Side-Effects:** The design process must not trigger builds, install packages, or modify environment configurations.

## 7. Test Plan for Phase 0

Tests must verify the robustness of the bridge logic:
1.  **Artifact Integrity:** Verify the command fails if hashes for Scope Lock, PRD, or Wireframe are missing or mismatched.
2.  **State Gating:** Verify the command fails if PRD status is not `APPROVED` or Wireframe review is not `PASS`.
3.  **Tool Validation:** Verify the command fails if an unsupported tool (other than `open-design`) is requested.
4.  **No-Write Verification:** Verify that `--dry-run` does not create any files or directories.
5.  **Sandbox Path Generation:** Verify that the generated output paths correctly follow the `products/<id>/design_runs/...` pattern.
6.  **Path Safety:** Verify that generated paths do not attempt to use `..` or other traversal techniques.

## 8. Future Phases

- **Phase 1:** Implement `product-design-adapter-preview --dry-run` logic and CLI route.
- **Phase 2:** Open Design Tool Evaluation (Installation, CLI capabilities, and sandboxing report).
- **Phase 3:** Implement `product-design-render --confirm` (Sandbox execution of Open Design).
- **Phase 4:** Implement `product-design-review --dry-run` (Summary of visual outputs).
- **Phase 5:** Implement `product-design-approve --confirm` (Artifact promotion).
- **Phase 6:** Technical Planning & Code Generation integration using the approved design artifacts.
