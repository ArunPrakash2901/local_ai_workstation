# Open Design Integration Plan

## 1. Objective

Visual design and UI/UX prototyping are non-deterministic, creative tasks that benefit from specialized rendering and spatial manipulation tools rather than raw LLM text generation or simple ASCII templates. While the Product Lane successfully defines *what* should be on a screen (specifications), an interactive design tool like **Open Design** (or similar design/prototyping adapters) is required to realize *how* it looks and feels.

The objective is to integrate Open Design as a controlled **Design Adapter** within the Local AI Workstation, allowing for high-fidelity visual prototyping without sacrificing the deterministic safety and human-gated workflows of the Product Lane.

## 2. Integration Principle: Deterministic Spec -> Visual Adapter

- **Product Lane remains the Source of Truth:** The Product Lane defines the PRD, scope lock, and wireframe *requirements* (components, hierarchy, navigation) in deterministic markdown/YAML.
- **Design Adapter is a Sandbox:** The Design Adapter (Open Design) consumes these specifications and generates a visual render/prototype.
- **Human-in-the-loop:** Design outputs are treated as "proposed artifacts" that must be reviewed and approved by the operator before moving to technical planning or implementation.
- **Sandboxed Execution:** The adapter operates in a strictly controlled directory and does not mutate the application source code directly.

## 3. Proposed Workflow

1.  **Approved active PRD:** The Product Lane has an approved PRD.
2.  **Confirmed Wireframe Spec:** The deterministic `wireframe_v1.md` (or similar) defines the screen map and components.
3.  **Design Adapter Preview:** The workstation packages the PRD and Wireframe Spec into a "Design Packet" for the adapter.
4.  **Open Design Sandbox Render:** The adapter (Open Design) generates visual layouts, CSS, or interactive prototypes in a sandboxed run directory.
5.  **Design Review:** The operator reviews the visual output against the original PRD and Wireframe Spec.
6.  **Design Approval:** The operator approves a specific design run, marking it as the "active design artifact."
7.  **Technical Plan / Implementation:** Technical planning consumes the approved visual artifacts (CSS, layout specs, screenshots) as inputs for implementation.

## 4. Sandboxed Output Policy

All design outputs must be confined to a product-specific design run directory:
`products/<product_id>/design_runs/open_design/<run_id>/`

**Prohibited Actions:**
- Writing directly into `src/`, `app/`, or other source code directories.
- Modifying `package.json` or project configurations.
- Overwriting existing approved design artifacts without a new run.

## 5. Proposed Commands (Planned, Not Implemented)

- `ws product-design-adapter-preview --product <id> --tool open-design --dry-run`
    - Previews the "Design Packet" that would be sent to the adapter.
- `ws product-design-render --product <id> --tool open-design --confirm`
    - Dispatches the task to the adapter to generate visual artifacts.
- `ws product-design-review --product <id> --dry-run`
    - Displays a summary of the latest design run and links to visual artifacts for human review.
- `ws product-design-approve --product <id> --confirm`
    - Marks a specific design run as approved and updates `product.yaml`.

## 6. Safety Classifications

Using current Workstation safety classes:

| Command | Classification | Rationale |
| :--- | :--- | :--- |
| `product-design-adapter-preview` | `DRY_RUN_ONLY` | Pure read of specs; prints preview. |
| `product-design-render` | `GUARDED_WRITE` / `PROVIDER_CALL` | Writes to sandbox; potentially calls a model/tool. |
| `product-design-review` | `DRY_RUN_ONLY` | Pure read of design run artifacts. |
| `product-design-approve` | `GUARDED_WRITE` | Updates `product.yaml` metadata and action log. |

## 7. Open Design Evaluation Questions

Before full adoption, the following must be verified:
- **Environment:** Does it support Windows/WSL? What are the Node.js/Python requirements?
- **Interface:** Is there a stable CLI? Can it be driven by structured JSON/Markdown artifacts?
- **Connectivity:** Can it run fully local? Does it require external API keys or cloud models?
- **Sandboxing:** Can it be restricted to a specific output directory? Does it attempt to run `npm install` or other side-effect-heavy commands?
- **Output:** What formats does it produce (HTML/CSS, Figma-like JSON, Screenshots)? Are they usable by implementation agents?
- **MCP Support:** Is there an existing Model Context Protocol server for it?
- **Maintenance:** Is the project actively maintained and safely licensed?

## 8. Design Artifact Model (product.yaml)

New metadata fields for `product.yaml`:

```yaml
active_design_run: "open_design/run_20260523T100000Z"
active_design_artifact: "products/<id>/design_runs/open_design/<run_id>/export/layout_spec.json"
active_design_hash: "sha256:..."
design_tool: "open-design"
design_status: "APPROVED" # DRAFTED, REVIEWED, APPROVED, REJECTED
design_created_at: "2026-05-23T10:00:00Z"
design_reviewed_at: "2026-05-23T11:00:00Z"
design_approved_at: "2026-05-23T11:05:00Z"
```

## 9. Review Policy

The Design Review must evaluate the output against:
- **Active Scope:** Does it include features outside the scope lock?
- **Active PRD:** Does it meet the functional goals and target audience needs?
- **Confirmed Wireframe:** Does it follow the established hierarchy and screen map?
- **Accessibility:** Are there clear indicators of focus, contrast, and semantic structure?
- **Responsiveness:** Does the design account for mobile/desktop layout shifts?

## 10. Relationship to Exchange Lane

Future visual design tools should communicate via the **Exchange Lane**. 

Instead of manual design execution:
1.  Product Lane generates an **Exchange Handoff Packet**.
2.  The **Design Adapter** (Open Design) consumes the packet.
3.  Results are imported back into the workstation as **Exchange Results**.
4.  Product Lane promotes the validated result to an "Approved Design" artifact.

This ensures design runs are traceable, reproducible, and safely isolated from the main implementation flow.
