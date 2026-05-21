# Phase 8.12 TUI Cockpit Information Architecture Polish

## Summary

Phase 8.12 improves cockpit information hierarchy for `ws tui` without changing backend capabilities or execution boundaries. The TUI now surfaces operator signal first, keeps verbose diagnostics on-demand, and reduces dashboard noise from raw paths and long lists.

## Scope

Updated:

- `tui/app.py`
- `tui/README.md`
- `WORKSTATION_MANUAL.md`
- `reports/PHASE_8_12_TUI_COCKPIT_INFORMATION_ARCHITECTURE_POLISH.md`

Not changed:

- backend command set
- execution allowlist
- Textual implementation
- research cockpit
- provider/model/browser execution behavior
- safe dry-run execution boundary

## Cockpit IA Changes

1. Readiness collapsed to one-line operator summary in dashboard views.
   - Example shape:
     - `[READY] Ollama ✓ | WSL ✓ | RTX 4070 Status: 456/8188 MiB | 38°C | 9 projects`
2. Verbose `ws ready` output removed from main dashboard by default.
3. Full readiness details preserved in System Health view (`[3] System` in plain mode).
4. Shared readiness summarization path used by snapshot/plain dashboards to avoid duplicate rendering logic drift.
5. Learning pane reordered to place operator decision first:
   - Recommended Next
   - risk/status
   - action label
   - current task/session
   - then provenance/artifacts/events
6. Backend command remains hidden by default and appears only when explicitly toggled.
7. Main cockpit artifact presentation now uses short labels + artifact filenames only (no full paths in dashboard panes).
8. Main learning view now shows 2–4 artifact highlights (context-relevant normal/review set).
9. Full artifact catalog and full path remain in artifact viewer.
10. Added persistent plain-mode safety footer:
    - `[READ_ONLY · SAFE_DRY_RUN] main · agent hygiene OK · q quit · ? help`
11. Handoff dashboard views now show at most 3 recent rows and omit path column.
12. Agent hygiene summary elevated near system pulse:
    - branch
    - unresolved count
    - reviewed count
    - ignored outputs status
13. Command log drawer kept compact (recent status reads + latest execution line).
14. Stale decision warning made operator-facing:
    - `[WARN] Advancement blocked: older review decision does not match current session. Next safe action: generate review session.`
15. Status prefix styling standardized with ASCII fallback support:
    - `OK`, `READY`, `INFO`, `WARN`, `FAIL`, plus `CHECK`/`TIMEOUT` where applicable.

## Validation

Executed:

- `python3 -m py_compile tui/app.py` (with `PYTHONPYCACHEPREFIX=%TEMP%` in Windows host shell)
- `ws tui --snapshot`
- `ws tui --plain` (scripted key probes)
- `ws ready`
- `ws agent-hygiene`

Observed:

- Readiness is one-line summary in snapshot/plain dashboard surfaces.
- Full verbose readiness remains available in System Health view.
- Learning screen shows recommended action block near top.
- Main cockpit no longer shows full artifact paths.
- Artifact viewer still shows full file path safely.
- Persistent safety footer appears at bottom of plain-mode major screens.
- Backend command drawer remains hidden by default.
- Non-allowlisted/model-backed recommended action remains disabled.
- Handoff display is capped to 3 rows and omits path.
- Agent hygiene summary appears in system pulse and footer context.

## Safety Confirmation

- No allowlist expansion.
- No new backend commands.
- No provider calls.
- No dependency installs.
- No stronghold mutation paths added.
- Snapshot mode retained.
