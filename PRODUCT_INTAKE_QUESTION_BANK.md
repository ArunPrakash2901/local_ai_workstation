# Product Intake Question Bank

Status: Phase 1 planning. Static questions only; no model or provider use.

Purpose: define deterministic Product Lane intake questions for Phase 1 v1. Each question should be rendered from local data and operator input only.

## Shared Intake Rules

Every product type should collect:

- goal
- target user or audience
- in-scope outcomes
- explicit non-goals
- constraints
- known dependencies
- success criteria
- privacy level
- blockers

Completion rule shared by all types:

- all required questions answered
- all blocking questions either resolved or recorded as `BLOCKED`
- privacy questions answered for private/default-private product types
- product record can identify one concrete next artifact: scope draft or blocker review

Question IDs should be stable and namespaced by product type, for example `website.goal` or `job-pack.target_role`.

## website

Required questions:

| ID | Question |
|---|---|
| `website.goal` | What is the primary business or communication goal of the website? |
| `website.audience` | Who is the target audience? |
| `website.primary_pages` | Which pages or sections are in scope for v1? |
| `website.conversion` | What action should visitors take? |
| `website.content_sources` | What content already exists and what must be written? |
| `website.success_criteria` | How will the operator know the site is successful? |

Optional questions:

| ID | Question |
|---|---|
| `website.brand_constraints` | Are there brand, tone, color, typography, or asset constraints? |
| `website.seo` | Are SEO titles, descriptions, or content keywords required? |
| `website.analytics` | Is analytics or tracking required? |
| `website.hosting` | Is a hosting/deployment target known? |

Blocking questions:

| ID | Question |
|---|---|
| `website.blocking_content` | Is any required page content missing? |
| `website.blocking_assets` | Are required logos, product images, or legal assets missing? |
| `website.blocking_approval` | Is external approval required before scope can lock? |

Privacy questions:

- Does the site include personal contact details, private portfolio material, or client-confidential work?
- Should any page or asset be excluded from cloud handoff in later phases?

Completion criteria:

- goal, audience, primary pages, conversion action, and success criteria are answered
- missing content/assets are either resolved or recorded as blockers

## webapp

Required questions:

| ID | Question |
|---|---|
| `webapp.goal` | What problem does the web app solve? |
| `webapp.users` | Who are the primary users and what are their roles? |
| `webapp.core_workflows` | What are the core workflows in v1? |
| `webapp.data_model` | What data does the app create, read, update, or delete? |
| `webapp.auth` | Does v1 require authentication or user accounts? |
| `webapp.success_criteria` | What must work for v1 to be considered useful? |

Optional questions:

| ID | Question |
|---|---|
| `webapp.integrations` | What external services or APIs are needed? |
| `webapp.permissions` | Are role-based permissions required? |
| `webapp.offline` | Does the app need offline/local-only behavior? |
| `webapp.deployment` | Where will it run in v1? |

Blocking questions:

| ID | Question |
|---|---|
| `webapp.blocking_auth` | Is the auth requirement unclear enough to block scope? |
| `webapp.blocking_data` | Are required data sources unavailable or unsafe to inspect? |
| `webapp.blocking_integrations` | Are required external integrations unknown or unapproved? |

Privacy questions:

- Will the app store personal, private, regulated, or credential-like data?
- Should any user data be excluded from future model/provider context?

Completion criteria:

- users, workflows, data model, auth stance, and success criteria are clear
- unresolved integration or data blockers are recorded

## dashboard

Required questions:

| ID | Question |
|---|---|
| `dashboard.goal` | What decisions should the dashboard support? |
| `dashboard.audience` | Who reads or operates the dashboard? |
| `dashboard.metrics` | Which metrics, statuses, or entities must appear in v1? |
| `dashboard.sources` | What data sources feed the dashboard? |
| `dashboard.refresh` | How fresh does the data need to be? |
| `dashboard.success_criteria` | What makes the dashboard operationally useful? |

