---
id: S011
status: In progress
parent: B004
depends_on:
  - S010
  - S012
---

# Deliver the content-topic research workflow

## Outcome

Deliver a repeatable workflow that researches and shortlists content topics
with editorial material kept in `content-production`. S010 records the original
contract; later user decisions removed brand guidance, JSON coverage history,
and automatic gap retries.

## Acceptance criteria

- The workflow uses the current editorial inputs, access limits, output
  destination, and failure behaviour defined in B004 and the README.
- A run produces sourced content leads with their audience interest and
  uncertainty, plus a separate current-week historical technology calendarium.
  Missing context and unsuccessful research remain visible. No fixed number of
  leads or calendarium events is required.
- Bounded recent report excerpts and user-maintained pursue and reject decisions
  inform research. Updates and reconsidered leads explain what changed;
  calendarium entries are not suppressed by prior findings or rejections.
- Research, recommendations, and user selections remain distinguishable. The
  workflow does not select a topic, plan its presentation, start preparation, or
  publish on the user's behalf.
- Outputs remain in `content-production`; workflow definitions and shared
  execution support remain in Pi Tejun. The workflow does not change unrelated
  projects or require brand guidance.
- The parent uses the approved subagent plugin for bounded research and
  consolidates settled results. Required child failures and incomplete research
  are visible; interrupted runs retain partial reports for inspection.
- Verification covers normal and failure cases, repeat use, decision boundaries,
  subagent settlement, and a representative live run under the simplified
  contract. Structural checks do not prove research quality.

## Tasks

- [x] Deliver the simplified workflow using the subagent support from S012.
- [x] Run credential-free checks for the current report and decision handling.
- [ ] Inspect a representative live result, including sources, audience value,
  anniversary dates, decision handling, and disclosed gaps.
- [ ] Present the result and evidence for acceptance.
