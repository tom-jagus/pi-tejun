---
id: S002
status: Done
parent: B001
depends_on:
  - S001
---

# Discover and run one workflow from any directory

## Outcome

Deliver the first complete manual path through the agreed interface, including
user-level setup, discovery, and execution through Pi. Use a small
verification workflow with explicit inputs and a predictable result, without
implementing the domain outcomes owned by other briefs.

## Acceptance criteria

- After the documented user-level setup, the interface works outside the
  Pi Tejun directory.
- The user can list available workflows. A readable workflow definition and its
  configuration identify its purpose, required inputs, allowed effects, and
  resolved output destination before execution, without a separate inspection
  command.
- The user can supply valid inputs and invoke the verification workflow through
  Pi.
- The run uses the agreed execution context and writes its result to the
  declared destination.
- A successful invocation identifies the result and its associated run.
- Invocation does not treat the generated result as accepted or grant permission
  for source changes, Git operations, or publication.

## Tasks

- [x] Implement the agreed user-level setup and shared terminal entry point.
- [x] Add the verification workflow and its readable definition.
- [x] Connect discovery, input handling, and Pi execution using the
      agreed configuration and authority boundaries.
- [x] Save the result and identify its run and destination to the user.
- [x] Document setup and demonstrate the complete path from an unrelated
      working directory.

## Review

All six acceptance criteria pass. The user confirmed successful execution
inside and outside the repository, then explicitly delegated final acceptance
to this review if the criteria passed.

- User-level setup is documented in the [README](../../../README.md#get-started).
  Installer tests cover repeat installation and command collisions. The
  installed command lists workflows from `/tmp`, and the user demonstrated
  execution outside the checkout.
- Discovery, TOML definitions, and local configuration expose purpose, inputs,
  allowed effects, and resolved output destinations before execution.
- `verify` accepts a local input file. Earlier saved live verification results
  match the heading and input exactly, and preparation tests cover file inputs.
  `content-smoke-test` adds a fixed-output test requiring no input file.
- The current smoke-test runs use the configured working directory, exact
  model selection, Kijun resources, and the model-check extension. Both saved
  outputs match the expected Markdown in `~/dev/default/content-production/`.
  The user approved starting or reusing the dedicated `tejun` Herdr session.
- Launch acknowledgement identifies the pending result and status paths.
  Saved records identify each workflow, run, and successful result; both
  current smoke-test runs also record successful tab cleanup.
- Workflow prompts prohibit source changes, Git mutations, acceptance, and
  publication. Invocation does not accept generated recommendations. These
  instructions are not filesystem or network access controls.

All 13 credential-free unit tests and five Pi 1.5.0 startup probes passed.
Live smoke-test evidence is user-reported execution corroborated by local
status records and exact output checks, not another automated model call.
S003 retains interruption and failure coverage; S004 retains collision,
history, isolation, and overlap coverage. These do not block S002's accepted
manual execution path. S002 is Done on the delegated acceptance basis.
