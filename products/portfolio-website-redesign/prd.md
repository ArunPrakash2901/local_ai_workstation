# PRD: Portfolio Website Redesign

No model/provider/agent calls.

- product_id: `portfolio-website-redesign`
- product_type: `website`
- label: Portfolio Website Redesign
- current_state: `SCOPE_LOCKED`
- scope_lock_hash: `f0c8a89304ce735567bd5fa4d18deaf466b124b04473ba142a277e3801de3031`
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

- TODO/UNKNOWN

## In Scope

- Home, Projects, About, Resume/CV, and Contact.
- Contact the owner, review projects, and download the resume/CV.
- Existing project summaries, resume content, LinkedIn/about copy, and selected project links. New concise copy may be written for the redesigned site.

## Out of Scope

- TODO/UNKNOWN

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

## Next Step

- PRD draft written by `ws product-prd --confirm` from locked scope.
- Review this preview and keep `scope_lock.md` as the source of truth.
- Written by `ws product-prd --confirm` from locked scope.
