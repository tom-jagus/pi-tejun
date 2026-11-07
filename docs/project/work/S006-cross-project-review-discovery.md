---
id: S006
status: Done
parent: B002
---

# Agree the cross-project review contract

## Outcome

Resolve the decisions needed to deliver B002 as one useful manual workflow.
Recommend a bounded review contract, establish its feasibility with the current
launcher, and obtain agreement before implementing the dependent delivery slice.

## Acceptance criteria

- The contract identifies included projects, discovery roots, exclusions,
  applicable instructions, and permitted read access.
- Priorities, evidence limits, recency, report length, and handling of missing,
  inaccessible, stale, or contradictory records are defined.
- The report distinguishes blockers, quick wins, and other unfinished work.
  Concise recommendations are grounded in project records without separate
  evidence lists, acceptance decisions, or invented commitments.
- The output destination and ownership are resolved. Project-local decisions
  and pause reasons inform later runs without a separate decision database.
- Feasibility findings identify the minimum generated-report support while
  preserving B001's exact-content workflows and manual execution lifecycle.
- A bounded verification plan covers every B002 criterion, distinguishes
  structural checks from recommendation quality, and preserves reviewed projects.
- The user accepts the contract and necessary integration scope before S007.

## Tasks

- [x] Establish approved discovery access and inspect project documentation.
- [x] Check the current launcher and destination against the intended workflow.
- [x] Agree coverage, priorities, report format, history, and authority limits.
- [x] Prepare and revise a concise sample against observed project records.
- [x] Obtain acceptance and align S007 with the accepted contract.

## Accepted contract

### Coverage and inspection

- Review immediate project directories under `~/dev/clients` and
  `~/dev/default`. Under `~/src/default`, include only repositories with
  non-Done briefs. Exclude other roots and forks.
- Every non-Done brief counts, including Draft. Keep paused projects visible
  with their recorded reason. Do not infer completion from inactivity or an
  unreadable index. Exclude a fully completed project's documented work.
- Flag missing, legacy, or incompatible documentation in `dev` as project
  documentation needing attention, not as permission to redefine or migrate it.
- Exclude `content-production` and `_projects-directions` as output folders.
  Keep exclusions explicit rather than generalizing from absent records.
- Read applicable instructions, charters, `docs/project/work.md`, and relevant
  brief/slice files. Item files own their status. Do not inspect source, run
  project tests, change projects, create backlog items, or accept findings.
- Do not follow symlinks outside approved roots or recursively discover nested
  projects. These conservative discovery limits avoid expanding access through
  directory structure. Missing or contradictory records need attention.

### Ordering and recency

- Client projects precede personal projects. Both `dev/default` and eligible
  `src/default` projects form the personal group.
- Within each group, put blockers and work awaiting review or a user decision
  first, then quick wins, then other unfinished work. State the actual blocker.
- A quick win has a clear, unblocked next action that could fit one focused
  session. Do not promise effort or treat completing a slice as finishing a brief.
- Within each category, sort oldest first by the newest modification time of
  `work.md` and Markdown work-item files, including Done items. Use project name
  for ties. This is filesystem recency, not proof of meaningful activity.
- Put unavailable dates after known dates within the relevant category, sorted
  by name. Do not substitute unrelated directory or source modification times.
- Show each eligible project once in its highest applicable category. Use no
  age threshold and do not hide paused work or previously inconvenient findings.

### Report and history

- Save a new Markdown report in `~/dev/default/_projects-directions` using the
  shared run naming and no-overwrite publication policy.
- Start with `# Client project`, followed by `# Personal projects`. Use category
  subheadings and project paths as headings. Omit empty categories; state when
  a group has no eligible projects.
- Each project has one `last modified:` date or `unavailable` and exactly two
  short bullets: the issue or opportunity, then the next action. Do not prefix
  them with labels or add evidence lists, outcome paragraphs, or source links.
- An optional short `# Summary` concerns pending work and what to tackle next,
  not workflow execution, exclusions, or a methodology explanation.
- Existing decisions and pause reasons remain in authoritative project records.
  Read them as data; do not create `decisions.md`, update decisions, resume old
  conversations, or treat earlier reports as accepted choices. Unrecorded
  choices cannot be remembered by a fresh run.

### Execution and failures

- Keep the existing named-workflow interface and fresh Pi TUI lifecycle. Local
  configuration supplies roots, exclusions, and destination. Use saved Pi model,
  thinking, and timeout defaults unless explicitly configured otherwise.
- Workflow instructions own discovery, assessment, and ordering. Enable existing
  read, write, and Bash tools for documentation reading, filesystem listing and
  timestamps, and writing only the current result. This is not a sandbox.
- Add narrow generated-report validation rather than a second review engine or
  a general plugin framework. Exact-text checks for existing workflows remain.
- Structural checks can reject malformed headings, dates, duplicate entries,
  broken visible ordering, or an expanded per-project format. They cannot prove
  full coverage, accurate classification, or recommendation quality.
- Retain inaccessible projects with an explicit problem and unavailable facts.
  An unreadable discovery root must not become a successful empty-group report.
  Use existing failed/incomplete diagnostics rather than fabricate coverage.
- Preserve fresh partial reservations, confirmed Pi exit, unique results, and
  no-overwrite publication. Invalid or incomplete output is not a successful run.

## Verification plan

- Coverage and evidence: disposable client, personal, completed, Draft, missing,
  legacy, and inaccessible-record examples; check selected paths and concise
  item references without source inspection or a report-side evidence appendix.
- Relevance and categories: inspect whether reasons and next actions follow the
  records, including review, user decisions, external blockers, quick wins, and
  no-action cases. Client/group/category ordering precedes recency; check ties
  and unavailable dates. These are behaviour checks, not guarantees from syntax.
- Prior decisions: alter a fixture's project-local pause or declined-work reason
  between runs and check that a later review respects the current record while
  retaining the project. Do not introduce output-side decision storage.
- Authority: compare reviewed fixture files before and after runs. No source,
  project-state, decision, or Git mutation is part of the workflow.
- Execution: exercise installed invocation outside the checkout, structural
  rejection, unreadable-root failure, repeat runs, output preservation, and the
  existing B001 regression suite without model calls.
- Demonstration: an approved real-agent report and human inspection of its
  coverage, ordering, concision, and recommendations remain S007 delivery
  evidence. A fake Herdr result does not prove Pi follows the prompt.

## Review

The user accepted closing S006 and starting S007 after reviewing the sample and
agreeing the narrow integration and failure-handling proposal. All discovery
criteria are met by the documented contract, read-only inspection, revised
sample, and verification plan. S006 is Done on that explicit user acceptance.

Inspection found current-format records in Pi Kijun, Pi Tejun, Tanteki Flow,
and Stream Studio; legacy records in OpenCode Mentor; and missing standard
records in Rakuraku Kii. The client root was empty, so the sample does not
demonstrate client-first ordering. Controlled examples and runtime behaviour
remain S007 checks. The concise sample is stored in the agreed output folder
as `cross-project-review-sample-20261107-154215.md`, not copied into Pi Tejun.

The current launcher was inspected: it compares exact expected bytes and needs
an additional generated-report path. The user accepted preserving that launcher
model with a narrow validation extension and instruction-owned review logic.
Automatic workflow behaviour and model compliance remain unverified until S007;
they are not required evidence of completing this discovery slice.
