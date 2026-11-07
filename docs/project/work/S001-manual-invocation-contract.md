---
id: S001
status: Done
parent: B001
---

# Agree the manual invocation and execution contract

## Outcome

Agree how the user discovers and invokes a workflow, and what a run
means. Resolve the execution choices needed by the remaining B001 slices
through bounded investigation and explicit user decisions, not implementation
of a general workflow framework.

## Acceptance criteria

- Propose a command structure covering workflow discovery and invocation, with
  concrete terminal examples. No separate inspection command is required.
- Distinguish configuration owned by the workflow, the destination, and the
  machine. Identify what belongs in version control and what does not.
- Define how a run selects applicable Kijun instructions, Pi resources, model
  settings, working directory, and session history.
- Define minimum run evidence, result checks, output collision behavior, and
  overlapping-run behavior.
- Explain the limits of authority enforcement. Do not describe instructions as
  filesystem or tool access controls.
- Check the proposal against the current Pi and Kijun capabilities, then obtain
  agreement on the decisions needed by the remaining slices.

## Tasks

- [x] Inspect current Pi capabilities and applicable Kijun setup and standards.
- [x] Compare bounded invocation and execution options against B001 and the
      charter, keeping scheduled and event-triggered execution in B007.
- [x] Propose terminal examples, configuration ownership, execution context,
      authority boundaries, and run-result policies.
- [x] Identify feasibility evidence and unresolved trade-offs, and obtain user
      agreement on the execution contract before dependent implementation.

## Review

The user agreed to the simplified
[manual execution contract](../../manual-execution-contract.md): Python,
`tejun list`, `tejun run` for enabled workflows, `tejun run NAME` for one workflow,
background launch into the `agent` Herdr session, workflow-owned Markdown
outputs, and Pi exiting after completion. Detailed manifests and transcript
archives are not required.

Five credential-free startup probes passed on Pi 1.5.0. Read-only Herdr 0.9.1
inspection confirmed the `agent` session exists and already hosts a Pi process
that must remain untouched. The previous draft had two independent content-review
turns; their findings were resolved, but that review does not cover this revised
Herdr launch contract.

The Herdr feasibility question is resolved by the user's manual test. Print-mode
agents appeared without working status. A normal TUI agent reported `working`,
briefly `done`, and disappeared after the script checked the output and sent
Ctrl+D. The user confirmed this was the expected behavior. Use that TUI lifecycle;
S002 was assigned to put the diagnostic script's waiting into a background
worker.

The user accepted removing the separate inspection requirement, resolving the
last acceptance-review finding. Workflow definitions still expose purpose,
inputs, allowed effects, and destinations before execution. The amended criteria
are met by the agreed contract, startup checks, and user-accepted manual TUI test.
S001 is Done on that acceptance basis. The subsequent
[S002 review](S002-first-manual-workflow-run.md#review) records implementation
and successful live execution. During S002, the user approved replacing the
existing `agent` session assumption with automatic startup or reuse of the
dedicated `tejun` session. The current contract reflects that accepted change;
the `agent` evidence above describes the original S001 investigation.
