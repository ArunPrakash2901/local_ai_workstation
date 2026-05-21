# PRD WARN Triage: portfolio-website-redesign

## Summary

The deterministic PRD review warning is reproducible and is limited to the `Out of Scope` section. The PRD contains `TODO/UNKNOWN` in `Out of Scope` because the locked scope already contains `TODO/UNKNOWN` there. The locked scope contains that placeholder because the imported answers do not include a product-level out-of-scope, non-goals, or exclusions answer.

This is not a PRD approval-ready state. The PRD should not be approved until the source-lineage gap is resolved through an answer/scope revision path, not by directly patching `prd.md`.

## Reproduced Review Status

Command run:

```powershell
wsl bash -lc 'cd /mnt/d/_ai_brain && ./scripts/ws product-prd-review --product portfolio-website-redesign --dry-run'
```

Result:

- review status: `WARN`
- affected section: `Out of Scope`
- exact warning: `Critical sections contain TODO/UNKNOWN: Out of Scope`
- missing required sections: none
- fail reasons: none
- only `Out of Scope` was listed under `Critical TODO/UNKNOWN`

## Affected Section

- `prd.md` section: `## Out of Scope`
- current content: `- TODO/UNKNOWN`
- corresponding `scope_lock.md` section: `## Out of Scope`
- current content: `- TODO/UNKNOWN`

## Evidence From answers.md

Relevant answer coverage exists for goals, audience, pages, conversion, content sources, success criteria, blockers, and privacy handoff exclusions.

Observed answers:

- `website.primary_pages`: Home, Projects, About, Resume/CV, and Contact.
- `website.conversion`: Contact the owner, review projects, and download the resume/CV.
- `website.content_sources`: Existing project summaries, resume content, LinkedIn/about copy, selected project links, and new concise copy.
- `website.privacy_handoff_exclusions`: Exclude client-confidential work samples, private contact details, and unpublished project materials from later cloud handoffs.

Finding:

- There is no explicit answer for product-level `out_of_scope`, `non_goal`, or `non_goals`.
- The privacy handoff exclusion answer is about later cloud handoffs, not the website product scope itself.
- The answers do not mention backend, authentication, CMS, blog engine, payments, complex animations, or other product exclusions.

## Evidence From scope_lock.md

`scope_lock.md` contains:

```markdown
## Out of Scope

- TODO/UNKNOWN
```

It also contains:

```markdown
## Explicit Non-Goals

- TODO/UNKNOWN
```

The privacy handoff exclusion from `answers.md` was preserved under `Privacy Level`, not under `Out of Scope`.

Finding:

- The locked scope does not contain real product-level out-of-scope content.
- The placeholder originated at scope-lock lineage time, before PRD generation.

## Evidence From prd.md

`prd.md` contains:

```markdown
## Non-Goals

- TODO/UNKNOWN
```

and:

```markdown
## Out of Scope

- TODO/UNKNOWN
```

Finding:

- The PRD matches the locked scope for `Out of Scope`.
- The PRD did not lose valid scope content; it propagated the locked placeholder.

## Renderer / Review Code Finding

`scripts/product_scope.py` derives out-of-scope values by collecting answers whose question ids contain:

- `.non_goal`
- `.non_goals`
- `.out_of_scope`

If no values are found, `_render_section_lines()` emits `- TODO/UNKNOWN`.

`scripts/product_prd.py` reads the `Out of Scope` section from `scope_lock.md`; if the section is empty it defaults to `TODO/UNKNOWN`, and otherwise it renders the section values as-is. In this product, the scope section value is already `TODO/UNKNOWN`, so the PRD renders that value.

`scripts/product_prd_review.py` treats `Out of Scope` as a critical section and flags any `TODO/UNKNOWN` token in critical sections. That behavior is consistent with the approval gate.

Finding:

- `product_prd.py` is not the root cause.
- `product_prd_review.py` is behaving as designed.
- `product_scope.py` is also behaving deterministically based on the available answers; however, the current intake answers do not provide product-level out-of-scope content.

## Root Cause Classification

`A. SOURCE_ANSWERS_INCOMPLETE`

Reason:

The source answers do not contain enough product-level out-of-scope information. The available privacy handoff exclusions are not a substitute for product non-goals/exclusions. The scope and PRD renderers preserved this absence deterministically by emitting `TODO/UNKNOWN`.

## Safest Correction Path

Recommended path: `Path 3 - Source answers incomplete`

Recommended actions:

- Do not patch `prd.md` directly.
- Do not patch `scope_lock.md` directly.
- Do not approve the PRD while `Out of Scope` remains `TODO/UNKNOWN`.
- Use a future answer revision / scope change workflow to add explicit product-level non-goals or exclusions.
- If this is only a smoke-test artifact, record the limitation and either create a new clean smoke record or add a future controlled revision flow that can regenerate scope and PRD from updated source answers.

Potential explicit exclusions to gather from the operator in a future correction task:

- Whether backend/API work is excluded.
- Whether authentication/accounts are excluded.
- Whether CMS/blog engine work is excluded.
- Whether payments/e-commerce are excluded.
- Whether complex animation, custom illustration, or heavy visual effects are excluded.
- Whether new private/client-confidential project content is excluded from the website itself, not just cloud handoff.

## Commands Not Run

- `ws product-prd-approve --confirm`
- `ws product-wireframe --dry-run`
- `ws ready`
- learning workflows
- product write workflows
- agents
- models
- providers
- browser automation
- apply workflows

## Files Not Modified

The following product artifacts were not modified by this triage task:

- `products/portfolio-website-redesign/product.yaml`
- `products/portfolio-website-redesign/scope_lock.md`
- `products/portfolio-website-redesign/prd.md`
- `products/portfolio-website-redesign/answers.md`
- `products/portfolio-website-redesign/questions.md`
- `products/portfolio-website-redesign/intake.md`

## Recommendation

Do not approve `portfolio-website-redesign` yet. Treat the current record as blocked on incomplete source answers. The next implementation task should be a guarded Product Lane answer/scope revision workflow, or a controlled smoke-test reset/new product record, so the `Out of Scope` content can be corrected from source lineage rather than manually patched downstream.
