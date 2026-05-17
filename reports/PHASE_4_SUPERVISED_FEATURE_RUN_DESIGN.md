# Phase 4: Supervised Feature-Run Design

Date: 2026-05-17  
Status: Design only. `ws feature-run` is not implemented in this phase.

## Executive Summary

The Feature Stronghold now owns the local evidence loop for one feature: contract, plan, validation, handoff, imported response, deterministic review, and current report. The next step should not be an unconstrained execution loop. It should be a **supervised run preflight** that proves the feature is genuinely ready for mutation before any apply-capable command is allowed to run.

The first implementation should therefore be:

```bash
ws feature-run <feature> --dry-run
```

That command should resolve the feature, re-read live workstation evidence, classify the next safe action, and write a run report. It should not invoke providers, run `agent-run`, or mutate any repo.

## Current Observed State

The current stronghold is already a good candidate for the future dry-run path:

- Feature: `stabilize-ws-command-documentation`
- Project: `workstation_control_plane`
- Feature state: `VALIDATED_LOCAL`
- Latest validation result: `PASS`
- Latest handoff review: `REVIEW_ACCEPTED`
- Current blockers: none currently recorded
- Current recommendation: `Ready for next supervised implementation phase`
- `provider_invocation`: `false`
- `browser_automation`: `false`

The reviewed feature artifacts currently line up on the same main commit:

- Feature state commit: `ef52ef0147e745caffe2c5b65dd00ddcd061802c`
- Latest feature handoff commit: `ef52ef0147e745caffe2c5b65dd00ddcd061802c`

The requested validation snapshot on 2026-05-17 also showed:

- `ws feature-status`: feature remains `VALIDATED_LOCAL`
- `ws handoff-status`: latest linked handoff remains `REVIEW_ACCEPTED`
- `ws feature-report`: latest validation `PASS`, latest review `REVIEW_ACCEPTED`
- `ws ready`: passed
- `ws agent-hygiene`: passed with `0` unresolved `CODEX_RUNNING` folders
- `git status --short`: clean before this report was created

## 1. What Should `ws feature-run` Do?

`ws feature-run` should become the feature-level execution coordinator, not a replacement for the existing lower-level commands.

For the first release, it should:

1. resolve the Feature Stronghold
2. read feature state, latest plan, validation evidence, latest report, and latest handoff review
3. re-check live workstation readiness and repo cleanliness
4. classify whether the feature is:
   - dry-run ready
   - ready for another handoff
   - blocked
5. write a feature-run preflight report under the stronghold
6. append the decision to the feature loop log
7. print the exact next safe action

It should **not**:

- call providers
- automate the browser
- run `ws agent-run`
- run apply
- mutate a repo
- create a worktree

Later, after the dry-run contract is proven stable, `feature-run` can coordinate a human-approved transition toward handoff, reviewed-worktree execution, and post-apply validation.

## 2. Allowed States Before `feature-run`

For the MVP dry-run, the accepted feature state should be deliberately narrow:

- `VALIDATED_LOCAL`

That state means the stronghold already has:

- a plan
- a passing local validation
- no provider or browser automation side effects

All other stronghold states should block or redirect:

| Feature State | MVP Behavior |
| --- | --- |
| `CREATED` | block; run `ws feature-plan` first |
| `LOCAL_PLAN_READY` | block; run `ws feature-validate` first |
| `HUMAN_APPROVAL_REQUIRED` | block; require explicit operator resolution |
| `BLOCKED` | block; preserve blocker |
| `PASSED` / `FAILED` | block; terminal feature already decided |

Future versions may support resume semantics from `HUMAN_APPROVAL_REQUIRED`, but that should not be part of the first implementation.

## 3. Main Repo Or Reviewed Worktree?

The dry-run MVP may inspect the feature's recorded repo path and current main state because it is read-only.

Any future **apply-capable** path should require a reviewed worktree before mutation:

- `ws worktree-review <worktree_path>` must return a usable state such as `READY`
- the selected worktree must still be clean and based on the expected commit
- the run report must name the exact worktree that would be used

The default policy should be:

