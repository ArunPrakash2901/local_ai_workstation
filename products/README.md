# Products Registry

`products/` is the local registry for Product Development Lane product records. Each product lives under `products/<product_id>/`, with `product.yaml` as the source of truth.

Product records are separate from strongholds for now. Promotion to strongholds is deferred.

## On-Disk Layout (through Scope Revision Slice 3)

```
products/
  README.md
  <product_id>/
    product.yaml
    action_log.md
    intake.md
    questions.md
    answers.md
    scope_lock.md
    prd.md
    decisions/
      scope_change_<change_id>.md
```

Notes:
- `action_log.md` is append-only human-readable history for registry events.
- `intake.md` and `questions.md` are created by `ws product-intake --confirm` when intake starts.
- `answers.md` is created by `ws product-answer-import --confirm` when operator answers are imported.
- `scope_lock.md` is created by `ws product-lock-scope --confirm` when scope is locked.
- A `logs/` directory is not created in the current slice. If later phases add logs, they must be documented and safety-classified.

## Commands (Phase 0 + Phase 1 Slice 5 + Phase 2 Slice 4)

- `ws product-new` (GUARDED_WRITE): Creates `products/<product_id>/product.yaml` and `action_log.md`. Requires `--confirm` for actual creation. Use `--dry-run` first to preview.
- `ws product-list` (PURE_READ): Lists products by reading `products/*/product.yaml`. No writes.
- `ws product-status <product_id>` (PURE_READ): Reads `products/<product_id>/product.yaml`. No writes.
- `ws product-questions --dry-run` (DRY_RUN_ONLY): Previews static intake questions. No writes.
- `ws product-intake --dry-run` (DRY_RUN_ONLY): Previews intake start and future artifacts. No writes.
- `ws product-intake --product <product_id> --confirm` (GUARDED_WRITE): Starts intake by writing `intake.md`, `questions.md`, and updating `product.yaml` state to `INTAKE_STARTED`.
- `ws product-answer-import --product <product_id> --file <answers_file> --confirm` (GUARDED_WRITE): Imports operator answers, writes `answers.md`, and classifies intake as `SCOPE_READY` or `CLARIFICATION_NEEDED`.
- `ws product-scope --product <product_id> --dry-run` (DRY_RUN_ONLY): Previews deterministic scope draft content from `product.yaml` + `answers.md`. No writes.
- `ws product-scope-change --product <product_id> --file <change_file> --dry-run` (DRY_RUN_ONLY): Previews deterministic impact of a proposed scope correction after locked scope/PRD review findings. No writes.
- `ws product-scope-change --product <product_id> --file <change_file> --confirm` (GUARDED_WRITE): Records a scope change decision under `decisions/`, updates `product.yaml` revision metadata, and marks downstream artifacts stale/needs-revision without editing immutable artifacts.
- `ws product-scope-revision --product <product_id> --dry-run` (DRY_RUN_ONLY): Previews deterministic revised scope text from `scope_lock.md` plus confirmed `decisions/scope_change_*.md`. No writes.
- `ws product-scope-revision --product <product_id> --confirm` (GUARDED_WRITE): Writes a versioned revised scope lock under `scope_locks/`, updates active scope metadata, keeps `scope_lock.md` immutable, and leaves PRD stale/`NEEDS_REVISION` until a future regeneration flow runs.
- `ws product-lock-scope --product <product_id> --confirm` (GUARDED_WRITE): Writes immutable `scope_lock.md`, records `scope_lock_hash` in `product.yaml`, and transitions `SCOPE_READY -> SCOPE_LOCKED`.
- `ws product-prd --product <product_id> --dry-run` (DRY_RUN_ONLY): Previews deterministic PRD content from locked scope. No writes.
- `ws product-prd --product <product_id> --confirm` (GUARDED_WRITE): Writes deterministic `prd.md` from locked scope and updates `product.yaml` metadata without changing state.
- `ws product-prd-review --product <product_id> --dry-run` (DRY_RUN_ONLY): Previews deterministic PRD review report from `product.yaml`, `scope_lock.md`, and `prd.md`. No writes.
- `ws product-prd-approve --product <product_id> --confirm` (GUARDED_WRITE): Writes `decisions/prd_approval.md` and updates PRD approval metadata in `product.yaml`.
- `ws product-prd-status --product <product_id>` (PURE_READ): Reports PRD artifact maturity and presence checks only. No writes.
- `ws product-wireframe --product <product_id> --dry-run` (DRY_RUN_ONLY): Previews deterministic text/ASCII wireframes from approved PRD and locked scope. No writes.

