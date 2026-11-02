---
id: B002
status: To do
---

# Cross-project review

## Outcome

Help the user decide what to work on next by assessing selected projects,
identifying useful next actions and refinement needs, and recommending
cross-project priorities. Retain assessments and user decisions in
`_projects-directions`.

## Why

Project records describe individual efforts but do not necessarily show which
one deserves attention now. A consolidated review should reduce repeated
inspection without turning every possible improvement into an obligation.

## Boundaries

The user has projects under both `src` and `dev`; establish their treatment,
discovery roots, and access rules before reviewing them. Read current evidence
alongside project records rather than assuming either activity or inactivity
proves a project's value.

This is advisory cross-project work, not acceptance review or authorization
to implement findings. Do not automatically change project status, add backlog
items, or create a duplicate project-state database. Preserve distinctions
between existing commitments, new suggestions, and the user's decisions.

## Acceptance criteria

- The report identifies which projects and evidence it assessed, and makes
  missing or uncertain coverage explicit.
- Recommendations explain their relevance to the user's priorities and
  constraints, with supporting evidence and unresolved assumptions.
- The result distinguishes actionable work, work needing refinement, blockers,
  paused projects, and cases where no action is warranted.
- Prior decisions, including declined suggestions and reasons for pausing work,
  inform later reviews rather than being repeatedly ignored.
- Cross-project recommendations and recorded user choices remain separate from
  the authoritative scope and status in individual projects.
- A run produces a reviewable result in the agreed destination without
  modifying the reviewed projects or treating recommendations as accepted work.

## Open questions

- Which projects are included, and what rules distinguish `src` and `dev`?
- What priorities, time constraints, and evidence should guide comparisons?
- How should user decisions be captured and revisited without repeating reports
  or duplicating project records?
- What report length and level of repository inspection provide useful value?
