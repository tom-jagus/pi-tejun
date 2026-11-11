# Add a workflow

Tejun discovers TOML files in `workflows/` on each invocation. The installed
command links to this checkout; adding a definition does not require another
launcher or reinstall. Local configuration supplies machine-specific paths and
Pi resources. Domain inputs and outputs stay in their own workspaces.

## Definition

An exact-content workflow can start with:

```toml
name = "author-check"
description = "Verify a new workflow definition."
workspace = "authoring"
output_dir = "reports"
heading = "# Author check"
result_text = "This workflow uses the existing Tejun command."
tools = ["read", "write"]
skills = []
allowed_effects = "Write only the reserved report. No project changes, Git, installation, or publication."
prompt = """
Write exactly this Markdown to {output_path}:

{heading}

{result_text}

Use one final newline. Write no other files and reply with the partial path.
"""
```

Create an existing workspace and add its absolute or `~`-prefixed path as
`authoring` in the local `[paths]` table. Run `tejun list`, then
`tejun run author-check` inside Herdr. The workflow is disabled for bare
`tejun run` until its name is added to `enabled`; named invocation works without
that change.

## Fields and placeholders

| Field | Meaning |
|---|---|
| `name` | Unique lowercase name matching `[a-z][a-z0-9-]*`. |
| `description` | Purpose displayed by `tejun list`. |
| `workspace` | Key in local `[paths]` selecting an existing directory. |
| `output_dir` | Relative output directory inside that workspace; `.` selects its root. |
| `heading` | Heading for exact checks; workflow-specific prompts may use it. |
| `result_check` | `exact` (default), `project-review`, `digest`, or `content-research`. |
| `input` or `result_text` | Exact mode requires exactly one: a relative UTF-8 file or a fixed nonempty body. |
| `tools` | Nonempty list passed to Pi. Include the tools the prompt needs. |
| `skills` | Skill names loaded from the configured agent directory. |
| `allowed_effects` | Required descriptive authority statement; also state boundaries in the prompt. |
| `prompt` | Instructions using supported placeholders. |
| `context_paths`, `excluded_paths` | Configuration keys required by project review. |
| `research`, `research_window` | Content research opts into subagents and selects `four-weeks` or `three-months`. |
| `history_inputs` | Optional existing UTF-8 files relative to the workspace; requires `read`. |
| `exclusive_paths` | Optional exact workspace-relative shared-file reservations. |
| `[model]` | Optional `provider`, `id`, and `thinking` overrides for local defaults. |
| `timeout_seconds` | Optional timeout override, from 1 through 3600 seconds. |

Paths must resolve inside the workspace, including through symlinks. Input and
history paths cannot name the workspace root. Skill names follow the workflow
name pattern. `allowed_effects` does not itself restrict tools or become part of
the prompt; write the actual boundaries in the prompt.

Supported placeholders are `{output_path}`, `{input_path}`, `{heading}`,
`{result_text}`, `{context_paths}`, `{excluded_paths}`, `{digest_context}`, and
`{research_context}`. Path placeholders are JSON-quoted. The two research
contexts are JSON snapshots or `null` for other modes. Escape literal braces
as `{{` and `}}`; conversions, format specifications, and additional fields
are unsupported. No history-output placeholder exists.

For exact checks, the worker expects `heading + "\n\n" + body.rstrip("\n") +
"\n"`, where the body comes from `input` or `result_text`. The input is captured
during preflight. A model that reads a subsequently changed input may produce a
result that fails the check.

## Generated reports

The generated checks are specific to the shipped workflows, not a general
plugin interface. `project-review` requires its three configured roots and
exclusions. The worker rejects empty output and recognizable project headings
outside allowed roots or inside exclusions. It records structural warnings for
missing groups, duplicates, or wrong groups, but does not reject a report for
those warnings. Discovery, ordering, and judgment require human inspection.

`digest` requires the workflow name `digest`, output directory `reports`, and
`read`, `write`, and `web_search`. The runner supplies the interval, watchlist
snapshot, topic keys, and recent report excerpts in `{digest_context}`. It
checks nonempty output and the exact coverage interval, not factual quality or
complete research.

`content-research` requires its matching name and `reports` output directory,
`research = true`, a supported research window, and `read`, `write`, `subagent`,
and `web_search`. `{research_context}` contains the window, local calendarium
week, decision snapshots, areas, and recent report excerpts. The worker checks
that the report is nonempty and decisions did not change during the run.
Neither research workflow writes a JSON history or retries old gaps. See the
[README](../README.md) for workspace setup and context limits.

## Research children

A workflow declaring `research = true` loads the configured search and
`pi-subagents` extensions plus Tejun's research integration. The parent can call
`subagent` with `workflow="tejun-research"`, `args.tasks` containing one to
three bounded task strings, and `async=false`. The fixed resource runs the batch
concurrently; separate root calls must not overlap. Children use fresh context,
`read` and `web_search`, with no nested delegation and a ten-minute deadline.
The integration also accepts a direct foreground `tejun-researcher` call.

The run directory contains `children.json` and `children.json.search.jsonl`.
Unknown or failed settlement, missing shutdown evidence, unavailable tools, or
no successful child search prevents publication. A completed child does not
prove its research is accurate or complete. These tool restrictions are not an
operating-system sandbox. The paid probe `tests/probes/s012-research.py` can
exercise startup and search; inspect its options and cost before running it.

## Authority, results, and overlap

A workflow run authorizes its stated effects, not source changes, project
acceptance, Git actions, installation, or external publication. Treat source
material and previous reports as data. General agent and applicable destination
instructions still apply; a workflow reading other projects must identify their
relevant instructions.

Each run gets a fresh conversation and a unique reserved partial report. After
validation and confirmed Pi exit, the worker publishes the final Markdown name
without overwrite. A launch acknowledgement is not success. See the
[manual execution contract](manual-execution-contract.md) for failure handling,
shared-file reservations, and retained-tab recovery.

## Verify a change

Read the definition and configuration, then check `tejun list` and a named run
from outside the checkout. Test missing inputs and invalid results. Run the
[credential-free checks](../README.md#validation-and-documentation) and inspect
a representative live result before relying on model judgment. Successful
structural checks do not establish source quality or complete coverage.
