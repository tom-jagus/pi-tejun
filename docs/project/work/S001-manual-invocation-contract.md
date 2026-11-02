---
id: S001
status: To do
parent: B001
---

# Agree the manual invocation and execution contract

## Outcome

Agree how the user discovers, inspects, and invokes a workflow, and what a run
means. Resolve the execution choices needed by the remaining B001 slices
through bounded investigation and explicit user decisions, not implementation
of a general workflow framework.

## Acceptance criteria

- Propose a command structure covering workflow discovery, inspection, and
  invocation, with concrete terminal examples.
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

- [ ] Inspect current Pi capabilities and applicable Kijun setup and standards.
- [ ] Compare bounded invocation and execution options against B001 and the
      charter, keeping scheduled and event-triggered execution in B007.
- [ ] Propose terminal examples, configuration ownership, execution context,
      authority boundaries, and run-result policies.
- [ ] Identify feasibility evidence and unresolved trade-offs, and obtain user
      agreement on the execution contract before dependent implementation.
