---
id: B002
status: In progress
---

# Cross-project review

## Outcome

Help the user decide what to work on next by assessing selected projects,
identifying useful next actions and refinement needs, and recommending
cross-project priorities. Save assessments in `_projects-directions`; keep
user decisions and pause reasons in authoritative project records.

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

- The report identifies assessed projects and relevant work in a concise format.
  Recommendations are grounded in project documentation, and missing or
  uncertain evidence is explicit without a separate evidence appendix.
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

## Delivery plan

[S006](S006-cross-project-review-discovery.md) records the accepted review
contract, including roots, exclusions, client-first ordering, concise report
format, documentation-only inspection, and the verification plan. The user
accepted closing discovery and authorized S007 implementation.

[S007](S007-cross-project-review-workflow.md) delivers the workflow through the
existing launcher. Pi follows workflow-owned instructions; shared code adds
only the necessary generated-report validation, preserving existing exact-text
checks. Separate project scanners, decision stores, and general frameworks are
not required. Scheduled and event-triggered execution remains B007 work.

Brief acceptance will assess the combined result against the criteria above,
not infer success from completed slices or structural validation alone.
