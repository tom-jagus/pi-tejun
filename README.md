# Pi Tejun

![Pi Tejun logotype](images/logotype.svg)

Pi Tejun runs reusable agent workflows with the [Pi harness](https://pi.dev).
It provides a consistent command, isolated runs, and saved results for recurring
project reviews and research. Scheduling is planned, not implemented.

## Get started

You need Python 3.11 or newer, `pi` and `herdr` on `PATH`, an activated Kijun
agent directory, and working Pi credentials. The agent directory must contain
`AGENTS.md`, `extensions/herdr-agent-state.ts`, and the `unslop` skill. Research
workflows also need a compatible Pi web-search extension. Content research needs
`pi-subagents` and its `workflow-resources.js` alongside the extension bundle.

From this checkout:

```sh
python3 install.py
tejun list
```

The installer links `~/.local/bin/tejun` to this checkout and creates
`~/.config/pi-tejun/config.toml` if it does not exist. It reads saved Pi model
defaults and preserves existing configuration. Keep the checkout in place and
ensure `~/.local/bin` is on `PATH`. `TEJUN_CONFIG` selects a different config
file. The installer does not migrate a config from the former
`~/.local/share/pi-tejun/config.toml` location.

Review the local config and set the paths and extensions needed by the workflow
you want to run. `config.example.toml` shows the available settings. Paths below
are examples; adapt them to your machine. Do not duplicate TOML tables.

## Usage

From a terminal inside Herdr:

```sh
tejun list
tejun run digest
tejun run project-review
tejun run content-research
tejun run
```

A named run works even if the workflow is shown as disabled. Bare `tejun run`
launches the workflows in the local `enabled` list, which is empty in the
example config. All selected workflows pass local preflight before any launch.
Read the definitions under `workflows/` for their inputs and boundaries.

Tejun starts or reuses a headless Herdr session named `tejun`. Each run starts a
fresh Pi agent in a workflow-named workspace without changing terminal focus.
The command reports the expected result and `status.json` paths after startup;
that acknowledgement does not mean the work is complete.

Only `state: success` confirms that validation passed, Pi exited, and the report
was published. Inspect `worker.log` and the retained tab when a run is
incomplete. Output is first reserved as a unique `.partial.md`, then published
without overwrite using a same-directory hard link. The destination filesystem
must support hard links. Interrupted or unconfirmed runs require inspection;
interrupting a worker does not necessarily stop its agent. Workflow instructions
and tool selection are not an operating-system sandbox.

## Project review

Configure the existing `[paths]` table:

```toml
project_directions = "~/dev/_projects-directions"
client_projects = "~/dev/clients"
personal_projects = "~/dev/default"
personal_repositories = "~/src/default"
content_production = "~/dev/content-production"
```

The three roots and report destination must exist. The report destination and
`content_production` are excluded from discovery. Tejun lists immediate child
projects and reads their project documentation, not source code or tests.
Personal repositories qualify when they have non-Done briefs. The workflow
prioritizes clients, blockers, and quick wins, and saves a report directly under
`project_directions`.

The runner checks nonempty output and recognizable project path headings against
the configured roots. It warns about missing project groups, duplicate paths, or
wrong groups; these structural warnings do not prevent publication. It does not
prove complete discovery, correct ordering, or useful recommendations. Inspect
reports before acting on them.

## Discovery digest

Configure the search extension and an existing workspace containing a manually
maintained `watchlist.md`:

```toml
[pi]
search_extension = "/absolute/path/to/pi-web-search/src/index.ts"

[paths]
digest_briefs = "~/src/default/digest-briefs"
```

Use top-level `- ` bullets for watchlist entries. An empty file is allowed.
The workflow uses a snapshot of those bullets and does not edit the file.
Reports go under `digest_briefs/reports/`.

The first run researches the preceding 24 hours. Later runs start at the latest
finalized report's run timestamp, with a maximum lookback of seven days. The
report should disclose a capped window and meaningful failed checks. Tejun does
not retry old gaps automatically. An older development may be missed after a
failure or long break.

The agent receives excerpts from up to three recent finalized reports, each
limited to 6,000 characters with a truncation marker. This helps avoid obvious
repeats but is not complete memory. No JSON coverage history is written or
required. Existing history files are left untouched and ignored. The runner
checks that the report is nonempty and states its reserved coverage interval;
that does not prove the research was complete or correct.

## Content research

Configure the search and subagent extensions and an existing workspace:

```toml
[pi]
search_extension = "/absolute/path/to/pi-web-search/src/index.ts"
subagent_extension = "/absolute/path/to/pi-subagents/bundle/index.js"

[paths]
content_production = "~/dev/content-production"
```

Create `pursue.json` and `reject.json` in that workspace. Each must be a JSON
list, which can start empty:

```json
[]
```

A decision entry requires `id` and `subject` strings and may include a `reason`
and a `sources` list of HTTP(S) URLs. Do not duplicate identifiers, subjects, or
source URLs across the lists. Tejun reads but does not change them, and rejects
a report if their contents change during the run.

The workflow researches content leads over a rolling four-week window and a
separate local Sunday-to-Saturday technology calendarium. It uses up to three
recent report excerpts and the decision lists. It does not read the digest,
select topics, prepare content, or publish externally. Reports go under
`content_production/reports/`. Gaps are disclosed in the report, not retried
automatically. No JSON research history is written.

The parent delegates bounded web research to foreground children. Tejun checks
child settlement, child search evidence, unchanged decisions, and a nonempty
report before publication. These checks do not verify sources or editorial
quality. The simplified workflow has credential-free test coverage but has not
yet been assessed through a representative live run.

## Overlap and recovery

A workflow cannot start while its named Herdr workspace has tabs. Successful
runs close their unchanged tab; failed or incomplete runs retain it for
inspection. Close a retained tab only after confirming its agent has stopped.
Different workflows may overlap. Workflow authors can also declare shared-file
reservations; their scope and recovery are described in the
[manual execution contract](docs/manual-execution-contract.md#history-and-overlap-policy).

`TEJUN_STATE_DIR` overrides the local run-state directory, normally
`~/.local/state/pi-tejun`. SIGKILL, machine failure, or an unwritable state
folder can leave a run without a final outcome. Do not treat a partial file or
old report as a newly completed result.

## Validation and documentation

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
node --test tests/workflow-check.test.mjs tests/research.test.mjs tests/research-batch.test.mjs
```

The tests use disposable fixtures and fake Herdr; they do not assess live model
output. Node needs built-in TypeScript type stripping. The optional probes under
`tests/probes/` can contact Pi providers and may incur charges.

- [Workflow authoring](docs/workflow-authoring.md) describes definition fields
  and the available result checks.
- [Manual execution contract](docs/manual-execution-contract.md) describes run,
  failure, and overlap behaviour.
- [Project charter](docs/project/charter.md) and [work index](docs/project/work.md)
  record project scope and current work.
- [B001 verification evidence](docs/b001-verification.md) records historical
  acceptance evidence, not the current list of shipped workflows.
