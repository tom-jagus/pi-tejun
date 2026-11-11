---
id: S007
status: Done
parent: B002
depends_on:
  - S006
---

# Deliver the manual cross-project review workflow

This records the original accepted delivery and evidence. The user later
simplified the report layout and structural checks. See the README for current
behaviour.

## Outcome

Deliver the named `project-review` workflow through the installed terminal
interface. It reviews agreed project documents, recommends next actions, and
saves a concise report in `_projects-directions`, without a separate scanner,
prioritization engine, or decision database.

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
- The concise Markdown starts with a dated `Project review` title, followed by
  `Client projects`, then `Personal projects`. Groups use second-level headings,
  categories third-level headings, and project paths fourth-level headings.
  Blockers/review/decisions precede quick wins, then other work; each category
  is oldest first using the agreed work-record modification metric. Unknown
  dates follow known dates, names break timestamp ties, and projects appear once.
- Each project path heading has `last modified:` and exactly two short unlabeled
  bullets identifying the issue and next action. An optional short summary
  concerns findings and next work, not methodology, exclusions, or execution.
  There is no evidence appendix or per-project outcome paragraph.
- Recommendations remain advisory. The workflow does not capture or implement
  decisions, update project scope/status/backlogs, or create a decision database.
  Current project records remain authoritative and are read as evidence.
- Inaccessible projects remain visible with explicit uncertainty. An unreadable
  root cannot become a successful empty report. The worker publishes only a
  fresh structurally valid result after confirmed Pi exit; partial, malformed,
  missing, symlinked, or stale results cannot establish success. Repeated runs
  preserve prior reports and existing exact-content verification checks.
- Credential-free checks exercise definition/configuration integration,
  structural rejection, repeatability, and the shared lifecycle. User-observed
  manual tests assess discovery, categories, ordering, access limitations,
  concision, and project preservation. Structural checks are not claimed to
  prove recommendation quality or coverage. A controlled changed-decision
  demonstration is not required by the accepted delivery scope.
- Usage and authoring documentation describes setup, invocation, results,
  limitations, authority, and workflow workspace behaviour. The combined result
  goes to a separate B002 assessment, not automatic brief acceptance.

## Tasks

- [x] Confirm S006 acceptance and align the slice with the final approved scope.
- [x] Add the named workflow and its documentation-only review instructions.
- [x] Add specific generated-report validation and configured roots/exclusions,
      retaining exact checks for the verification workflows.
- [x] Enable tools for listings, timestamps, document reads, and the current
      report write without claiming technical read-only enforcement.
- [x] Exercise installed CLI integration, generated-result rejection, repeated
      publication, failures, workspace isolation, and same-workflow rejection.
- [x] Review successful real-agent reports and accept the user's manual-test
      observations for the remaining behavioural and project-preservation checks.
- [x] Obtain user acceptance, update documentation, and hand B002 to review.

## Boundaries

Only the current result file may be written by a run. No source inspection,
project tests, source/configuration changes, Git actions, installation, decision
capture, backlog creation, or publication are authorized in reviewed projects.
Bash and prompt boundaries are behavioural guidance, not a filesystem sandbox.

Review logic lives in workflow instructions and configured roots. Shared code
checks the report structure and execution lifecycle, not project eligibility or
recommendation quality. Each workflow uses its own named Herdr workspace in
session `tejun`, with default tab names. Existing tabs block another run of the
same workflow; different workflows may overlap. Success closes only the owned,
unchanged Pi tab, and Herdr removes an empty workspace. Failures retain the tab
for inspection. Scheduling and events remain B007 scope.

## Review

The user accepted the implementation and explicitly requested S007 be marked
Done. They accepted their manual observations as sufficient for the remaining
discovery, ordering, access-limit, and project-preservation checks. They removed
the controlled changed-decision demonstration from acceptance scope because no
decision-implementation feature is being delivered. This supersedes that part
of S006's verification plan; existing project records still guide advisory
recommendations. Decision capture and automatic project changes remain excluded.

The user-approved workflow rename, dated title/hierarchy, and per-workflow
workspace policy supersede the original format and overlap wording. The prompt,
validator, tests, usage guide, authoring guide, and execution contract now agree.

Credential-free verification passes 65 Python tests, the Node extension test,
and whitespace checks. Tests cover installed invocation outside the checkout,
configured roots, malformed/generated output, unchanged exact checks,
no-overwrite publication, retained failures, atomic workspace reservation,
separate workflows, and retry after tab closure. An isolated real-Herdr check
confirmed workspace labels, default tabs, busy rejection, last-tab removal, and
fresh allocation without starting Pi.

Saved runs `20261107T163743Z-9c485abc7223` and
`20261107T170151Z-662cbc3827aa` both record success, report publication, confirmed
Pi exit, and tab closure. Their reports remain in the configured output folder;
the latter records the dedicated workspace ID. These are live execution
artifacts. Broader behavioural acceptance rests on the user's manual testing,
not a claim that fake-agent tests establish model compliance.

All criteria are satisfied on this revised scope and acceptance basis. B002
remains subject to its own outcome-level assessment.
