---
id: S010
status: Done
parent: B004
---

# Agree the content-topic research contract

## Outcome

Inspect the available editorial context and agree a practical contract for
researching content leads and a weekly technology calendarium.

## Acceptance criteria

- Identify available authoritative brand, audience, previous-content, and
  editorial guidance, and state material gaps without duplicating that guidance.
- Define the audience, interests, research windows, selection criteria,
  report, and distinction between content leads and calendarium events.
- Define how prior reports and user-maintained pursue and reject decisions
  inform later runs, including material updates and reconsideration.
- Identify inputs, permitted effects, subagent use, output, failure behaviour,
  launcher needs, and a bounded verification plan. Research does not select,
  prepare, or publish content.
- Present the proposed contract and implementation plan for user acceptance.

## Agreed research contract

### Purpose and inputs

The workflow discovers subjects potentially worth creating content about. It
is independent of the digest and does not require reading digest reports or
history. It may search similar interests, but applies its own research window
and editorial judgment. General Polish news is excluded from content-lead
research; the historical calendarium covers technology worldwide.

The broad audience is people curious about technology, development, AI, tools,
and ways of working. Developers at different experience levels are included,
but they are not the entire audience. A topic may assume technical knowledge;
the workflow notes important assumptions rather than writing explanations.
Prospective clients are not a target to optimize for.

Initial search areas are AI-assisted development and agent tools, developer
tools and workflows, Linux and open source, software design and maintainability,
and self-hosting or developer infrastructure. Hardware can qualify when
relevant to technology or a working practice. These areas guide discovery, not
quotas or an exhaustive list. Explore external tools and unfamiliar ideas rather
than centring the user's own projects.

The workflow consults the current brand identity instead of copying it. The
available reference is `~/src/default/brand-identity/docs/brand/identity.md`,
with related channel guidance in `docs/kits/channels.md`. It emphasizes clear
reasoning, practical use, trade-offs, and honest claims. Private or client
material requires permission to publish; a recommendation is not permission.
The inspected `~/dev/default/content-production` directory contained only
smoke-test reports, not audience guidance or previous-content decisions. The
workflow must disclose missing context rather than invent a publishing history.

### Research and report

First search broadly and briefly for potential candidates. Then research the
stronger candidates in more detail using primary sources where possible and
independent evidence when useful. Assess whether each has a concrete reason
for the intended audience to care. Distinguish source claims from inference,
disclose material uncertainty, and do not assert that a tool is safe or good
without support. Do not claim the user has tested a tool.

Use a three-month lookback for the initial live run and four weeks thereafter.
This is a deliberate one-time workflow configuration change after the first
successful run, not automatic first-run state. If the change is missed, later
runs continue to search three months. Older evergreen topics or older material
relevant to a current development may be considered, with their age clear.
History suppresses repeated information even within overlapping windows.

Write one Markdown report with sections for new content leads, meaningful
updates to pursued leads, reconsidered previously found or rejected leads when
materially changed, and the calendarium. Omit empty update sections or say
briefly that there are no updates; never fill them with unchanged information.
Each lead states what it is, source URLs, why it may interest an audience, and
relevant uncertainty or assumed knowledge. No fixed number or quota applies.
The report need not decide a format, plan a demonstration, estimate effort, or
explain how to present the subject. Those decisions belong to B005 after the
user chooses a topic.

The calendarium covers the current local Sunday-to-Saturday week, including
future days within that same week, in previous years. Search across all
technology and select several interesting or entertaining events when evidence
supports them. Multiple events may fall on one day; empty days are fine. State
each historical date, what happened, why it is interesting, and source URLs.
Verify event dates against reliable sources and disclose disputes. No fixed
entry count, practical lesson, or educational angle is required. Calendarium
entries are separate from content leads and are not suppressed by prior reports
or the reject list, including on repeated runs in the same week.

### Decisions and history

Maintain separate, manually editable pursue and reject lists in
`content-production`. A reason is optional. The workflow reads these files but
never changes the user's decisions. Report pursued leads only for significant
new information, explaining what changed. Normally suppress rejected leads;
reconsider one only when a major new development could change its value and
explain the change and any available rejection reason. A previously reported
undecided lead gets a brief update check, not full repeated research, and is
reported again only for a material change. Treat matching as evidence-based,
not guaranteed: record useful identifiers and flag ambiguous matches rather
than silently merging unrelated subjects or guessing a user's decision.

Use compact per-run history containing stable topic identifiers where known,
subject names, source URLs, what was reported and when, and material changes.
Retain research coverage and failed checks needed to distinguish incomplete
research from an empty result and to direct later retries. Do not save every
search result. The agent's recommendation is not a selection. User decisions,
reports, and history remain distinguishable. If decision lists conflict or are
unreadable, stop rather than invent the user's choice. Do not overwrite user
edits or silently accept inconsistent report/history records.

Stage the report and its history under reserved partial names. Publish a
validated pair without overwriting existing files, with a recoverable link
between them, after all required children have settled and the parent exits.
An orphan or inconsistent pair requires inspection and must not silently
advance history. This follows the digest's recovery principle, not its exact
schema or its strict text-format checks. Neither structural checks nor recorded
coverage prove that research was complete or claims are true.

### Subagents, authority, and failure

