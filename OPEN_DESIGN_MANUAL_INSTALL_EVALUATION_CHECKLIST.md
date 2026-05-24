# Open Design Manual Install Evaluation Checklist

## Purpose
This checklist is a human-operated evaluation guide for deciding whether and how Open Design should be installed locally later.

This is not an install script and does not perform any installation.

## Current Status
- Open Design has not been installed by the workstation.
- Open Design has not been executed by the workstation.
- Product design workflow is still in non-executing packet/review mode.

## Prerequisite Checks (Manual)
- [ ] Node runtime presence verified.
- [ ] npm presence verified.
- [ ] pnpm requirement confirmed (required vs optional).
- [ ] Open Design CLI/executable name and path confirmed.
- [ ] Output directory configurability verified.
- [ ] Local-only behavior vs provider-backed behavior understood.
- [ ] BYOK/provider requirements understood.
- [ ] Agent CLI invocation behavior understood (Codex/Gemini/Claude/OpenCode/Cursor or others).
- [ ] Network call behavior understood.
- [ ] Output can be constrained to `allowed_write_root`.
- [ ] stdout/stderr capture approach defined.
- [ ] timeout/cancel behavior confirmed.

## Manual Evaluation Steps
1. Read Open Design official docs manually.
2. Choose an install location outside app/source repositories.
3. Verify runtime requirements without executing render workflows.
4. Install only after explicit human approval.
5. Rerun workstation runtime probe:
   - `ws product-design-runtime-probe --tool open-design --dry-run`
6. Do not run render workflows until sandbox/output controls are verified.

## Explicit Stop Conditions
- Unknown write behavior.
- Unknown external/provider call behavior.
- Cannot constrain output to allowed write root.
- Requires writing inside app/source repository paths.
- Requires secrets in unmanaged files or unsafe locations.

## Future Workstation Command Gates (Planned)
- Runtime probe must pass with acceptable readiness signal.
- Prepared run packet must exist.
- Packet HTML review surface must exist.
- This checklist must be manually reviewed by an operator.

Note:
- Manual checklist review marking is planned for a future phase and is not implemented in this slice.
