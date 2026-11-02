---
id: S003
status: To do
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

- [ ] Implement input and dependency checks with actionable diagnostics.
- [ ] Apply the agreed result checks and map execution outcomes to terminal
      reporting and saved run evidence.
- [ ] Handle cancellation, partial outputs, and execution failures without
      presenting an earlier result as a newly completed one.
- [ ] Add repeatable tests for invalid inputs, missing dependencies, incomplete
      results, stale results, cancellation, and execution failure.
