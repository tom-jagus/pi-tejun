---
id: S009
status: Done
parent: B003
depends_on:
  - S008
---

# Deliver the manual thematic digest

## Outcome

Deliver a manually invoked digest workflow that researches selected interests,
produces sourced findings, and uses useful coverage history in `digest-briefs`.

## Acceptance criteria

- `tejun run digest` starts the workflow in the `digest-briefs` workspace.
  The configured search extension is available to Pi, and generated reports
  receive an appropriate result check.
- A run produces a concise English digest under `reports/` with sources, dates,
  reasons for inclusion, and distinctions between facts, claims, interpretation,
  and uncertainty, following the research contract in S008.
- The workflow reads but does not edit the watchlist. It reports material
  updates and failed checks without listing unchanged entries.
- Later runs use retained history to identify previous coverage, explain
  material changes when repeating a finding, and retry unresolved gaps. Failed
  or incomplete research is distinguishable from a successful empty search.
- Coverage does not advance for failed or unpublished reports. Interrupted
  publication leaves a visible, recoverable state without silently losing gaps.
  Reports and history remain in `digest-briefs`; runs do not create project
  actions or content assignments.
- Credential-free checks and an observed live run cover the S008 verification
  plan, including repeated runs, empty searches, watchlist gaps, interrupted
  publication, and existing workflow regressions. Structural checks are not
  presented as proof of research quality or completeness.

## Tasks

- [x] Align this slice with the accepted S008 contract and verification plan.
- [x] Deliver the workflow, search integration, and agreed launcher support.
- [x] Verify report and history recovery and run the agreed regression checks.
- [x] Inspect an approved live run and present the result for acceptance.

## Review

The user accepted S009 following the criteria review, including the limitation
that observed live runs used an empty watchlist. Non-empty watchlist parsing
and coverage requirements have automated evidence, but real watched-case
updates and unchanged-case omission were not demonstrated live.

Verification passed 80 Python tests, the Node extension test, five credential-free
Pi startup probes, and whitespace checks. Tests cover installed invocation,
repeated coverage, gap retries, invalid history, and interrupted publication.
Saved live runs demonstrate sourced findings, repeat suppression, retry history,
and confirmed Pi exit and tab closure. Run `20261107T213852Z-a4dd8b350c19`
demonstrates the accepted concise incomplete-check notice, with detailed reasons
kept in history. Structural validation does not prove research completeness or
factual accuracy. B003 still needs its separate outcome-level assessment.
