# R4.5 Retention Policy

## Purpose
Define what the workstation keeps, ignores, reviews, and later may archive before any cleanup command is added.

## Report Policy

Tracked curated reports:
- Stable summary reports with durable operator value stay tracked, including:
  - `reports/R3_WORKSTATION_CONTRACT_TESTS.md`
  - `reports/R4_AGENT_HYGIENE_REPORT.md`
  - `reports/R4_5_RETENTION_POLICY.md`
- Existing one-off repair, phase, and status reports remain tracked unless a later review explicitly reclassifies them.

Generated reports ignored by Git:
- `reports/AGENT_CONTRACT_VALIDATION_*.md`
- `reports/AGENT_HYGIENE_*.md`

Why:
- These are timestamped runtime evidence produced repeatedly by normal commands.
- Keeping the latest file on disk is useful for local inspection, but tracking every instance creates low-value Git noise.
- Timestamped audit and cleanup-plan outputs under `cleanup/` are already covered by the existing `cleanup/` ignore rule, so no extra root-level report pattern is needed for them.
- A historical generated report that was already tracked before this policy may remain tracked until a later explicit review; this policy prevents new recurring files from becoming Git noise.

## Branch Policy

Keep:
- `main`
- the current working branch until its purpose is complete
- any branch with unique commits until reviewed

Likely safe to delete later, after manual review:
- local branches that point to the same commit as `main`
- dry-run-created `agent/*` branches with no unique work

Must be reviewed before deletion:
- branches with commits not reachable from `main`
- old `auto/*`, `codex/*`, `codex-handoff/*`, and `agent/*` branches carrying historical implementation experiments or failure evidence

No branch is deleted by the current hygiene flow.

## Stale `CODEX_RUNNING` Run-Folder Policy

Stale `CODEX_RUNNING` folders are diagnostic artifacts, not active runs, when they:
- are historical
- have no `final_report.md`
- have no stdout/stderr/exit-code terminal artifacts

Policy:
- keep them while they explain known runner failures
- list them in `ws agent-hygiene`
- only archive or delete them later after the associated failure history is no longer needed

## Run-Folder Archive Policy

Current state:
- `auto_runs/` is ignored by Git and remains local runtime storage.

Future archive candidates, after explicit review:
- old `PLAN_ONLY` runs
- duplicate canary runs
- stale failed runs whose diagnosis has been captured in a curated report

Must not be auto-removed:
- runs tied to unresolved failures
- the latest successful real apply evidence
- any run still referenced by a report or active decision

## Current Decision
- Ignore recurring validation and hygiene reports in Git.
- Keep curated summary reports tracked.
- Keep branch and run cleanup manual-only until a later explicit retention/apply workflow exists.

## Next Step
Use `ws agent-hygiene` with this policy to produce recommendations only. Add no delete/archive behavior until the operator explicitly asks for a reviewed cleanup command.
