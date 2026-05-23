# Local AI Workstation Current State and Next Queue

**Date:** 2026-05-23  
**Project Root:** `D:\_ai_brain`

## 1. Executive Summary

The Local AI Workstation has successfully transitioned from an ad-hoc collection of scripts into a professional, multi-lane development control plane. It now features **hard-gated safety manifests**, **deterministic artifact lineage**, and **explicit state machines** for product development, exchange orchestration, and runtime management.

Work is organized into distinct **Lanes** that prioritize safety and auditability. The workstation's operating model ensures that the operator is the decision-maker, while automated adapters handle the structured transport of data between the workstation and various AI models. 

This report serves as the canonical map for the operator to navigate the current system state and understand the priority of the upcoming queue.

## 2. Current Lane Status Table

| Lane | Status | What exists | Current blocker / next action | Safe command examples |
|---|---|---|---|---|
| **Foundation & Safety** | **DONE** | Safety manifest (`ws_command_safety.yaml`), Command matrix, `check_local_safety.py` | None; manifest must be updated for all new commands | `python scripts/check_local_safety.py` |
| **TUI / Cockpit** | **DONE** | Home, Learning, Artifacts, System screens; Read-only framing | Polish Product Lane integration | `ws tui --plain` |
| **Product Lane** | **CURRENT** | Intake, Scope Revision, PRD (Rev), Wireframe, Tech Plan Gate | Tech Plan implementation (`--confirm`) | `ws product-prd-status --product portfolio-website-redesign` |
| **Exchange Lane** | **CURRENT** | Packet schema, Registry, Dispatch dry-run, Result Import, Adapter Preview | Codex `REVIEW_ONLY` guarded dispatch | `ws exchange-list` |
| **Runtime / Sessions** | **CURRENT** | Session registry, One-shot process planning, Start/Cleanup previews | `session-start --confirm` (One-shot mode) | `ws session-list` |
| **Design Adapter** | **NEXT** | Open Design sandbox planning | Integrate wireframes with rendering tools | *Planning Phase* |
| **Local Model Workers** | **LATER** | Ollama integration (`hermes3:8b`), Tutor/Assessor logic | Full integration with Exchange/TUI | `ws warm` |
| **Browser / MCP** | **LATER** | Packet redaction, Escalation gates | Browser transport adapter (Phase 3 Exchange) | `ws redact <packet>` |
| **Quant Lane** | **LATER** | Trading-research stronghold templates | Research-only paper analysis | `ws stronghold-status` |

## 3. Current Real Product State (portfolio-website-redesign)

The primary implementation product is currently in the **Technical Planning** transition.

- **Active Scope:** `scope_locks/scope_lock_v2.md` (Hash MATCH)
- **Active PRD:** `prds/prd_v2.md` (**APPROVED**, 2026-05-22)
- **Wireframe State:** **DRAFTED** (`wireframes/wireframe_v1.md`, 2026-05-23)
- **PRD Approval State:** **APPROVED**
- **Tech Plan State:** Gate previewed; `dry-run` PASS.
- **Next Product Action:** `ws product-wireframe-review --product portfolio-website-redesign --dry-run` followed by Technical Plan confirmation.

## 4. Current Planned Sessions

The runtime layer is prepared for controlled model execution. No processes should be started until `session-start --confirm` is validated.

- **`codex_product_lane`**: Managed session for Codex implementation tasks sourced from Product Lane.
- **`gemini_product_lane`**: Managed session for Gemini planning and review tasks.
- **`codex_exchange_lane`**: Managed session for Exchange Lane packet orchestration.

## 5. Exchange Lane State

The Exchange Lane provides the structured bus for all external reasoning.

- **Built:** Packet creation (`ws exchange-new`), Registry, Dispatch dry-run, Result import, Adapter preview.
- **Active:** Codex `REVIEW_ONLY` guarded dispatch path implementation. This allows the workstation to send packets to Codex without granting unrestricted shell access.
- **Missing:** Real execution dispatch (Phase 1), automated validation (Phase 2), and browser transport (Phase 3).

## 6. Safe Parallel Work Policy

To maintain the deterministic integrity of the workstation:

1. **Safety Core Serialization:** Only one lane should edit `scripts/ws`, `registry/ws_command_safety.yaml`, `WS_COMMAND_SAFETY_MATRIX.md`, or `check_local_safety.py` at a time.
2. **Docs/Planning Parallelism:** Documentation and planning tasks are always parallel-safe.
3. **Execution vs. Implementation:** Real product write smoke tests (`--confirm`) must not run while the implementation code for that specific lane is being modified.
4. **Lane Serialization:** Implementation work in `session`, `exchange`, and `product` lanes should be serialized unless they are working on purely independent helper modules.

## 7. Next Queue

### Immediate NEXT
- **Product technical plan confirmation/review implementation.**
- **Open Design integration planning** (Connecting wireframes to Figma/local tools).
- **Workstation current-state upkeep** (Safety manifest synchronization).

### Soon
- **Design adapter preview** (Rendering ASCII wireframes in a visual sandbox).
- **Session-start confirm** (Initial one-shot process execution).
- **Gemini CLI adapter preview** (Enabling multi-model reasoning exchange).

### Later
- **Browser ChatGPT/Gemini automation** (Phase 3 Exchange transport).
- **MCP layer** (Resource/tool exposure to external agents).
- **Local model worker execution** (Autonomous tutoring/assessment).
- **Implementation code generation.**

## 8. Do-Not-Do-Yet List

- **No browser automation yet.** Use manual copy/paste for transports.
- **No unrestricted PowerShell shell.** Use only managed sessions.
- **No app code generation.** Wait for Technical Plan approval.
- **No bypassing safety manifest.** Every command must be classified first.
- **No implementation from stale artifacts.** Always ensure hash MATCH.

## 9. Operator Daily Loop

1. **Integrity Check:** Run `python scripts/check_local_safety.py`.
2. **Lane Selection:** Pick one active implementation lane (Product, Exchange, or Runtime).
3. **Planning Parallelism:** Run planning/docs tasks for other lanes if implementation is waiting for review.
4. **Review Reports:** Inspect `action_log.md` and status reports.
5. **Decide & Advance:** Approve or amend drafted artifacts to move products to the next state.

## 10. Validation

**Validation Result:** `PASS` (Verified all 189 command entries and test suites).

*Note: If validation fails due to concurrent work, record as 'UNRELIABLE due to concurrent lane work'.*
