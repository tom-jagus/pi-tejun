---
id: B001
status: In progress
---

# Consistent workflow invocation

## Outcome

Provide a discoverable, system-wide terminal interface for invoking named Pi
workflows with defined inputs and known output destinations. Keep workflow
definitions and shared setup together in Pi Tejun rather than requiring a
separate entry-point convention for each destination repository.

## Why

The user should not have to navigate into a repository or reconstruct a prompt
each time they want a project review or research report. A common interface
should also make future workflows easier to find and use.

## Boundaries

This brief covers manual invocation; B007 covers scheduled and event-triggered
execution. Manual access should remain usable independently of those triggers.
Do not prescribe messaging or a particular plugin. Keep domain material and
decisions in their dedicated locations; personal credentials and machine-specific
settings need not become tracked workflow content.

Use applicable Kijun standards without duplicating or weakening them. Defining
an invocation does not grant unrestricted tool or filesystem access. Do not
choose a command name, implementation language, or session strategy in this
brief.

## Acceptance criteria

- An available workflow can be identified and invoked without changing the
  terminal's current directory to its repository.
- Each workflow has a clear purpose, required inputs, allowed effects, and an
  output destination the user can identify before execution.
- Missing inputs, unavailable dependencies, and failed or incomplete execution
  are distinguishable from a successfully produced result.
- Repeated invocation has defined behavior for existing outputs and relevant
  history, without silently continuing an unrelated interactive session.
- Adding a workflow does not require an unrelated repository or another
  installation convention solely to expose its terminal entry point.
- Invocation does not imply approval of generated recommendations, source
  changes, Git work, or external publication.

## Execution contract

The [manual execution contract](../../manual-execution-contract.md) records the
agreed simple launcher model and user-verified Herdr TUI lifecycle. No separate
inspection command is required. Readable workflow definitions and configuration
keep inputs, allowed effects, and output destinations knowable before execution.
The launcher now starts or reuses a dedicated `tejun` Herdr session. The
accepted manual execution evidence is recorded in S002; failure, repeatability,
and overlap requirements remain in S003 and S004.
