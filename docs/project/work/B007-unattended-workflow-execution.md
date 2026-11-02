---
id: B007
status: To do
---

# Unattended workflow execution

## Outcome

Enable explicitly approved workflows to run automatically on defined schedules
or events, with results saved in their dedicated locations for review at the
desk. Preserve the same workflow purpose and boundaries as manual invocation
without requiring continuous or off-hours supervision.

## Why

Automation is a core part of Pi Tejun: repeatable work should not depend on the
user remembering to invoke it each time. Some workflows suit schedules; others
should follow an approved event. The appropriate trigger belongs to each
workflow rather than being fixed for the whole collection.

## Boundaries

This brief covers shared automation capability; individual workflow briefs
define their required triggers and constraints. No execution host, scheduler,
plugin, service, frequency, or always-running agent is selected here. Manual
invocation remains independently useful, and individual workflows need not
support every trigger type.

Messaging is excluded for now. Use explicitly approved task-specific authority,
not an inherited interactive session grant or blanket permission. Unexpected
conditions should lead to an inspectable stop or failure rather than expanded
access, unlimited retries, or an indefinite approval dialog. Automation does
not itself approve recommendations, source changes, Git work, or publication.

## Acceptance criteria

- Each enabled automation has an explicit trigger, required inputs, permitted
  effects, output destination, and authority that the user can inspect.
- Scheduled and event-triggered behavior respects any required user selection
  rather than treating the existence of a candidate as approval to proceed.
- Unavailable hosts, missed triggers, repeated events, and overlapping runs
  have defined behavior and do not silently produce conflicting results.
- Success, incomplete output, and failure are distinguishable at the desk;
  stale results cannot be mistaken for a newly completed run.
- Execution has agreed limits and a way to disable it without removing manual
  access to the workflow.
- Enabling automation does not introduce a requirement to supervise or respond
  through a phone or messaging service.

## Open questions

- Which workflow first benefits from unattended execution, and why?
- Where would it run, and what should happen when that machine is unavailable?
- Which events or schedules, retry policies, and execution limits are useful?
- What authority can persist for a task, and what access controls enforce it?
- How should failures, costs, and results be reviewed without creating unwanted
  notifications or another maintenance burden?
