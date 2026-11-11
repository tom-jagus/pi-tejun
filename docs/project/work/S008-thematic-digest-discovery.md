---
id: S008
status: Done
parent: B003
---

# Agree the thematic digest contract

This is the original accepted discovery record. The user later replaced JSON
coverage history and automatic retries with bounded recent-report excerpts.
See B003 and the README for current scope and behaviour.

## Outcome

Establish a practical contract for the first manual thematic digest and identify
what the existing launcher needs to deliver it. Obtain the user's agreement
before starting implementation.

## Acceptance criteria

- The contract identifies initial interests, source selection, research window,
  reading budget, and criteria for worthwhile findings.
- It defines how to present sources, dates, claims, uncertainty, and the
  difference between failed research and a successful search with no findings.
- It establishes what coverage and selection history to retain in
  `digest-briefs`, how later manual runs use it, and any retention limits.
- It identifies the destination, permitted effects, access requirements, and
  how the existing launcher can support the workflow or what it lacks.
- A bounded verification plan covers B003's criteria, including research quality,
  repeated coverage, failure cases, and separation from project and content work.
- The user accepts the contract and any necessary delivery scope.

## Agreed discovery decisions

The digest is written in English. It selects findings by significance rather
than topic quotas. Up to eight findings is guidance for a normal run, not a
hard limit or a target.

Initial interests are AI and agent workflows, security, Linux and open-source
desktops, developer tools and programming, hardware and peripherals, GitHub
repository discovery, homelab and self-hosting, and major events in Poland
across any field. Lesser-known hardware brands and open-source browsers are of
interest. Polish news has a high inclusion threshold. Findings are for the
user's information, not automatic content assignments or content-value notes.

The first run looks back 24 hours; later runs cover the period since the last
successful run. Coverage history records checked periods and research failures
so a saved report does not silently hide a gap. Findings distinguish confirmed
facts from attributed claims and uncertainty. A major unverified report may be
included when its uncertainty is itself important, without presenting it as fact.

The workflow belongs in Pi Tejun. Reports, coverage history, and a
user-maintained Markdown watchlist belong in `~/src/default/digest-briefs`.
The intended command is `tejun run digest`, with Pi running in a dedicated Herdr
workspace in that directory. Reports are concise Markdown summaries with source
URLs; failures state the error and reason without a long diagnostic account.

The workflow reads but does not edit the watchlist. It reports material updates
and separately identifies failed watchlist checks, without listing unchanged
entries. Coverage history is separate from the watchlist and retains only useful
coverage and selection information, not every search result.

## Accepted completion contract

The user accepted the following research, history, access, and verification
scope for delivery.

### Research and report

Search across the agreed interests without a fixed source list or topic quotas.
Prefer primary sources for original claims and independent, reliable reporting
for corroboration. Use official security advisories and Polish authorities when
relevant, while recognizing their limits. Treat GitHub trending as a discovery
signal, not proof of quality, safety, or adoption. Attribute unverified claims;
include a major unverified report only when the uncertainty itself matters.

Each finding has a concise summary, relevant event or publication date, why it
matters to an interest, and source URLs. The report states the coverage period.
A successful search with nothing worthwhile says so. The user-approved S009
reporting amendment replaces the separate failure section with a short
incomplete-check qualification and retry notice. Detailed reasons remain in
coverage history; unchanged watchlist entries are not listed. No coverage claim implies exhaustive
search or guarantees that all important events were found.

### History and recovery

Keep reports under `reports/` and compact per-run coverage records under
`history/`. Retain the checked intervals, topic or watchlist gaps and reasons,
covered subjects and source links, and material selection decisions needed to
avoid repetition. Do not retain all search results. Keep records indefinitely
initially; review retention when the accumulated history becomes burdensome.

A later run reads committed coverage records, starts at the last successful
coverage boundary, and retries unresolved topic or watchlist gaps for their
recorded intervals. It reports any gap it still cannot cover. A technically
successful report with partial research must not mark failed coverage complete.
A missing or inconsistent history record is a visible recovery problem, not
proof that the missing interval was checked.

History updates must not advance coverage for an unpublished or failed report.
Stage per-run history alongside the partial report; publish validated output and
history with a recoverable association. Success requires both. If interruption
leaves one published without the other, preserve the artifacts and surface the
recovery state rather than silently treating the interval as complete. The
implementation must test this boundary; two filesystem writes are not assumed
to be atomic together.

### Access and verification

Permit web searches and source access, reading applicable instructions and the
watchlist and history, and writing only the current report and coverage records
in `digest-briefs`. Do not edit the watchlist, other projects, source or
configuration; do not perform Git actions, create content assignments, or
publish externally. Instructions and tools are not a sandbox.

Discovery found that Tejun disabled automatic extensions and lacked a digest
result check. The delivery scope required explicitly loading `pi-web-search`,
verifying selected provider/model support, and adding a suitable generated-result
check. S009 records the delivered integration and verification evidence.

Use credential-free tests for configuration and extension selection, report
validation, first and repeated periods, empty findings, failed searches,
watchlist gaps, history recovery, interrupted publication, and existing workflow
regressions. Use controlled examples to assess source attribution, uncertainty,
repeat handling, and separation from project or content decisions. Finally,
inspect an approved real-agent run and its saved report for source quality,
coverage, concision, and user value. Structural tests cannot prove research
completeness or factual accuracy.

## Tasks

- [x] Discuss the brief's open questions and agree a bounded first use case.
- [x] Inspect relevant launcher capabilities and destination requirements.
- [x] Propose the report, history, authority, and verification approach.
- [x] Align the dependent delivery slice with the accepted contract.

## Review

The user accepted the discovery contract and delivery scope. The agreed
contract covers the research, report, history, authority, and verification
criteria. Launcher inspection identified the need for generated-result support,
explicit search extension loading, and recoverable report and history publication.
Live search compatibility and delivery behaviour remain implementation checks,
not evidence of completed delivery. S009 is aligned with the accepted contract.
