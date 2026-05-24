# Open Design Local Evaluation Report

## Purpose
This document defines the local evaluation scope for Open Design integration in the workstation.
The goal is to assess whether Open Design can be used as a downstream visual design adapter with strict safety boundaries.

## Role In Workstation Architecture
- Open Design is a downstream design adapter candidate.
- Product Lane artifacts (scope, PRD, wireframe, technical plan) remain source-of-truth.
- Open Design outputs are future derived artifacts, not Product Lane authoritative records.

## Current Status (This Phase)
- Open Design installed: `NO` (`TO_VERIFY`)
- Open Design executed: `NO`
- External repository clone performed: `NO`
- Integration in this phase: dry-run preview only

## Integration Assumptions
- Future design runs must be sandboxed under:
  - `products/<product_id>/design_runs/open_design/<run_id>/`
- Design adapter inputs should be derived from approved Product Lane artifacts only.
- Product metadata should not be updated during render preview.

## Items To Verify Later
- install/runtime requirements (`TO_VERIFY`)
- Windows native support (`TO_VERIFY`)
- WSL support (`TO_VERIFY`)
- CLI availability and stable command surface (`TO_VERIFY`)
- output formats and determinism characteristics (`TO_VERIFY`)
- bounded output directory enforcement (`TO_VERIFY`)
- external model/provider service usage behavior (`TO_VERIFY`)
- local-only execution support (`TO_VERIFY`)
- MCP usage/support behavior (`TO_VERIFY`)
- Markdown/YAML artifact consumption compatibility (`TO_VERIFY`)
- strict write-boundary compliance:
  - `products/<id>/design_runs/open_design/<run_id>/` only (`TO_VERIFY`)

## Risks
- uncontrolled writes outside sandbox
- visual output drifting from approved PRD/wireframe intent
- hidden external calls during tool execution
- dependency/toolchain bloat on workstation
- weak or inconsistent Windows support

## Next Evaluation Step
Future manual local install and runtime assessment in a dedicated evaluation slice.
This step is intentionally out of scope for the current implementation.