Current Product Lane commands do not call agents, models, providers, browser automation, cloud CLIs, or apply workflows outside `products/<product_id>/`.
`ws product-wireframe --dry-run` does not write `wireframes.md`, does not update `product.yaml`, and does not create UX/technical/build planning files.
`ws product-scope-change --dry-run` does not write decision records, does not update `product.yaml`, and does not regenerate scope/PRD/wireframes.
`ws product-scope-change --confirm` does not rewrite `scope_lock.md`, does not rewrite `prd.md`, does not edit `answers.md`, and does not generate a revised scope lock in this slice.
`ws product-scope-revision --dry-run` does not write `scope_lock_v2.md`, does not update `product.yaml`, and does not regenerate `prd.md`.
`ws product-scope-revision --confirm` writes a new versioned revised scope lock only; it does not rewrite `scope_lock.md`, `prd.md`, or `answers.md`, and it does not regenerate PRD artifacts.

## Product States (through Phase 1 Slice 5)

- `INBOX`: Product record exists, but intake has not started.
- `INTAKE_STARTED`: Intake has been started (templates created), but intake completion and scope lock are not implemented in this slice.
- `CLARIFICATION_NEEDED`: Intake answers were imported, but required/blocking/privacy questions are still unresolved.
- `SCOPE_READY`: Required/blocking/privacy intake answers are complete; deterministic scope draft preview is available via `ws product-scope --dry-run`.
- `SCOPE_LOCKED`: Scope is locked with immutable `scope_lock.md`; further changes require a future scope change decision flow.
- `BLOCKED`: Product cannot proceed until an operator-visible blocker is resolved.

## Supported Product Types (Phase 0)

- `website`
- `webapp`
- `dashboard`
- `automation`
- `job-pack`
- `cover-letter`
- `interview-prep`
- `video-script`

## Privacy Defaults

- `job-pack`, `cover-letter`, and `interview-prep` default to `private: true`.
- No cloud handoff exists in Phase 0.

## What Not To Put Here

Do not store:
- secrets, tokens, credentials, or `.env` files
- raw large datasets
- model weights
- generated binaries
- unrelated project source code (unless a later phase explicitly supports it)

## Future per-product .gitignore policy

Phase 0 does not automatically create `products/<product_id>/.gitignore`.

Later phases may add a per-product `.gitignore` when products begin to accumulate generated artifacts. The purpose is to keep product artifacts bounded and prevent accidental drift into secrets, large data, binaries, model outputs, or unrelated project source.

Product planning artifacts should stay readable: markdown, YAML, and plaintext.

Suggested future `.gitignore` sketch (proposed, not currently generated by `ws`):

```gitignore
.env
*.key
*.pem
*.token
credentials*
secrets*
raw_data/
data/
*.sqlite
*.db
*.parquet
*.csv
*.zip
*.7z
*.bin
*.pt
*.safetensors
node_modules/
dist/
build/
__pycache__/
*.pyc
```

Notes:
- This is a proposed future per-product policy, not active behavior.
- Product source code policy will be decided later.
- Phase 0 product records should remain simple: `product.yaml` and planned logs/docs only.

## Validation (No-Write)

PowerShell:

```powershell
$env:PYTHONDONTWRITEBYTECODE="1"
python scripts\check_local_safety.py
```

This safe local check validates product registry tests without running `ws` commands, creating real products, or running agents/models/providers.
