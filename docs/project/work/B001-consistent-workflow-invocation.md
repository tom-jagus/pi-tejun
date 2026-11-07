---
id: B001
status: Done
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
The launcher starts or reuses a dedicated `tejun` Herdr session, preserves
existing outputs, and coordinates declared shared files. Individual slice
reviews record the accepted manual, failure, repeatability, and overlap
evidence. The [authoring guide](../../workflow-authoring.md) documents workflow
extension, and the [verification evidence](../../b001-verification.md) maps the
combined delivery to every criterion above.

## Review

All six acceptance criteria pass on the combined implementation, documentation,
and verification evidence. The user explicitly delegated acceptance to this
review if the criteria passed, followed by a commit on `main`. This assessment
checks the brief's outcome separately from its completed slices.

1. One installed command discovers and invokes both workflows from outside the
   checkout. Current installed-command tests corroborate the earlier accepted
   S002 live demonstration of the outside-repository manual path.
2. Readable TOML definitions and local configuration identify each workflow's
   purpose, input, allowed effects, and destination before execution. Discovery
   shows resolved destinations without a separate inspection command.
3. Preflight diagnostics, saved status, exact-content checks, and confirmed Pi
   exit distinguish invalid inputs, unavailable dependencies, failed launches,
   incomplete execution, and successful results. Tests cover both workflows and
   the shared failure paths, including cancellation and unconfirmed work.
4. Repeated runs preserve outputs, use unique run identities and fresh Pi
   conversations, and load only declared history. Collision, overlap, shared-file
   reservation, and recovery policies are documented and tested.
5. A TOML definition added after installation is discovered and executed through
   the existing command without a launcher or installer change, reinstallation,
   or an entry-point convention in another repository.
6. Workflow prompts retain their narrow authority. Invocation does not accept
   recommendations or authorize source changes, Git mutations, or publication.
   Instructions and declarations are explicitly not sandbox controls.

The review reran all 40 Python tests, the Node extension check, and five Pi
1.5.0 startup probes successfully. Current integration checks use fake Herdr;
new live model access and desktop notifications were not tested. Prior accepted
live evidence remains recorded in S002 and the execution contract.

B001 is Done on this delegated acceptance basis. The accepted manual launcher
currently validates exact-content Markdown verification results. Arbitrary
report validation and domain workflows require further work; scheduled and
event-triggered execution remains B007 scope. These limits do not prevent the
agreed manual invocation outcome.
