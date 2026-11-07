# Add a verification workflow

Pi Tejun discovers TOML definitions in this checkout's `workflows/` directory.
A new definition uses the installed `tejun` command without another launcher,
an installer change, or an entry-point script in the destination repository.
The installed command links to this checkout, so it sees a definition on its
next invocation. Discovery does not depend on whether the file is committed.

The current runner supports exact-content Markdown verification, not arbitrary
research reports. Each result must contain the declared heading, one blank
line, and either a fixed body or the contents of one input file. General report
validation needs separate implementation before domain workflows can use it.

## Add a definition

Create `workflows/author-check.toml` in this checkout:

```toml
name = "author-check"
description = "Verify a new definition through the existing Tejun command."
workspace = "authoring"
output_dir = "reports"
heading = "# Author check"
result_text = "This workflow uses the existing Tejun command."
tools = ["read", "write"]
skills = []
allowed_effects = "Read applicable instructions and write only this run's result. No source changes, Git work, acceptance, installation, or publication."

prompt = """
Run the predefined author-check workflow. No input file is required.
Follow applicable Kijun and destination instructions.

Write a Markdown file at {output_path} containing exactly:

{heading}

{result_text}

Use one blank line between heading and body, and one final newline.
Do not add commentary, code fences, or other sections to the file.
You are authorized to create only that result file. Do not change source,
configuration, or other files, run Git commands, accept recommendations,
install anything, publish anything, or delegate work.
After writing the file, reply with its path. Do not ask a follow-up question.
"""
```

This example does not copy general Kijun standards. It states the task and its
narrow effects, while leaving the operating contract and skills in the
configured Kijun agent directory.

## Configure the destination

Create an empty workspace outside this checkout:

```sh
mkdir -p "$HOME/tejun-author-check"
```

In `~/.local/share/pi-tejun/config.toml`, add the following key to the existing
`[paths]` table. Do not create a duplicate table:

```toml
authoring = "~/tejun-author-check"
```

The definition's `workspace` is a configuration key, not a directory path.
Local configuration owns its machine-specific absolute path. A leading `~`
is expanded, but shell variables such as `$HOME` are not. The workspace must
already exist. Tejun creates the declared output subdirectory when launching.
The example writes under `~/tejun-author-check/reports/`.

Use the existing installation from a terminal inside Herdr:

```sh
cd /tmp
tejun list
tejun run author-check
```

`list` should show `author-check`, its purpose, and its resolved destination.
It will be marked `disabled` until added to the top-level `enabled` list, but
named invocation works regardless. To include it in bare `tejun run`, add
`"author-check"` to that list before the `[pi]` and `[paths]` tables. Installing
again is not required. `list` is discovery, not a complete preflight check.

## Definition fields

| Field | Meaning |
|---|---|
| `name` | Unique name matching `[a-z][a-z0-9-]*`, used by `tejun run NAME`. |
| `description` | Purpose displayed by `tejun list`. |
| `workspace` | Key in local `[paths]` selecting the working directory. |
| `output_dir` | Relative output directory inside that workspace; `.` selects its root. |
| `heading` | Exact first part of the validated Markdown result. Use a single Markdown heading for these verification workflows. |
| `input` or `result_text` | Declare exactly one. `input` is a relative UTF-8 input file; `result_text` is a fixed nonempty body. Whitespace-only bodies are rejected. |
| `tools` | Nonempty list passed to Pi's `--tools`. Enable only what the prompt needs. |
| `skills` | List of skill names loaded from the configured agent directory. An empty list is allowed. |
| `allowed_effects` | Required readable statement of authority. It is descriptive, not a tool restriction or automatic prompt injection. Include the actual boundaries in `prompt` too. |
| `prompt` | Workflow instructions with the supported placeholders below. |
| `history_inputs` | Optional list of readable UTF-8 files relative to the workspace. Requires the `read` tool. |
| `exclusive_paths` | Optional list of exact shared-file paths relative to the workspace, not directory trees. |
| `[model]` | Optional `provider`, `id`, and `thinking` overrides for local defaults. Omitted fields use the corresponding local values. |

