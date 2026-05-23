# Q3.5 Operator UX & Resource Budget Report

## 1. Scope of Investigation
- Inspected the authoritative `scripts/ws` router to understand how subcommands are dispatched.
- Inspected `registry/ws_command_safety.yaml` and `WS_COMMAND_SAFETY_MATRIX.md` to understand the rigorous safety metadata and classification constraints.
- Analyzed the current MatFinOg python script (`08_browse_knowledge_base.py`) for read-only query capabilities.

## 2. Document Creation
The following operational and design documents were successfully created in `docs/workstation/` to formalize UX and hardware constraints:
- `OPERATOR_COMMANDS.md`: Maps the user-facing intent to the underlying `ws` architecture for both status, quant, and MatFinOg tasks.
- `RESOURCE_BUDGET.md`: Codifies strict CPU, RAM (16GB max), and VRAM (8GB max) guidelines, explicitly forbidding hidden local LLM runs.
- `LOW_RESOURCE_MODE.md`: Details the default degraded-but-safe operational mode of the workstation (no RAG, no Vector DBs, chunking required).
- `SLASH_COMMAND_STRATEGY.md`: Establishes the design rules for translating future `/commands` into `ws` aliases to ensure the central safety manifest is never bypassed.

## 3. WS Shortcuts and Safety Constraints
**Explicitly Deferred `ws` Modfications:** 
Adding MatFinOg shortcuts (`ws matfinog overview`, etc.) directly to `scripts/ws` at this moment has been explicitly deferred to documentation. 
*Reasoning:* Modifying `scripts/ws` requires perfectly synced updates to the 3,500-line `registry/ws_command_safety.yaml` and the `WS_COMMAND_SAFETY_MATRIX.md` files. Even minor whitespace or key drift triggers failures in `check_ws_manifest_drift.py` and `validate_ws_command_safety.py`. Per the prompt instructions ("If integration is risky, do not modify scripts/ws. Document the proposed command design only"), this approach was chosen to preserve absolute safety validation integrity while clearly designing the UX path forward in `OPERATOR_COMMANDS.md` and `SLASH_COMMAND_STRATEGY.md`.

## 4. Hardware and Capability Assurance
- **GPU Usage:** None added. Explicitly bounded.
- **Local LLMs:** None added. Guarded by explicit operator-flag policies.
- **Embeddings/RAG:** None added. Disabled by default in low-resource mode.
- **Browser Automation:** None added. Forbidden in low-resource mode.

## 5. Validation Results
Executed `python scripts/check_local_safety.py`.
- **Status:** PASSED (0 warnings, 0 errors, 0 manifest drifts).
- The Local AI Workstation remains in a pristine, deterministic, strictly-validated state.

## 6. Recommended Next Task
**Quant Q4: Research Idea Intake + Hypothesis Contract**
It is completely safe to proceed to Phase Q4. The system is well-documented, resource-bounded, and the Quant implementation backlog can now be targeted.