Optional questions:

| ID | Question |
|---|---|
| `dashboard.filters` | What filters or drilldowns are needed? |
| `dashboard.alerts` | Are warnings, thresholds, or alerts needed? |
| `dashboard.export` | Is export or reporting required? |
| `dashboard.display` | Where will the dashboard be viewed? |

Blocking questions:

| ID | Question |
|---|---|
| `dashboard.blocking_sources` | Are any required data sources unavailable? |
| `dashboard.blocking_definitions` | Are key metric definitions unresolved? |
| `dashboard.blocking_access` | Is access to data blocked or unsafe? |

Privacy questions:

- Does the dashboard expose private, financial, customer, employment, or credential-adjacent data?
- Should any data source be excluded from cloud/provider handoff later?

Completion criteria:

- audience, core metrics, data sources, refresh expectations, and success criteria are answered
- unavailable data sources are blockers

## automation

Required questions:

| ID | Question |
|---|---|
| `automation.goal` | What repeated task should be automated? |
| `automation.trigger` | How is the automation triggered? |
| `automation.inputs` | What inputs does it read? |
| `automation.outputs` | What outputs or side effects does it produce? |
| `automation.safety` | What must never be changed or deleted? |
| `automation.success_criteria` | How will safe completion be verified? |

Optional questions:

| ID | Question |
|---|---|
| `automation.schedule` | Is a schedule needed? |
| `automation.rollback` | Is rollback or undo needed? |
| `automation.logging` | What logs or audit trail should be kept? |
| `automation.permissions` | What permissions are required? |

Blocking questions:

| ID | Question |
|---|---|
| `automation.blocking_write_scope` | Is the write scope unclear? |
| `automation.blocking_confirmation` | Does the automation need confirmation UX before any write? |
| `automation.blocking_permissions` | Are required permissions unavailable? |

Privacy questions:

- Does the automation read secrets, credentials, private files, large datasets, or raw model output?
- Should any input path be forbidden by default?

Completion criteria:

- trigger, inputs, outputs, write scope, safety constraints, and verification criteria are clear
- unsafe or ambiguous write scope blocks scope lock

## job-pack

Required questions:

| ID | Question |
|---|---|
| `job_pack.goal` | What job application outcome is this pack for? |
| `job_pack.target_role` | What role, company, or role family is being targeted? |
| `job_pack.materials` | Which materials are in scope: resume bullets, cover letter, interview notes, portfolio summary, or outreach? |
| `job_pack.source_material` | What source material may be used? |
| `job_pack.voice` | What voice and positioning should the pack use? |
| `job_pack.success_criteria` | What makes the pack ready to use? |

Optional questions:

| ID | Question |
|---|---|
| `job_pack.deadline` | Is there an application deadline? |
| `job_pack.constraints` | Are there claims, skills, or employers that must not be mentioned? |
| `job_pack.versions` | Are multiple role/company variants needed? |
| `job_pack.links` | Are portfolio or LinkedIn links in scope? |

Blocking questions:

| ID | Question |
|---|---|
| `job_pack.blocking_source` | Is required source material missing? |
| `job_pack.blocking_claims` | Are factual claims unverified? |
| `job_pack.blocking_privacy` | Is private employment material present without an explicit privacy stance? |

Privacy questions:

- Confirm this product is `private: true` unless explicitly overridden.
- What personal data, employer names, salary details, or contact details are included?
- Should all cloud/model/provider handoffs remain blocked for this product until a future explicit confirmation flow exists?

Completion criteria:

- target role, materials, allowed source material, voice, privacy stance, and success criteria are answered
- unverified personal claims remain blockers

## cover-letter

Required questions:

| ID | Question |
|---|---|
| `cover_letter.goal` | What application is this cover letter for? |
| `cover_letter.company_role` | What company and role is being targeted? |
| `cover_letter.key_fit` | What two or three points prove fit for the role? |
| `cover_letter.source_material` | What resume or background material may be used? |
| `cover_letter.tone` | What tone should the letter use? |
| `cover_letter.success_criteria` | What makes the letter ready to send? |

