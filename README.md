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

## Get started

You need Python 3.11 or newer, `pi` and `herdr` on `PATH`, an activated Kijun
agent directory, and working Pi credentials. The configured agent directory
must contain `AGENTS.md` and `extensions/herdr-agent-state.ts`; the `verify`
and `project-review` workflows also need the `unslop` skill. The current setup
was checked with Pi 1.5.0 and Herdr 0.9.1.

From this repository, install the user-level command:

```sh
python3 install.py
```

The installer creates `~/.local/bin/tejun` as a link to this checkout. Keep the
checkout in place. On first installation, it creates local configuration at
`~/.config/pi-tejun/config.toml` using your saved Pi provider, model, and
thinking defaults. It also creates a verification workspace with `input.md`.
Existing local configuration is preserved. The installer refuses unrelated
command collisions and does not change Pi settings or shell startup files.

If `~/.local/bin` is not already on `PATH`, add it for the current terminal:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

Existing installations must move their configuration from
`~/.local/share/pi-tejun/config.toml` to `~/.config/pi-tejun/config.toml` before
using the new default. The installer does not migrate the old file. Preserve
its configured workspace paths; moving the configuration does not require
moving reports, verification inputs, or run state. `TEJUN_CONFIG` still selects
an alternative configuration file.

Review the local configuration before running anything. `[pi]` selects the
agent directory, provider, exact model, thinking level, Herdr status extension,
and workflow timeout. Keep credentials in Pi, not in this file. Workflow
`[model]` fields override these defaults. In particular, `verify` currently
selects `openai/gpt-6.1-sol` with `low` thinking; check access before using it.
The simpler `content-smoke-test` uses your local defaults.

For the smoke test, add this entry to the existing `[paths]` table in
`~/.config/pi-tejun/config.toml`:

```toml
content_production = "~/dev/default/content-production"
```

The destination must already exist. Then run from a terminal inside Herdr,
without needing to attach to the workflow session:

```sh
mkdir -p ~/dev/default/content-production
cd /tmp
tejun list
tejun run content-smoke-test
```

Tejun starts or reuses a dedicated headless Herdr session named `tejun`. Each
workflow gets a workspace labelled with its name and a default-named tab. It
creates fresh Pi TUI agents without attaching or changing your terminal's
focus. Launch acknowledgement waits for startup, not for the workflow to finish.

## Usage and results

```sh
tejun list
tejun run content-smoke-test
tejun run verify
tejun run project-review
tejun run
```

`list` shows each workflow's purpose, enabled state, and resolved output
location. `run NAME` can launch a named workflow even when it is shown as
`disabled`. The `enabled` list in local configuration applies only to bare
`tejun run`, which initially selects `verify`.

Read the definitions in `workflows/` before invoking a workflow. They declare
inputs, allowed effects, and output locations. `content-smoke-test` needs no
input file and writes a fixed short Markdown result directly to
`[paths].content_production`. `verify` reads `input.md` under
`[paths].verification` and saves its heading followed by the input text under
that workspace's `reports/` directory. It first produces a longer diagnostic
review in the Pi conversation, not in the output file. You can edit the local
`input.md` to supply different verification text.

Each invocation prints its expected result path and the path to its local
`status.json`, normally under `~/.local/state/pi-tejun/runs/`. A launch message
means completion is pending. Inspect the status file for the final outcome and
`worker.log` in the same run directory for diagnostics. Only `state: success`
confirms completion. A missing final outcome is unconfirmed work, not success.
`TEJUN_CONFIG` and `TEJUN_STATE_DIR` can override the local config and state paths.

Output names include the workflow and a unique run identifier. The launcher
reserves a new, empty `.partial.md` file before starting Pi. After the declared
result check and confirmed Pi exit, it publishes the final `.md` file without
replacing any existing name, then removes the partial name. Publication uses
an atomic hard link in the same directory, so the destination filesystem must
support hard links. Existing run records and partial files are also preserved.
Successful runs close their unchanged workflow tab. Cleanup errors are recorded
without relabelling a published result as failed.

