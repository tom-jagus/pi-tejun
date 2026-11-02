# Pi Tejun

![Pi Tejun logotype](images/logotype.svg)

Pi Tejun is a project for turning recurring agent tasks into reusable workflows
built around the [Pi harness](https://pi.dev). The goal is to define how a task
should run once, then invoke it by name or let it run on an approved schedule or
event, with results saved where they belong.

## The problem

A recurring task involves more than its prompt. Reviewing projects, researching
a topic, or preparing content also requires choosing inputs, supplying context,
setting boundaries, checking earlier results, and deciding where to save the
output. Repeating those instructions in interactive sessions leaves the user
responsible for coordinating each run.

Separate scripts and saved prompts can help, but each can introduce a different
way to start work, manage context, and collect results. Automating them also
raises questions about authority, repeated runs, failures, and supervision.
Pi Tejun aims to make those concerns explicit and consistent across workflows.

## The intended approach

Each named workflow should describe its purpose, required inputs, allowed
effects, and output destination. Shared execution support should make it
possible to:

- Discover and invoke workflows from the terminal without navigating to their
  implementation directories or reconstructing instructions.
- Run suitable workflows on approved schedules or events, within defined
  authority and execution limits.
- Save results in known locations, with successful, incomplete, and failed runs
  clearly distinguishable.
- Use relevant history without silently resuming an unrelated interactive
  session or repeatedly ignoring earlier user decisions.

The same workflow boundaries should apply whether a run starts manually or
automatically. Routine work should not require continuous supervision, and
results should be available for review at the desk.

Initial use cases include cross-project reviews, sourced discovery digests,
content-topic research and preparation, and exploration of recording analysis
and editing assistance. These are individual workflows, not a required pipeline.

## What belongs here

Pi Tejun owns reusable workflow definitions, workflow-specific instructions,
and shared execution support. Research, generated results, and user decisions
stay in their dedicated project or content locations.

The separate Pi-Kijun project defines the authoritative Pi harness setup and
general working standards. Pi Tejun uses that setup rather than duplicating it.
Automation does not itself authorize source changes, project acceptance, Git
operations, or publication.

## Project status and documentation

The project is in planning, with seven accepted briefs awaiting refinement and
implementation. No runnable workflows are available yet.

- [Project charter](docs/project/charter.md) defines the purpose and boundaries.
- [Work index](docs/project/work.md) lists the briefs and their current status.
- [Work records](docs/project/work/) contain outcomes, acceptance criteria, and
  open questions.
