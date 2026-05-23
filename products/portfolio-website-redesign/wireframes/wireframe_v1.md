# Wireframe v1: Portfolio Website Redesign

No model/provider/agent calls.

Product Metadata:
- product_id: portfolio-website-redesign
- product_type: website
- label/title: Portfolio Website Redesign
- product_state: SCOPE_LOCKED
- prd_status: APPROVED
- current_prd_stale: False

Artifact Sources:
- prd_source: active_prd
- prd_path: prds/prd_v2.md
- prd_hash_status: MATCH
- scope_source: active_scope_lock
- scope_path: scope_locks/scope_lock_v2.md
- scope_hash_status: MATCH

Design Assumptions (from PRD):
- Primary goal: Present Arun Prakash / Abi as a credible portfolio candidate for data analytics, data engineering, ML modelling, analytics consulting, and graduate/job applications.
- Primary audience: Recruiters, hiring managers, analytics teams, consulting teams, and potential collaborators.
- Scope focus: Home, Projects, About, Resume/CV, and Contact.
- Constraint: No required page content is missing.
- Success signal: Recruiters can quickly understand background and projects, and the site leads to more interview or contact inquiries.

## Page/Screen Map

- 1. Home: Primary entry page
- 2. Projects: Portfolio listing
- 3. Project Detail: Case-study page
- 4. About: Author narrative
- 5. Contact / Resume: Reach-out and resume access

## ASCII/Text Wireframes


### Home
+------------------------------------------------------------+
| Header: [Logo] [Primary Nav] [CTA]                         |
|------------------------------------------------------------|
| Hero: Value proposition / key message                      |
|------------------------------------------------------------|
| Featured Projects Grid                                     |
|------------------------------------------------------------|
| About Snapshot | Contact CTA                               |
|------------------------------------------------------------|
| Footer: Links / social / resume                            |
+------------------------------------------------------------+

### Projects
+------------------------------------------------------------+
| Header + Filters/Sort                                      |
|------------------------------------------------------------|
| Project Card Grid (title, short summary, tags)             |
|------------------------------------------------------------|
| Pagination / Load More                                     |
+------------------------------------------------------------+

### Project Detail
+------------------------------------------------------------+
| Breadcrumbs | Project Title                                |
|------------------------------------------------------------|
| Problem | Approach | Outcome                               |
|------------------------------------------------------------|
| Media / screenshots / artifacts                             |
|------------------------------------------------------------|
| Related Projects | Next Project CTA                         |
+------------------------------------------------------------+

### About
+------------------------------------------------------------+
| Header                                                     |
|------------------------------------------------------------|
| Bio / Experience summary                                   |
|------------------------------------------------------------|
| Skills / Timeline / Principles                             |
|------------------------------------------------------------|
| Contact CTA                                                |
+------------------------------------------------------------+

### Contact / Resume
+------------------------------------------------------------+
| Header                                                     |
|------------------------------------------------------------|
| Contact methods / form (if applicable)                     |
|------------------------------------------------------------|
| Resume download / profile links                            |
+------------------------------------------------------------+

## Component Inventory

- Global header/navigation
- Primary content area
- Section-level calls to action
- Supporting metadata/context blocks
- Footer or utility region
- Error/empty state treatment

## Navigation Model

- Top-level navigation between primary screens/pages
- Contextual links from list/overview to detail
- Return paths (breadcrumbs/back action)
- Direct entry handling for deep links

## Content Hierarchy

- Level 1: Core value/intent framing
- Level 2: Primary workflow or key content
- Level 3: Supporting evidence/details
- Level 4: Secondary utilities and metadata

## Responsive Notes

- Desktop-first multi-column layouts collapse to single column on small screens.
- Navigation reduces to compact menu on narrow widths.
- Dense modules (grids/charts/tables) need stacked fallback.

## Accessibility Notes

- Ensure semantic landmarks (header/main/nav/footer).
- Keyboard focus order must follow visual reading order.
- Color contrast and non-color state indicators required.
- Interactive controls require explicit labels and states.

## Unresolved Design Questions

- None

## Generated From

- product.yaml
- prds/prd_v2.md
- scope_locks/scope_lock_v2.md

Next Step:
- Generated by `ws product-wireframe --confirm`
- future ws product-ux-spec --dry-run
- future ws product-tech-plan --dry-run