All selected workflows undergo local input, configuration, and resource checks
before session startup. Validation errors return diagnostics without launching
an agent. Handled launch failures record `failed` once a run record exists;
later execution failures record `incomplete`. Blocked or unsettled agents and
invalid results remain available for diagnosis. Session startup diagnostics go
to `~/.local/state/pi-tejun/herdr-server.log` by default.

SIGINT or SIGTERM interruption of the launcher before worker handoff, or of
the worker before publication, records an incomplete outcome where a run
exists. Interrupting the worker does not necessarily stop its Pi agent. After
successful worker handoff, work continues independently of the caller. SIGKILL
and machine failure cannot produce a final status update; a run left at
`started` or `working` is unconfirmed, not successful. Preserve its diagnostics
and partial output until inspected.

Do not treat a partial file, an old output, or a launch acknowledgement as a
newly completed result. The launcher does not accept results or authorize
source changes, Git work, or publication. Workflow instructions are not
filesystem or network access controls.

## Project review

`project-review` reads project documentation and suggests next actions. Add
these entries to the existing `[paths]` table in your local configuration:

```toml
project_directions = "~/dev/default/_projects-directions"
client_projects = "~/dev/clients"
personal_projects = "~/dev/default"
personal_repositories = "~/src/default"
```

Keep the `content_production` entry from setup; that folder and the report
workspace are explicit exclusions. Verify all paths before running. The three
roots and report destination must already exist. Create the destination if
needed, then invoke the named workflow:

```sh
mkdir -p ~/dev/default/_projects-directions
tejun run project-review
```

Existing installations retain their configuration, so editing
`config.example.toml` or reinstalling does not add these keys to your live file.
Named invocation does not require changing `enabled`. The workflow uses local
Pi model, thinking, and timeout defaults.

The review includes immediate projects under the client and personal project
roots. The personal repository root includes only repositories with non-Done
briefs, including Draft. Missing or legacy records under the project roots need
attention rather than automatic migration. Paused projects remain visible.

Reports put clients before personal projects, then blockers and work awaiting
input or review before quick wins and other unfinished work. Within each
category, projects sort oldest first by their newest work-record modification
time, including Done records. This measures filesystem recency, not meaningful
activity. Unavailable dates follow known dates. Each project appears once with
a date and two short bullets identifying the issue and next action.

The report has a dated title, project-group headings, category headings, and
project-path headings. Structural validation checks this format, configured
path membership, duplicates, dates, visible ordering, and brevity. It does not
prove complete discovery, correct classification, or useful recommendations.
Inspect reports before acting on them. No decision-capture or implementation
step is included. Existing project records remain authoritative.

The workflow may list directories, inspect timestamps, read instructions and
project documentation, and write its current result. It must not inspect
source, run project tests, change projects, or perform Git work. Its tools are
not a read-only sandbox. Unreadable roots reject the run rather than imply an
empty group; inaccessible project records must remain visible as uncertainty.

## Discovery digest

`tejun run digest` researches the agreed interests and writes concise English
summaries with dates and source links. It uses the configured Pi model and
thinking defaults, explicitly loads web search, and allows 900 seconds per run.
It does not use subagents or create content assignments.

Add these keys to the existing tables in your local configuration, adjusting
the search extension path for your installed package:

```toml
[pi]
search_extension = "/home/tom/.pi/agent/npm/node_modules/pi-web-search/src/index.ts"

[paths]
digest_briefs = "~/src/default/digest-briefs"
```

Do not duplicate tables or remove existing configuration. The selected search
model must support the extension's search API and have working Pi credentials.
Tejun disables ambient extensions, so installation alone does not enable search.

The workspace must exist and contain `watchlist.md`. Add cases as top-level
`- ` bullets, optionally describing which updates matter. An empty watchlist is
allowed. The workflow reads but does not edit it. From inside Herdr, run:

```sh
tejun run digest
```

Reports go under `reports/`; separate JSON coverage records go under `history/`.
The first run checks the preceding 24 hours. Later runs use the last published
coverage boundary and retry unresolved gaps. Material updates are selected by
significance rather than topic quotas; eight findings is normal guidance, not
a hard limit. Unchanged watchlist cases are omitted.

