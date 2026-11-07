---
id: S005
status: To do
parent: B001
depends_on:
  - S003
  - S004
---

# Prove another workflow needs no separate entry-point convention

## Outcome

Verify that a second small verification workflow can use the shared interface
without another installation convention. Document supported usage and workflow
authoring, and verify the complete B001 behavior against its acceptance
criteria.

## Acceptance criteria

- A second workflow with different inputs and an output destination can be
  added through the agreed workflow-definition mechanism.
- It uses the existing installation and terminal interface without a bespoke
  launcher or changes to an unrelated repository.
- Discovery, readable definitions, validation, execution, and run-result handling
  apply consistently to both workflows without a separate inspection command.
- User documentation covers setup, invocation, configuration ownership, result
  locations, failures, and repeated runs.
- An authoring example explains how to add a workflow without duplicating
  Kijun standards or storing domain history in Pi Tejun.
- End-to-end verification maps the delivered behavior back to every B001
  acceptance criterion.

## Tasks

- [ ] Add a second verification workflow with different inputs and a declared
      output destination through the shared definition mechanism.
- [ ] Verify both workflows use the same installation, discovery, readable
      definition format, execution, and run-result handling.
- [ ] Check the implementation and write user and authoring documentation,
      including configuration ownership and authority boundaries.
- [ ] Run end-to-end checks and prepare evidence for each B001 acceptance
      criterion without treating child completion as brief acceptance.
