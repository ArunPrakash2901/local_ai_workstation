# PRD: Portfolio Website Redesign

No model/provider/agent calls.

- product_id: `portfolio-website-redesign`
- product_type: `website`
- label: Portfolio Website Redesign
- current_state: `SCOPE_LOCKED`
- scope_lock_hash: `375c515260c14d87e77655f3e46a6f8eabba8edb52d854ed8a12646f50456871`
- private: `False`

## Executive Summary

- Locked scope source: `scope_lock.md`
- Goal summary: Present Arun Prakash / Abi as a credible portfolio candidate for data analytics, data engineering, ML modelling, analytics consulting, and graduate/job applications.
- Audience summary: Recruiters, hiring managers, analytics teams, consulting teams, and potential collaborators.

## Problem Statement

- Present Arun Prakash / Abi as a credible portfolio candidate for data analytics, data engineering, ML modelling, analytics consulting, and graduate/job applications.
- Audience: Recruiters, hiring managers, analytics teams, consulting teams, and potential collaborators.
- The locked scope is the source of truth for later planning phases.

## Target Users / Audience

- Recruiters, hiring managers, analytics teams, consulting teams, and potential collaborators.

## Goals

- Present Arun Prakash / Abi as a credible portfolio candidate for data analytics, data engineering, ML modelling, analytics consulting, and graduate/job applications.

## Non-Goals

- Backend services, authentication, CMS/blog engine, payment features, complex animations, and unrelated project source-code rewrites are out of scope.

## In Scope

- Home, Projects, About, Resume/CV, and Contact.
- Contact the owner, review projects, and download the resume/CV.
- Existing project summaries, resume content, LinkedIn/about copy, and selected project links. New concise copy may be written for the redesigned site.

## Out of Scope

- Backend services, authentication, CMS/blog engine, payment features, complex animations, and unrelated project source-code rewrites are out of scope.

## Requirements

- Home, Projects, About, Resume/CV, and Contact.
- Contact the owner, review projects, and download the resume/CV.
- Existing project summaries, resume content, LinkedIn/about copy, and selected project links. New concise copy may be written for the redesigned site.
- Scope lock hash must match product.yaml before any downstream planning.
- Preview mode must not write files, update product.yaml, or invoke models/providers/agents.

## Constraints

- No required page content is missing.
- No required logos or images are missing; use existing headshot/assets if available, otherwise keep the design text-led.
- No external approval is required.

## Dependencies

- Existing project summaries, resume content, LinkedIn/about copy, and selected project links. New concise copy may be written for the redesigned site.

## Success Criteria

- Recruiters can quickly understand background and projects, and the site leads to more interview or contact inquiries.

## Risks and Mitigations

- If scope_lock.md and product.yaml diverge, downstream planning must stop until scope is re-locked.
- If any section renders TODO/UNKNOWN, treat the PRD preview as provisional.

## Acceptance Criteria

- Product state remains `SCOPE_LOCKED`.
- `scope_lock_hash` is present and matches `scope_lock.md`.
- Preview mode writes no files and changes no product state.
- No model/provider/agent calls occur.

## Generated From

- product.yaml
- scope_lock.md
- scope_lock.md is the locked source of truth for downstream planning.
- product.yaml records the lock hash and state metadata.

## Open Questions At Lock

- None

## Operator Confirmation

- I confirm this scope is the basis for downstream planning. Changes require a future scope change decision record.
- This lock operation does not run agents, models, providers, browser automation, or cloud handoffs.
- I confirm this revised scope supersedes the previous active scope for downstream planning. Historical scope locks remain immutable.
- This scope revision does not run agents, models, providers, browser automation, or cloud handoffs.

## Next Step

- PRD revision written by `ws product-prd-revision --confirm` from active locked scope.
- Review this preview and keep `scope_lock.md` as the source of truth.
- Written by `ws product-prd-revision --confirm` from active locked scope.
