# Open Design Local Evaluation Report

## Purpose
This document defines the local evaluation scope for Open Design integration in the workstation.
The goal is to assess whether Open Design can be used as a downstream visual design adapter with strict safety boundaries.

## Role In Workstation Architecture
- Open Design is a downstream design adapter candidate.
- Product Lane artifacts (scope, PRD, wireframe, technical plan) remain source-of-truth.
- Open Design outputs are future derived artifacts, not Product Lane authoritative records.

## Current Status (This Phase)
- Open Design installed: `NO`
- Open Design executed: `NO`
- External repository clone performed: `NO`
- Integration in this phase: dry-run preview only
- Current runtime readiness: `PARTIAL_RUNTIME_FOUND`
- Prepared packet present: `YES`

## Official Runtime Requirements (Verified)
- Official quickstart currently requires `Node.js 24`.
- Official quickstart currently requires `pnpm 10.33.2` via Corepack.
- Official quickstart currently requires `git`.
- Official quickstart expects a local coding-agent CLI on `PATH` for agent-backed generation, with BYOK fallback documented in Open Design.
- Official quickstart uses:
  - `git clone https://github.com/nexu-io/open-design`
  - `pnpm install`
  - `pnpm tools-dev`
- Official troubleshooting notes call out Windows `better-sqlite3` builds and recommend Visual Studio Build Tools if that dependency hangs.

## Current Workstation State
- `node -v`: `v22.17.0`
- `npm -v`: `11.6.1`
- `corepack --version`: `0.33.0`
- `pnpm`: `NOT_FOUND`
- `open-design`: `NOT_FOUND`
- `od`: `NOT_FOUND`
- Runtime blocker summary:
  - Node is present but the major version is below the current documented requirement.
  - pnpm is not yet available on `PATH`.
  - Open Design is not yet installed on `PATH`.

## Recommended Install Boundary
- Recommended evaluation root: `D:\open_design_eval\open-design`
- Reason:
  - outside `_ai_brain`
  - outside app/source repositories
  - allows Open Design runtime state such as `.od/` to stay isolated from workstation source trees
  - keeps any future package-manager writes, caches, and daemon-managed state in a dedicated non-product folder
- Do not install inside:
  - `D:\_ai_brain`
  - `D:\portfolio_website`
  - any application repository intended for source control

## Integration Assumptions
- Future design runs must be sandboxed under:
  - `products/<product_id>/design_runs/open_design/<run_id>/`
- Design adapter inputs should be derived from approved Product Lane artifacts only.
- Product metadata should not be updated during render preview.
- Open Design installation and daemon state should remain outside app/source repositories.

## Items To Verify Later
- install/runtime requirements (`VERIFIED_FOR_CURRENT_PUBLIC_DOCS`)
- Windows native support (`TO_VERIFY`)
- WSL support (`BLOCKED_BY_HOST_PERMISSION_ERROR`)
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

## Wrapper Evaluation
- Direct Python dry-run command surfaces pass:
  - `python scripts\ws_product_design_runtime_probe.py --tool open-design --dry-run`
  - `python scripts\ws_product_design_runtime_report.py --tool open-design --dry-run`
  - `python scripts\ws_product_design_install_checklist.py --tool open-design --dry-run`
- Plain `ws ...` was not available in the current PowerShell session because no `ws` alias/function/script was on `PATH`.
- `powershell -ExecutionPolicy Bypass -File scripts\ws.ps1 ...` reached the wrapper but failed at the WSL bridge with:
  - `Wsl/Service/CreateInstance/E_ACCESSDENIED`
- Safe fallback today:
  - use the direct Python wrapper commands above for dry-run evaluation
  - do not change `scripts/ws` or `scripts/ws.ps1` in this slice

## Approval Boundary
- No install was attempted in this evaluation slice.
- Node replacement/upgrade was not attempted.
- pnpm enablement via Corepack was not attempted.
- Open Design clone/install was not attempted.
- Network access and package-manager execution remain blocked pending explicit approval.

## Next Evaluation Step
If explicit approval is granted later, the next safe sequence is:
1. Install Node 24 or switch the active Node runtime to 24.
2. Enable the pinned pnpm version through Corepack.
3. Clone Open Design into `D:\open_design_eval\open-design`.
4. Install dependencies there only.
5. Re-run the workstation dry-run probe and runtime report.
6. Stop before any render or agent-backed design execution.
