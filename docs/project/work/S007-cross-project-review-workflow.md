---
id: S007
status: To do
parent: B002
depends_on:
  - S006
---

# Deliver the manual cross-project review workflow

## Outcome

Deliver one named manual workflow that reviews the agreed project documents,
recommends useful next actions, and saves a concise report in
`_projects-directions`. Implement the accepted
[S006 contract](S006-cross-project-review-discovery.md#accepted-contract)
without a separate scanner, prioritization engine, or decision database.

## Acceptance criteria

- The workflow is discoverable and runnable through the existing installed
  interface outside Pi Tejun. Its readable definition and local configuration
  expose roots, exclusions, tools, instructions, model defaults, effects, and
  destination. Reviewed projects need no bespoke entry point.
- Pi reads only applicable instructions and project documentation, considering
  all non-Done briefs, including Draft. Missing or incompatible `dev` records
  need attention; `src/default` retains its non-Done brief eligibility rule.
  Paused projects remain visible, and completed work and explicit output-folder
  exclusions follow S006. Recommendations distinguish evidence from uncertainty.
- The concise Markdown starts with `Client project`, then `Personal projects`.
  Each group orders blockers/review/decisions before quick wins, then other work;
  each category is oldest first using the agreed work-record modification metric.
  Unknown dates follow known dates; names break ties; each project appears once.
- Each project path heading has `last modified:` and exactly two short unlabeled
  bullets identifying the issue and next action. An optional short summary
  concerns findings and next work, not methodology, exclusions, or execution.
  There is no evidence appendix or per-project outcome paragraph.
- Later runs respect current decisions, declined suggestions, and pause reasons
  recorded in project documents without a separate decisions file or automatic
  conversation/report history. Missing reasons are not invented. Recommendations
  do not update authoritative project scope, status, backlog, or decisions.
- Inaccessible projects remain visible with explicit uncertainty. An unreadable
  root cannot become a successful empty report. The worker publishes only a
  fresh structurally valid result after confirmed Pi exit; partial, malformed,
  missing, symlinked, or stale results cannot establish success. Repeated runs
  preserve prior reports and existing B001 behaviour.
- Credential-free checks exercise definition/configuration integration,
  structural rejection, repeatability, and the shared lifecycle. Behaviour
  examples and an approved real-agent demonstration assess coverage, categories,
  ordering, changed project-local decisions, concision, and project preservation.
  Structural checks are not claimed to prove recommendation quality or coverage.
- After acceptance, relevant usage and authoring documentation describes setup,
  invocation, results, limitations, and authority. The combined result is handed
  to a separate B002 acceptance assessment rather than automatically accepting
  the brief on slice completion.

## Tasks

- [x] Confirm S006 acceptance and align the slice with its final contract.
- [ ] Add the named workflow and its documentation-only review instructions.
- [ ] Add the smallest generated-report validation and configuration support,
      retaining exact checks for the existing verification workflows.
- [ ] Enable existing tools needed for listing, timestamps, document reads, and
      the current report write without claiming technical read-only enforcement.
- [ ] Exercise installed CLI integration, generated results and rejection,
      repeated publication, failures, and existing regression checks.
- [ ] Check controlled behaviour examples and an approved real-agent report,
      including later changed project-local reasons and unchanged project files.
- [ ] Present delivery and remaining evidence for acceptance; update usage docs
      and records only after acceptance. Do not automatically accept B002.

## Boundaries

Only the current result file may be written by a run. No source inspection,
project tests, source/configuration changes, Git actions, installation, decision
capture, backlog creation, or publication are authorized in reviewed projects.
Bash and prompt boundaries are behavioural guidance, not a filesystem sandbox.

The runtime needs no catalogue API or bespoke project scanner. Review logic
lives in workflow instructions and local roots/configuration. Necessary shared
changes concern generated results and their structural checks, not a second
implementation of project classification or recommendation logic. Scheduling
and events remain B007 scope.
