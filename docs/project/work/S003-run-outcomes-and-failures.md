---
id: S003
status: Done
parent: B001
depends_on:
  - S002
---

# Make unsuccessful runs distinguishable from completed results

## Outcome

Make manual invocation dependable when inputs, dependencies, or execution fail.
Distinguish successful, incomplete, and failed runs through terminal outcomes
and saved evidence, without building a general monitoring system.

## Acceptance criteria

- Missing or invalid inputs and unavailable dependencies produce actionable
  diagnostics without being reported as successful runs.
- Successful, incomplete, and failed execution have distinguishable terminal
  outcomes and saved evidence where execution began.
- Process completion alone does not establish success. The agreed minimum
  result checks must pass.
- An absent, partial, or stale result cannot be mistaken for a newly completed
  result.
- Cancellation and execution failure leave enough information to identify what
  ran, what happened, and where any partial output remains.
- Tests cover these cases without requiring a live model call for every test.

## Tasks

- [x] Implement input and dependency checks with actionable diagnostics.
- [x] Apply the agreed result checks and map execution outcomes to terminal
      reporting and saved run evidence.
- [x] Handle cancellation, partial outputs, and execution failures without
      presenting an earlier result as a newly completed one.
- [x] Add repeatable tests for invalid inputs, missing dependencies, incomplete
      results, stale results, cancellation, and execution failure.

## Review

All six acceptance criteria pass. The user accepted the delivered S003/S004
result and requested its documentation and commit after the separate S001/S002
commit.

- Definition, configuration, UTF-8 input, Pi resource, executable, and history
  checks produce actionable diagnostics. All selected workflows are locally
  validated before any session startup.
- Pending launch acknowledgement is distinct from success. Handled launch
  failure records `failed`; execution failure and graceful interruption record
  `incomplete`. Status and worker diagnostics identify the run and output paths.
- Exact result bytes and confirmed Pi exit are required before publication.
  Blocked, working, and unknown agents are retained rather than closed.
- Missing, empty, incorrect, stale, and symlinked results cannot establish
  success. A fresh partial reservation prevents reuse of an earlier partial.
- SIGINT/SIGTERM handling preserves incomplete status and diagnostics. A real
  disposable SIGTERM test includes the signal mask inherited at worker
  handoff. Timeout, disappeared-agent, and malformed-request tests retain
  useful evidence. SIGKILL remains unconfirmed work; it cannot write a final
  status or silently become success.
- Credential-free Python tests and Node extension checks exercise these cases.
  Extension checks cover exact-model rejection, safe authentication/provider
  diagnostics, aborted or truncated responses, and successful recovery.

The combined suite passes 36 Python tests, Node extension checks, and five
Pi startup probes. The installed CLI and real detached worker also complete a
disposable outside-repository test with fake Herdr. No model provider or real
Herdr session was used by these checks; S002 retains the live demonstration.
Worker interruption does not necessarily stop its Pi agent. Retained-agent
and reservation recovery limits are documented in the
[contract](../../manual-execution-contract.md#results-and-failure-handling).
S003 is Done on the user-accepted result and this review basis.
