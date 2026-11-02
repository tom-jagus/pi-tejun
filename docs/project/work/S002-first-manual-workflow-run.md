---
id: S002
status: To do
parent: B001
depends_on:
  - S001
---

# Discover, inspect, and run one workflow from any directory

## Outcome

Deliver the first complete manual path through the agreed interface, including
user-level setup, discovery, inspection, and execution through Pi. Use a small
verification workflow with explicit inputs and a predictable result, without
implementing the domain outcomes owned by other briefs.

## Acceptance criteria

- After the documented user-level setup, the interface works outside the
  Pi Tejun directory.
- The user can list available workflows and inspect a workflow's purpose,
  required inputs, allowed effects, and resolved output destination before
  execution.
- The user can supply valid inputs and invoke the verification workflow through
  Pi.
- The run uses the agreed execution context and writes its result to the
  declared destination.
- A successful invocation identifies the result and its associated run.
- Invocation does not treat the generated result as accepted or grant permission
  for source changes, Git operations, or publication.

## Tasks

- [ ] Implement the agreed user-level setup and shared terminal entry point.
- [ ] Add the verification workflow and its inspectable definition.
- [ ] Connect discovery, inspection, input handling, and Pi execution using the
      agreed configuration and authority boundaries.
- [ ] Save the result and identify its run and destination to the user.
- [ ] Document setup and demonstrate the complete path from an unrelated
      working directory.
