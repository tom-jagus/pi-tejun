---
id: S005
status: Done
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

- [x] Add a second verification workflow with different inputs and a declared
      output destination through the shared definition mechanism.
- [x] Verify both workflows use the same installation, discovery, readable
      definition format, execution, and run-result handling.
- [x] Check the implementation and write user and authoring documentation,
      including configuration ownership and authority boundaries.
- [x] Run end-to-end checks and prepare evidence for each B001 acceptance
      criterion without treating child completion as brief acceptance.

## Review

All six acceptance criteria pass. The user explicitly delegated acceptance to
this review if the criteria passed, followed by a commit on `main`.

1. The existing `verify` and `content-smoke-test` definitions provide different
   input forms and output destinations through the same TOML mechanism. S005
   verifies that earlier delivery rather than adding a redundant workflow.
2. Installed-command integration tests run both from outside the checkout.
   A further test adds the authoring example after installation in a disposable
   checkout, then discovers and runs it without reinstalling, changing the
   launcher, or adding an entry point in a destination repository.
3. Both definitions use the same discovery, validation, execution, and status
   handling. Tests check named and enabled-set invocation, successful results,
   missing configuration, incorrect results, and preserved repeated outputs.
   The readable definitions remain the inspection mechanism.
4. The [README](../../../README.md) documents setup, invocation, configuration,
   results, failures, repetition, and overlap recovery.
5. The [authoring guide](../../workflow-authoring.md) documents supported fields
   and a complete tested example. Kijun standards, credentials, machine paths,
   and domain history retain their separate ownership and authority boundaries.
6. The [B001 evidence map](../../b001-verification.md) covers every brief
   criterion. B001 was assessed separately against its combined outcome, not
   accepted merely because its slices were complete.

The review reran all 40 Python tests, the Node extension check, and five Pi
1.5.0 startup probes successfully. Installed integration uses fake Herdr and
real detached workers; no new live workflow or model request was performed.
Exact-content validation and instruction-based authority limits are documented.
No blocking findings or unmet criteria remain. S005 is Done on this delegated
acceptance basis.
