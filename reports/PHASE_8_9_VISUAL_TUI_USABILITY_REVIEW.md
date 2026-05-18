# Phase 8.9 Visual TUI Usability Review

## Assessment

Phase 8.8 materially changed the operator experience. Plain mode now reads like a small workstation application rather than a formatted Bash transcript. The TUI is not yet polished enough to be considered finished, but it is now recognizably a human-facing cockpit with a clear safety envelope.

## 1. Human-Facing Language

Yes, the primary UI is now human-facing.

- The Learning screen leads with `Current Task`, `Recommended Action`, `Provenance`, `Latest Artifacts`, and `Safety`.
- The recommended action is shown as `Start review tutor`, not as the raw backend command.
- Operator choices are expressed as actions such as `View Latest Plan` and `Show Backend Command`.

The main remaining command-first surface is `--snapshot`, which is acceptable because snapshot mode is a report output rather than the main interactive experience.

## 2. Navigation Clarity

Yes, the header, sidebar, breadcrumbs, and cards make navigation clearer.

- The header establishes product identity and global state immediately.
- The sidebar makes the main sections legible even when some are disabled.
- Breadcrumbs make location explicit, especially inside Learning.
- Cards break the Learning view into understandable units instead of one long text block.

This is a meaningful improvement over the prior line-oriented console view.

## 3. Numbered Actions

Mostly yes.

- The numbered actions are easy to scan and fit plain-mode expectations well.
- The operator can understand the available path without memorizing shell syntax.

One rough edge remains: when the main action is disabled, the list starts with `[disabled]` and then continues at `[2]`, `[3]`, `[4]`. That is truthful, but slightly awkward because the visual rhythm implies a missing first action. Before adding more execution classes, the disabled primary action should probably stay visibly mapped to slot `[1]` with a disabled state label.

## 4. Backend Command Visibility

Yes, backend commands are sufficiently hidden.

- Commands are absent from the default Learning screen.
- They appear only after the operator chooses `Show Backend Command`.
- This keeps the main surface focused on intent while preserving auditability and manual fallback.

The command drawer is correct conceptually, though long commands wrap aggressively and are not especially pleasant to read in plain mode.

## 5. Artifact Viewer

Useful and appropriately constrained.

- The `View Latest Plan` path is practical and removes a common manual file lookup.
- The viewer enforces a safe boundary by only opening markdown artifacts under the selected learning stronghold.
- The latest review plan was displayed successfully during validation.

The current viewer is still basic: it prints the whole document into the terminal flow, has no paging, no section jump, and no compact summary mode. It is safe enough now, but it is the clearest area where usability can improve without expanding system power.

## 6. Disabled Actions

Yes, disabled actions are clear.

- The current recommendation is `Start review tutor`.
- The UI explicitly labels it `[PURPLE]`.
- The action card says `[DISABLED] Action requires manual command / future phase.`
- The numbered action list does not present a misleading executable button.

That is the correct behavior for the present boundary, because `Start review tutor` is not in the allowlist.

## 7. Safety Boundary Visibility

Yes, the safety boundary is visible enough for the current phase.

- Global badges show `[READ_ONLY]` and `[SAFE_DRY_RUN]`.
- The Safety card spells out what remains disabled.
- The current non-allowlisted action is visibly blocked.
- The status drawer shows only the read-only backend reads that were executed.

The TUI now communicates safety in the UI itself rather than requiring the operator to remember backend policy.

## 8. Plain Mode Before Textual

Yes, plain mode is acceptable before Textual.

It now provides:

- an application shell
- sectioned navigation
- readable Learning state
- hidden backend detail
- safe artifact inspection
- honest disabled states

Textual would improve polish and interaction density, but it is no longer a prerequisite for having a usable operator cockpit.

## 9. What Still Feels Clunky

- Home cards still embed dense raw command output, so some tables wrap poorly and lose alignment.
- The artifact viewer is a terminal printout rather than a bounded reading surface.
- Long backend commands wrap and truncate awkwardly once revealed.
- Disabled primary action numbering is slightly inelegant.
- The sidebar is descriptive rather than truly navigable beyond the simple numeric home menu.
- The screen still redraws whole large blocks instead of feeling like a focused panel update.

These are usability issues, not architectural failures.

## 10. Improve Before Local Tutor Execution

Before enabling local tutor execution, improve the operator's ability to inspect and understand evidence:

1. Refine the artifact viewer:
   - paging or bounded reading
   - compact metadata header
   - previous/next artifact navigation
   - clearer return path
2. Improve disabled primary-action rendering:
   - keep slot `[1]`
   - show explicit disabled reason by lane, for example `LOCAL_MODEL action not enabled yet`
3. Add stronger recommendation context:
   - why this action is next
   - which artifact made it next
   - whether all prerequisites are current
4. Improve long-command disclosure formatting so the hidden drawer is readable when opened.

Those changes would reduce operator ambiguity before introducing a PURPLE action that actually calls a local model.

## 11. Best Next Phase Choice

Of the proposed options, the best next phase is **artifact viewer improvements**.

Reasoning:

- The visual shell is already good enough to prove the interaction model.
- The safety boundary is already clear.
- Textual installation policy is not blocking current use.
- Local tutor execution should wait until the operator can inspect plans and assessments with less friction.

## 12. Recommended Next Bounded Phase

Recommended next phase:

`Phase 8.10: Learning Cockpit artifact viewer improvements`

Suggested scope:

- improve the plain-mode markdown viewer
- keep it read-only
- add bounded paging / navigation
- add artifact metadata and clearer context
- preserve the current dry-run-only execution boundary

That is a tighter next step than either broad visual polish or enabling local tutor execution immediately.

## Validation Performed

Completed on May 18, 2026:

- `ws tui --plain`
  - opened Learning
  - showed the backend command drawer
  - viewed the latest plan
  - confirmed the current non-allowlisted `Start review tutor` action is disabled
- `ws tui --snapshot`
- `ws ready`
- `ws agent-hygiene`
- `git status --short`
- `git diff --stat`

Observed current state:

- safety badges visible: `READ_ONLY`, `SAFE_DRY_RUN`
- current recommendation: `Start review tutor`
- current recommendation lane: `PURPLE`
- current execution state: correctly disabled
- latest plan viewer: working and constrained to the selected learning stronghold

## Conclusion

Phase 8.8 succeeded. The plain-mode TUI now feels like an operator cockpit rather than a Bash wrapper. The next work should improve evidence inspection, not broaden execution.
