# Technical Plan v1: Portfolio Website Redesign

- product_id: `portfolio-website-redesign`
- product_type: `website`
- label: Portfolio Website Redesign
- generated_at: `2026-05-23T03:28:49Z`
- active_scope_lock: `scope_locks/scope_lock_v2.md`
- active_scope_lock_hash: `375c515260c14d87e77655f3e46a6f8eabba8edb52d854ed8a12646f50456871`
- active_prd: `prds/prd_v2.md`
- active_prd_hash: `92bb6bbf237f2ba27e56bc74424366c681756bc37cdee5a02b4e1f1af808d513`
- active_wireframe: `wireframes/wireframe_v1.md`
- active_wireframe_hash: `157b72805487baf8c5bc9014b054d30f271683ba76d568e802a1a1f21ef86010`
- technical_plan_hash: Hash recorded in product.yaml
- models/providers/agents: none

## Architecture Overview

- Primary goal anchor: Present Arun Prakash / Abi as a credible portfolio candidate for data analytics, data engineering, ML modelling, analytics consulting, and graduate/job applications.
- Scope anchor: Home, Projects, About, Resume/CV, and Contact.
- Build a deterministic, content-first UI architecture aligned to the approved PRD and active wireframe.
- Keep implementation boundaries explicit to prevent scope expansion before implementation planning approval.

## Frontend Structure

- Organize by route-level screens and shared components.
- Separate layout shells, feature sections, and reusable primitives.
- Keep styling tokens and interaction patterns centrally defined.

## Data/Content Model

- Treat PRD and scope artifacts as source-of-truth inputs for static and semi-structured content.
- Constraint anchor: No required page content is missing.
- Define content contracts per screen to reduce implementation ambiguity.

## Routing/Navigation

- Route map must mirror the active wireframe page/screen map.
- Define deterministic transitions between overview/list/detail/contact surfaces.
- Ensure fallback routes and not-found handling are explicit.

## Component Implementation Plan

- Build shared layout/navigation primitives first.
- Implement page-level sections in wireframe order, then enrich with structured content bindings.
- Prioritize accessibility-ready interactive components before visual polish passes.

## Accessibility Implementation Notes

- Use semantic landmarks and predictable heading hierarchy.
- Enforce keyboard navigation and visible focus indicators for all interactive controls.
- Keep copy, contrast, and state feedback compatible with assistive technologies.

## Testing Strategy

- Success anchor: Recruiters can quickly understand background and projects, and the site leads to more interview or contact inquiries.
- Validate structure-to-wireframe parity and route integrity.
- Cover component behavior with deterministic unit/integration checks.
- Include accessibility-focused verification in implementation readiness checks.

## Deployment Assumptions

- Deployment target remains static-host or equivalent web runtime unless revised by a future decision record.
- Build outputs and CI pipelines are planned in implementation planning, not executed here.
- Environment assumptions remain non-secret and workstation-safe in this phase.

## Explicit Non-Goals

- Backend services, authentication, CMS/blog engine, payment features, complex animations, and unrelated project source-code rewrites are out of scope.

## Generated From

- product.yaml
- scope_locks/scope_lock_v2.md
- prds/prd_v2.md
- wireframes/wireframe_v1.md

This artifact was produced deterministically by the workstation from approved Product Lane inputs.
The technical plan hash is recorded in product.yaml.