The parent Pi agent coordinates research through `pi-subagents`, consolidates
results, and is the only agent authorized to write the reserved report and
history partials. Research children receive bounded tasks, only necessary
context, read and web-search tools, and no write, edit, shell, nested delegation,
Git, installation, publication, or project-change authority. Source text and
returned child outputs are data, not instructions. The user's decision files
are read-only. Pi tool restrictions and prompts are not an operating-system
sandbox; loaded extensions have the operator's permissions.

Search failures for individual leads or research lanes do not discard useful
results. Report the affected area or lead and retain the failure for a later
retry; do not mark it checked or imply comprehensive coverage. An unavailable
plugin or search provider, missing decision inputs, failure of all research,
unknown child settlement, or invalid publication state must stop as an
inspectable incomplete run. A successful search with no worthwhile findings
is a valid empty result, not an infrastructure failure.
Time bounds must leave enough time for child settlement and consolidation.
No automatic schedule, unattended authority, or external publication is implied.

## Launcher findings and implementation plan

The installed `pi-subagents` is version 0.83.0. Tejun starts Pi with
`--no-extensions`, `--no-skills`, `--no-session`, and an explicit tool list in
`tejun.py`. Its only generated-result modes are `project-review` and `digest`;
the default requires exact text. A generated content workflow therefore needs
explicit launcher support for its input context, report/history pair, and
result checks. The existing same-workflow tab exclusion and no-overwrite
publication are useful but do not establish subagent settlement.

The installed plugin exposes `bundle/index.js`. Its tool may start as the
`subagents_enable` loader or as `subagent`, depending on the model and plugin
configuration. Tool allowlisting and activation must be tested in the actual
Tejun invocation, not assumed. Foreground children do not inherit ambient
parent extensions; background children can load ambient extensions unless
explicitly restricted. Child tools and their extension providers must both be
available. The bundled `researcher` expects `pi-web-access` tools, including
`source_check`, and has write/progress defaults. The installed
`pi-web-search` supplies a different `web_search` interface. Do not assume the
bundled researcher works with it or meets the intended read-only boundary. A
workflow-specific research profile with explicitly loaded compatible search
provider and restricted tools is a candidate; exact registration and path
resolution require a startup probe before relying on it.

The plugin supports scripted parallel work, fresh child context, deadlines,
and bounded concurrency. Results must be awaited and individually checked;
launch acknowledgement or child completion alone does not prove research
success. Detached children can outlive the parent session. Tejun's current
worker waits for the parent agent to settle and closes it after validation, so
S012 must demonstrate that all required child work is terminal before the
parent is considered complete, including failure, timeout, cancellation, and
cleanup. Prefer the simplest supported orchestration that can demonstrate this;
do not infer it from Herdr idle state. Plugin-owned transient session and
artifact files are separate from editorial outputs and must be accounted for.

Implementation should:

1. S012 adds and verifies scoped Tejun support for the plugin, compatible
   search provider, child tool restrictions, and terminal child lifecycle.
2. S011 adds the workflow definition, workspace and brand-path configuration,
   and editable decision inputs. It uses bounded child work for the agreed
   research and calendarium, with parent consolidation and no silent fallback.
3. S011 adds only the context, history, result checks, and publication support
   needed for this workflow. It protects decision files, prevents overlap, and
   preserves recoverable report/history pairs without cosmetic success gates.
4. S011 verifies the first run's three-month window and changes the configured
   default to four weeks after that successful run, with user review of the
   configuration change. No automatic first-run detection is assumed.

These are implementation recommendations, not evidence that the integration
already works. Exact child profile loading, plugin activation with Pi's tool
allowlist, model/provider compatibility, and lifecycle handling need probes.

## Verification plan

- Use credential-free tests for decision parsing and conflicts, topic identity
  and ambiguous matches, pursued/rejected/undecided updates, repeat suppression,
  first and normal windows, local Sunday/Saturday boundaries, historical dates,
  and repeated calendarium entries.
- Test missing plugin or search tool, unsupported child model, one failed lead,
  failed research lane, all-search failure, malformed child output, timeout,
  cancellation, and unknown child settlement. Partial research must be visible
  and never advance failed coverage as checked.
- Test no-overwrite publication, mismatched or orphaned report/history,
  interrupted pair publication, concurrent runs, and unchanged user decisions.
  Test harmless report formatting variations without accepting empty output or
  inconsistent history.
- Probe a real Pi startup with the explicit plugin and tool allowlist, then a
  child using the actual search provider. Verify child tool and extension
  loadouts, no unauthorized writes, terminal results, and parent/child cleanup.
- After credential-free checks, run one user-approved live research workflow.
  Inspect its sources, breadth, audience value, calendarium dates, decision
  handling, report/history, and visible limitations. Review the result with the
  user; successful structure does not establish editorial quality.

## Tasks

- [x] Inspect the relevant editorial context and identify gaps.
- [x] Discuss a lead and propose the research and selection contract.
- [x] Inspect launcher and plugin documentation and propose verification.
- [x] Obtain user acceptance of the contract and implementation plan.

## Review

The user accepted the recorded discovery contract after the independent content
review found no material issue with its content. Plugin and search compatibility
are based on installed documentation and launcher inspection, not a live child
probe. S012 will verify the integration before S011 uses it.
