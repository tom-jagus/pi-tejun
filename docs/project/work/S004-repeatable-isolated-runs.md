---
id: S004
status: Done
parent: B001
depends_on:
  - S002
---

# Make repeated runs, history, and overlaps predictable

## Outcome

Demonstrate that invoking a workflow again does not silently reuse the wrong
context or damage an existing result. Apply the output, history, and overlap
policies agreed in S001 to the execution path delivered by S002.

## Acceptance criteria

- Repeated invocation follows the agreed policy for existing outputs.
- Each run remains identifiable, and earlier results are preserved or replaced
  only according to that explicit policy.
- A run never silently resumes an unrelated interactive Pi session.
- Relevant workflow history is supplied only through the agreed mechanism.
  Execution history remains distinct from domain decisions.
- Overlapping invocations follow the agreed policy and cannot silently create
  conflicting results.
- Tests demonstrate repeat execution, session isolation, output collisions,
  and overlap handling.

## Tasks

- [x] Inspect the shared execution code and coordinate changes with S003. Work
      sequentially unless their shared interfaces are stable.
- [x] Implement the agreed output collision and repeated-invocation behavior.
- [x] Select session context and workflow history explicitly for each run.
- [x] Implement the agreed overlapping-run policy.
- [x] Test repeat execution, unrelated-session isolation, existing outputs,
      history selection, and overlapping invocations.

## Review

All six acceptance criteria pass. Work followed S003 in the shared launcher.
The user accepted the delivered S003/S004 result and requested its documentation
and commit after the separate S001/S002 commit.

- Repeat invocation creates unique run directories, partial reservations, and
  final names. Existing run IDs and partial names are rejected, not replaced.
- Atomic no-overwrite publication preserves an existing final file or symlink.
  Tests confirm earlier results remain intact and independently launched runs
  produce distinct output paths and run identities.
- Each invocation creates a fresh Pi process, conversation, agent name, and
  unfocused pane with explicit resources. Tests check `--no-session`, disabled
  ambient resources, and the absence of resume/continue flags.
- Optional `history_inputs` declares readable files inside the workspace. Only
  their resolved paths are supplied as history, with data-only instructions;
  unlisted files and previous run records are not automatically supplied.
  No digest index or domain-history interpretation was added.
- Unique-output-only runs can overlap. Declared `exclusive_paths` rejects
  shared-file conflicts across processes; session initialization is serialized
  separately. Reservations survive uncertain execution and release only when
  agent startup was not attempted or Pi exit is confirmed.
- Permanent tests cover repeated overlapping launches, separate panes,
  no-overwrite publication, partial and run-ID collisions, explicit history,
  concurrent server initialization, ownership-safe release, and SIGKILL without
  false success or automatic reservation expiry.

The combined suite passes 36 Python tests, Node extension checks, and five
Pi startup probes. An installed CLI and real detached worker pass a disposable
outside-repository integration check using fake Herdr, without model requests
or changes to live sessions. Coordination requires consistent shared-file
declarations and the same local state directory; it is not a filesystem access
control. Recovery and these limits are documented in the
[execution contract](../../manual-execution-contract.md#history-and-overlap-policy).
S004 is Done on the user-accepted result and this review basis.