An empty digest says `No verified updates since the last check.` Incomplete
research adds a brief qualification and retry notice, with detailed reasons in
history. A successful run means valid output was published, not that every
research check succeeded or that all important news was found.

Report and history publication must both complete for success. The history
record contains the report hash. Missing or inconsistent pairs block later runs
with a recovery diagnostic. Preserve the report, partial files, history, and run
diagnostics for inspection; do not fabricate history or advance the boundary to
bypass the check. Coverage records are retained indefinitely initially.

## History and overlapping runs

Every run starts a fresh Pi conversation with explicitly selected resources.
There is no automatic session continuation or loading of previous run records.
Digest history is supplied through its dedicated coverage context. Other
workflow definitions may declare optional, workspace-relative `history_inputs`
files. The launcher checks that they are readable and includes their resolved
paths in the prompt for Pi to read as data. It does not decide what the history
means, maintain a digest index, or update domain decisions.

Different workflows can overlap, including when writing unique reports in the
same directory. A second run of the same workflow is rejected while its named
workspace contains any tabs. An atomic per-workflow lock protects the workspace
check and tab creation. Failed runs retain their tab for inspection; close that
tab before retrying. Do not close an active run merely to bypass this check.

Successful runs close only their unchanged Pi tab. Herdr removes a workspace
when its last tab closes, so the next run recreates it. If other tabs remain,
the workspace remains and blocks another run. Existing unrelated workspaces
and the earlier shared `tejun` workspace are not migrated or closed.

A workflow that shares mutable files must also declare their exact,
workspace-relative paths in `exclusive_paths`. All workflows using the same
shared mutable file must declare it consistently. These are file reservations,
not directory-tree locks or restrictions on tool access. Their complete rules
and recovery procedure are in the
[execution contract](docs/manual-execution-contract.md#history-and-overlap-policy).

Conflicting runs are rejected rather than queued. Reservations are released
after confirmed Pi exit, or after a launch failure before agent startup was
attempted. If an agent might still be running, reservations remain, even after
a worker exits or is killed. Before manually removing a reservation, inspect
its owner record and confirm that both its worker and Pi agent have stopped.
Coordination requires the same Tejun state directory; separate state directories
or hosts do not share reservations.

## Validation

Run the credential-free checks from this repository:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
node --test tests/workflow-check.test.mjs
PYTHONDONTWRITEBYTECODE=1 python3 tests/probes/s001-pi-contract.py
```

The extension tests require Node with built-in TypeScript type stripping. The
Python suite includes disposable subprocess signals, cross-process reservations,
concurrent session initialization, and an installed CLI plus detached worker
using fake Herdr outside the repository. It does not start a real workflow or
contact a model provider.

## Project status and documentation

B001 and its slices S001 through S005 are complete. Manual discovery,
installation, background execution, failure handling, repeatability, and
shared-file coordination are implemented and accepted.

S006 and S007 deliver the accepted `project-review` workflow, specific generated
report validation, and per-workflow workspace isolation. Acceptance includes
successful saved live runs and the user's manual observations; structural tests
are not proof of model compliance. B002 is accepted, with the verification
limitations recorded in its brief.

S008 and S009 deliver the accepted manual `digest` workflow, search integration,
and recoverable coverage history. Acceptance includes an explicit limitation:
non-empty watchlist behaviour has automated evidence but no live demonstration.
B003 awaits separate brief-level review. Scheduled execution and the other
proposed domain workflows remain unimplemented.

- [Workflow authoring](docs/workflow-authoring.md) explains supported definition
  fields, local configuration, exact and generated-result checks, and adding a
  workflow through the existing command.
- [B001 verification evidence](docs/b001-verification.md) maps manual invocation
  behavior and reproducible checks to all six brief acceptance criteria.
- [Project charter](docs/project/charter.md) defines the purpose and boundaries.
- [Manual execution contract](docs/manual-execution-contract.md) records the
  launcher model and manual integration evidence.
- [Work index](docs/project/work.md) lists the briefs and their current status.
- [Work records](docs/project/work/) contain outcomes, acceptance criteria, and
  open questions.