Optional questions:

| ID | Question |
|---|---|
| `cover_letter.length` | Is there a length or format requirement? |
| `cover_letter.referral` | Is there a referral, recruiter, or contact to mention? |
| `cover_letter.constraints` | Are there topics or claims to avoid? |
| `cover_letter.deadline` | Is there a deadline? |

Blocking questions:

| ID | Question |
|---|---|
| `cover_letter.blocking_role` | Is the target role/company unknown? |
| `cover_letter.blocking_claims` | Are key claims unsupported by source material? |
| `cover_letter.blocking_privacy` | Is private personal data present without confirmation? |

Privacy questions:

- Confirm this product is `private: true` unless explicitly overridden.
- Does the letter include address, phone, salary, employer-confidential, immigration, or health/personal details?
- Should cloud handoff remain unavailable for this product in Phase 1?

Completion criteria:

- company/role, fit points, source material, tone, and privacy stance are answered
- unsupported claims block scope lock

## interview-prep

Required questions:

| ID | Question |
|---|---|
| `interview_prep.goal` | What interview or assessment is being prepared for? |
| `interview_prep.role_context` | What role, company, and interview stage are in scope? |
| `interview_prep.focus_areas` | Which skills, topics, stories, or exercises need preparation? |
| `interview_prep.source_material` | What resume, job description, or notes may be used? |
| `interview_prep.output_format` | What should the final prep artifact contain? |
| `interview_prep.success_criteria` | What makes the prep useful? |

Optional questions:

| ID | Question |
|---|---|
| `interview_prep.schedule` | When is the interview? |
| `interview_prep.interviewers` | Are interviewer names or roles known? |
| `interview_prep.practice` | Are practice questions, STAR stories, or drills needed? |
| `interview_prep.constraints` | Are any topics off-limits? |

Blocking questions:

| ID | Question |
|---|---|
| `interview_prep.blocking_role` | Is the role/stage unclear? |
| `interview_prep.blocking_source` | Is required job description or resume material missing? |
| `interview_prep.blocking_privacy` | Is private personal or employer data present without confirmation? |

Privacy questions:

- Confirm this product is `private: true` unless explicitly overridden.
- Does this include personal history, salary, employer-confidential work, or interviewer details?
- Should all cloud/provider handoffs remain blocked until a future explicit privacy confirmation exists?

Completion criteria:

- role context, focus areas, source material, output format, privacy stance, and success criteria are answered
- missing job description or resume source material blocks scope lock

## video-script

Required questions:

| ID | Question |
|---|---|
| `video_script.goal` | What is the purpose of the video? |
| `video_script.audience` | Who is the target viewer? |
| `video_script.format` | What format is needed: short, tutorial, demo, explainer, ad, or narration? |
| `video_script.key_points` | What key points must be covered? |
| `video_script.call_to_action` | What should the viewer do next? |
| `video_script.success_criteria` | What makes the script usable? |

Optional questions:

| ID | Question |
|---|---|
| `video_script.length` | Target length or word count? |
| `video_script.tone` | Tone, pacing, and style? |
| `video_script.visuals` | Are visual beats, captions, or scene notes needed? |
| `video_script.references` | Are there reference videos or examples? |

Blocking questions:

| ID | Question |
|---|---|
| `video_script.blocking_audience` | Is the audience or purpose unclear? |
| `video_script.blocking_claims` | Are factual claims unsupported? |
| `video_script.blocking_assets` | Are required product visuals, screenshots, or legal approvals missing? |

Privacy questions:

- Does the script include personal details, client material, unreleased product details, or confidential claims?
- Should any references be excluded from later cloud/provider handoff?

Completion criteria:

- purpose, audience, format, key points, call to action, and success criteria are answered
- unsupported claims or missing required assets are blockers
