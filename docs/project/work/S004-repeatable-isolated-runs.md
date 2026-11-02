---
id: S004
status: To do
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

- [ ] Inspect the shared execution code and coordinate changes with S003. Work
      sequentially unless their shared interfaces are stable.
- [ ] Implement the agreed output collision and repeated-invocation behavior.
- [ ] Select session context and workflow history explicitly for each run.
- [ ] Implement the agreed overlapping-run policy.
- [ ] Test repeat execution, unrelated-session isolation, existing outputs,
      history selection, and overlapping invocations.