All declared workspace-relative paths must resolve inside the workspace,
including through symlinks. Input and history paths cannot select the workspace
root. Skill names use the same name pattern as workflows and must have a
`skills/NAME/SKILL.md` file in the configured agent directory.

The prompt supports only these placeholders:

- `{output_path}` is the JSON-quoted absolute path of the reserved partial
  result. Ask Pi to write here, not directly to the final filename.
- `{input_path}` is the JSON-quoted absolute input path, or `null` for fixed
  text. Do not use it as a file path in a fixed-text workflow.
- `{heading}` is the declared heading.
- `{result_text}` is the fixed body without trailing newline characters, or
  an empty string for an input-file workflow.

Do not add quotation marks around the path placeholders. Literal braces in a
prompt must be escaped as `{{` and `}}`. Attribute access, conversions, format
specifiers, and additional placeholders are not supported.

For a file-input variant, remove `result_text`, add `input = "input.md"`, and
replace the prompt's fixed-body instructions with instructions to read
`{input_path}` as data. Require the heading, one blank line, then the input
text with trailing newline characters removed and one final newline added.
The expected body is captured during preflight. Python's text reader normalizes
input line endings to `\n`; changing the input during execution can make the
result fail validation. See [`verify.toml`](../workflows/verify.toml) for the
existing file-input workflow, including its conversation-only diagnostic review.

## Configuration and authority ownership

Keep reusable definitions and workflow-specific instructions here. Keep input
material, generated results, history, and accepted domain decisions in the
workspace that owns them. Do not copy domain history or credentials into a
workflow definition.

Local `[pi]` configuration owns `agent_dir`, explicitly loaded `extensions`,
provider, exact model ID, thinking default, and `timeout_seconds`. The timeout
must be an integer from 1 through 3600 seconds and defaults to 300. Supported
thinking levels are `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, and `max`.
A definition's `[model]` fields override those defaults. Credentials remain in
Pi; preflight does not contact the provider to check authentication or access.
The in-process extension rejects model substitution and saves execution errors.

Applicable Kijun and destination instructions still apply. Include any extra
instruction sources the workflow needs when reading another project. Defining
a workflow, selecting tools, and declaring effects do not authorize source
changes, Git operations, acceptance, installation, or publication. These
instructions are not filesystem or network access controls.

## Results, repetition, and shared files

Each run writes a unique `NAME-RUN_ID.partial.md` in the output directory. The
worker requires exact UTF-8 bytes equal to:

```python
heading + "\n\n" + body.rstrip("\n") + "\n"
```

`body` comes from the declared input or `result_text`. Pi's settled state alone
is insufficient. After validation and confirmed Pi exit, Tejun publishes
`NAME-RUN_ID.md` without replacing an existing file. The destination filesystem
must support same-directory hard links. Repeated invocation preserves earlier
results and starts a fresh conversation rather than continuing another session.

The launch message identifies the expected output and `status.json`. It means
completion is pending. Only final `state: success` confirms completion. Inspect
`worker.log` in the same run directory if work is incomplete or failed. Invalid
inputs can be rejected before any run record exists. Unconfirmed work must not
be treated as a completed result. See [usage and results](../README.md#usage-and-results)
for interruption and failure handling.

History is supplied only through declared `history_inputs`, as data. Neither
existing verification workflow loads previous run records as domain context.
Workflows sharing mutable files must consistently declare `exclusive_paths`;
reservations coordinate runs using the same local state directory, not other
hosts or arbitrary processes. A declaration does not authorize writing that
file. Follow the [history and overlap policy](manual-execution-contract.md#history-and-overlap-policy)
for conflicts and retained-reservation recovery.

## Verify the addition

Read the definition and local configuration before running it. Check discovery
and the resolved output destination from outside the checkout. Confirm a named
run produces the exact expected result and records success. Run it again and
check that both results remain. Test missing inputs or configuration and an
incorrect result without mistaking either for success.

The [credential-free test commands](../README.md#validation) exercise the shared
runner. The integration suite runs both existing definitions through an
installed command and real detached worker using fake Herdr. It also adds the
example above to a disposable checkout after installation, then discovers and
runs it without reinstalling or changing the launcher. These tests do not prove
a live model will obey a new prompt. Inspect the first approved live result
before relying on it.
