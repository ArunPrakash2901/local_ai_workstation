# Review Bucket Doctrine

This document outlines the three-bucket strategy for workstation artifacts, distinguishing between machine-readable contracts and human-oriented review surfaces.

## Bucket 1: Agent/Internal Contracts (Canonical Source)

- **Formats:** Markdown (`.md`), JSON (`.json`), YAML (`.yaml`).
- **Role:** The official source of truth for the workstation.
- **Consumers:** CLI tools, local models, agents, validators, and automation.
- **Characteristics:** Cheap to generate, fast to parse, deterministic, and version-controlled.
- **Examples:** Phase packets, worker prompts, manifests, branch plans, product packets.

## Bucket 2: Human Review Surfaces (Inspection)

- **Formats:** Static HTML (`.html`).
- **Role:** Optimized for human judgment, taste, and approval.
- **Consumers:** Human operators (Arun).
- **Characteristics:** Visual, easy to read, scannable, and highlighting key decisions/risks.
- **Constraint:** HTML is **never** the source of truth. It is a projection of Bucket 1.
- **Examples:** PRD review, wireframe review, implementation plan review.

## Bucket 3: Interactive Playgrounds (Judgment & Correction)

- **Formats:** Interactive HTML/JS (Future).
- **Role:** Allowing humans to "play" with requirements or designs.
- **Consumers:** Human operators.
- **Characteristics:** Drag-and-drop, commenting, side-by-side comparison, interactive adjustment.
- **Constraint:** Any decision made in Bucket 3 must be written back to Bucket 1 (e.g., as an amendment packet or approval record).
- **Status:** Future work.

## Implementation Rules

1. **Unidirectional Flow:** Artifacts flow from Bucket 1 to Bucket 2.
2. **Checksum Validation:** Every HTML review surface must record the checksum of its source Bucket 1 artifact.
3. **No Execution:** Review surfaces must not trigger any workstation side effects (execution, branching, git actions).
4. **Static by Default:** Bucket 2 artifacts should be self-contained static HTML with no external dependencies.