- **main repo for read-only evidence only**
- **reviewed worktree required for mutation**

This keeps the supervised execution lane compatible with the workstation's worktree isolation direction and avoids making `main` the place where uncertain agent output first lands.

## 4. Should The First Implementation Be Dry-Run Only?

Yes.

The first implementation should be dry-run only because the workstation has just completed the local evidence loop. The next thing to prove is not whether an agent can edit files; it is whether the system can reliably answer:

- is this feature still eligible for execution?
- are the report, validation, and review artifacts fresh?
- is the next safe action apply, handoff, or stop?
- are all mutation gates visible before any tool crosses them?

Only after that decision surface is stable should a later phase wire in apply-capable behavior.

## 5. Integration With Existing Commands

| Existing Command | Feature-Run Role |
| --- | --- |
| `ws feature-validate` | prerequisite evidence source; must have latest `PASS` on the current commit |
| `ws feature-report` | prerequisite summary source; latest report must exist and match the current evidence set |
| `ws apply-ready` | future lower-level pre-apply gate after a reviewed worktree is selected |
| `ws agent-run` | future bounded execution engine only after all gates pass and a human approves mutation |
| `ws worktree-review` | required reviewed execution-location gate before any future apply path |

Recommended orchestration model:

1. `feature-run --dry-run` verifies feature-level readiness.
2. If reasoning is still missing, it emits `FEATURE_RUN_HANDOFF_READY`.
3. If all feature-level gates pass, it emits `FEATURE_RUN_DRY_READY`.
4. A later supervised mode can require:
   - reviewed worktree
   - fresh `apply-ready`
   - explicit human approval
5. Only then may a future path invoke `agent-run`.

## 6. Exact Gates Before Any Apply

Before any future apply-capable `feature-run` mode is allowed, all of these gates must pass:

| Gate | Required Result |
| --- | --- |
| Feature state | `VALIDATED_LOCAL` |
| Local validation | latest result is `PASS` |
| Latest browser/CLI review | `REVIEW_ACCEPTED` |
| Allowed files | explicit, non-empty allowlist |
| Latest feature report | present and current for the same evidence set |
| Repo cleanliness | clean |
| Current feature evidence | plan, validation, review, and report all match the current expected commit |
| `ws ready` | healthy |
| `ws agent-hygiene` | healthy |
| Reviewed worktree | required and freshly `READY` before mutation |
| `ws apply-ready` | passes for the selected execution context |
| Active run safety | no unresolved conflicting run or stale execution lock |

The user-specified gates are the hard minimum. The worktree, freshness, and active-run checks are necessary additions because a feature can be locally valid yet still unsafe to mutate from the wrong place or against stale evidence.

## 7. What Must Remain Human-Approved?

Keep these steps human-gated:

- choosing whether to proceed after the dry-run result
- selecting or accepting the execution worktree
- sending any browser/cloud handoff
- approving any provider or CLI invocation that can influence later mutation
- launching any real apply or `agent-run`
- accepting diffs that exceed expectations even if still within the allowlist
- deciding whether a blocker should be overridden, retried, or abandoned
- final merge/keep/discard decisions

The human should approve irreversible boundaries, not reconstruct routine evidence by hand.

## 8. What Should Be Automated?

Automate the local coordination work:

- stronghold resolution
- evidence discovery
- current-commit comparisons
- latest validation/review/report lookup
- clean-repo checks
- readiness and hygiene checks
- terminal-state classification
- report writing
- loop-log append
- next-safe-action recommendation

Later phases may automate:

- creation of a feature-linked handoff packet when reasoning is still required
- reviewed-worktree preflight
- generation of the exact future `apply-ready` command

Automation should compress the operator's search burden, not remove the approval boundary before mutation.

## 9. Reports To Write

Recommended future report layout inside the stronghold:

```text
runs\
  <timestamp>_feature-run-dry\
    feature_run_report.md
    gate_results.json
```

`feature_run_report.md` should include:

- feature identity
- starting feature state
- current repo snapshot
- gate-by-gate results
- validation/report/review evidence paths
- selected terminal state
- blockers, if any
- exact next safe command
- explicit safety statement that no mutation occurred

`gate_results.json` should hold the machine-readable version of the same gate decisions for later orchestration.

The run should also append one readable entry to `loop_log.md`. Future apply-capable versions can add:

- `apply_preflight_report.md`
- `apply_execution_report.md`
- `post_apply_validation_report.md`

## 10. Terminal States

These should describe the result of one `feature-run` attempt, separate from the long-lived Feature Stronghold state machine:

| Terminal State | Meaning |
| --- | --- |
| `FEATURE_RUN_DRY_READY` | dry-run gates passed; safe to ask for supervised next-step approval |
| `FEATURE_RUN_BLOCKED` | required evidence or safety gate failed |
| `FEATURE_RUN_HANDOFF_READY` | feature is locally coherent but still needs reviewed reasoning evidence before execution |
| `FEATURE_RUN_APPLY_READY` | future state only; reviewed worktree, human approval, and `apply-ready` all passed |
| `FEATURE_RUN_COMPLETED` | future state only; execution and post-run validation completed successfully |
| `FEATURE_RUN_FAILED` | future state only; an execution attempt or required validation failed terminally |

For the first dry-run implementation, the only reachable terminal states should be:

- `FEATURE_RUN_DRY_READY`
- `FEATURE_RUN_HANDOFF_READY`
- `FEATURE_RUN_BLOCKED`

That limited surface is enough to validate the preflight contract without pretending mutation is already safe.

## 11. MVP Command

Recommended first command:

```bash
ws feature-run <feature> --dry-run
```

Recommended MVP behavior:

- require the feature to resolve cleanly
- require state `VALIDATED_LOCAL`
- re-read latest validation, latest report, latest linked review, repo status, readiness, and hygiene
- emit one dry-run terminal state
- write a run report under `runs/`
- append to `loop_log.md`
- leave:
  - providers untouched
  - browser untouched
  - `agent-run` untouched
  - worktrees untouched
  - repos untouched

No other flags are needed in the first slice. A later phase can add explicit worktree selection once the dry-run result is trustworthy.

## 12. Why Actual Apply Should Stay Deferred

Actual apply should remain deferred until dry-run proves stable because it combines several risks at once:

- feature evidence may be stale even when each artifact is individually well-formed
- report freshness and commit alignment need to be verified repeatedly, not assumed
- worktree policy must be explicit before mutation leaves the main repo
- lower-level apply gates need to be composed, not bypassed
- the system has not yet proven that it can classify "ready", "needs handoff", and "blocked" consistently across repeated runs

Dry-run is the cheap place to find contract flaws. Once that layer is boring and reliable, a later phase can add a supervised apply transition with much less ambiguity.

## Recommended First Implementation

Implement later:

```bash
ws feature-run <feature> --dry-run
```

Initial success criteria:

1. resolves an existing stronghold
2. re-checks live evidence without mutating anything
3. writes one machine-readable and one human-readable run report
4. appends a loop-log event
5. classifies the next safe action using the terminal states above

Do not enable apply, provider execution, browser automation, CLI execution, or worktree mutation in that first implementation.

## Validation Run

Requested validation performed on 2026-05-17:

- `ws feature-status`
  - latest feature: `stabilize-ws-command-documentation`
  - state: `VALIDATED_LOCAL`
- `ws handoff-status`
  - latest linked handoff: `REVIEW_ACCEPTED`
- `ws feature-report /mnt/d/_ai_brain/features/workstation_control_plane/stabilize-ws-command-documentation`
  - latest validation: `PASS`
  - latest review: `REVIEW_ACCEPTED`
  - recommendation: `Ready for next supervised implementation phase`
- `ws ready`
  - passed
- `ws agent-hygiene`
  - current branch: `main`
  - unresolved `CODEX_RUNNING` folders: `0`
- `git status --short`
  - clean before this design report was created
- `git diff --stat`
  - no tracked diff before this design report was created

No apply path was run, no provider was invoked, no browser automation was used, no worktree was created or modified, and no project repository was modified.
