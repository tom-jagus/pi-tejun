# Manual execution contract

## Decision status

This contract was agreed in
[S001](project/work/S001-manual-invocation-contract.md) and implemented for the
first manual execution path in
[S002](project/work/S002-first-manual-workflow-run.md). It uses Python,
background Pi TUI execution, workflow-owned Markdown outputs, and Pi exiting
after completion. The user accepted removing the separate inspection command.

During S002, the user replaced the existing `agent` session requirement with a
dedicated Herdr session named `tejun`, started headlessly when needed. The user
verified the current launcher inside and outside the repository and confirmed
that output reached the expected destination. Installation and runnable
verification workflows are available; see the
[setup instructions](../README.md#get-started).

This contract also states the failure, repeatability, and overlap requirements
that S003 and S004 must finish verifying. Their inclusion here does not mean
those slices are complete.

## User interface

```sh
tejun list
tejun run
tejun run content-smoke-test
```

`list` shows recognized workflows, their purpose, enabled state, and resolved
output destinations, or `not configured` when the destination path is absent.
It is not a full dependency or configuration check. `run NAME` launches one
named workflow, including one shown as disabled. Bare `run` launches the
workflows enabled in local configuration. Discovery alone does not enable a
newly added workflow. There is no separate inspection command. Readable workflow
definitions expose purpose, required inputs, allowed effects, and output
destinations before execution.

Normal invocation needs no run IDs, destination flags, or model flags. A shared
user-level launcher works from any directory. Setup must refuse unrelated
existing commands and must not modify shell startup files or Pi settings.

## Launch and completion

Invocation currently requires a terminal inside Herdr. The Python launcher
starts work in the dedicated session named `tejun`, without focusing it or
attaching the caller's terminal. If its server is not running, the launcher
starts `herdr --session tejun server` as a detached process and waits for
readiness. It creates an unfocused workspace if the session has none. It reuses
a running session rather than starting another server. Other sessions remain
untouched.

The command waits for session and Pi startup, then returns a launch
acknowledgement rather than waiting for workflow completion. Acknowledgement
means started, never completed successfully. Immediate launch errors are
returned to the caller. Session startup has a bounded readiness wait and a
local diagnostic log, normally `~/.local/state/pi-tejun/herdr-server.log`.

Each workflow uses a fresh Pi process and conversation in a new, unfocused
Herdr tab. Never submit work into an existing agent or reuse an unrelated pane.
The dedicated session is not a persistent pool of agents.

Launch Pi in normal interactive TUI mode so Herdr's Pi integration can report
its state. A background Python worker submits the predefined workflow, waits for
it to settle, and checks the expected Markdown output. On successful completion,
the worker sends Ctrl+D to exit Pi. It must not close an agent that is blocked,
still working, or missing its expected output; retain diagnostics instead.

Pi does not remain open for follow-up conversation after success. Existing
Herdr/Omarchy plugins display its status; Tejun does not build a second
notification service. The worker records the final outcome and file path in
local status and diagnostic files. It closes a successful workflow's tab only
if that tab still contains just its original pane and no agent. Cleanup errors
do not relabel a validated result as failed. The Herdr session stays running.

`run` with several enabled workflows must not wait for their completion in the
caller's terminal. Independent work can use separate terminals. Workflows that
would conflict at the same output location must not run simultaneously. Do not
build a general queue, scheduler, or multi-agent coordinator.

## Ownership and configuration

- Tracked workflow definitions in Pi Tejun describe the name, purpose,
  instructions, required inputs/context, allowed effects, and Markdown output
  destination. They also define any relevant history and result checks.
- Local configuration supplies machine-specific workspace paths, the Kijun
  agent directory, explicitly loaded extensions, exact model/provider and
  thinking defaults, timeout, and the enabled workflow set. Workflow model
  fields may override the local defaults. The `pi` and `herdr` executables are
  resolved from `PATH`. Normal invocation does not repeat these choices.
- Credentials remain with Pi. Do not copy them into workflow definitions,
  diagnostic records, or version control.
- Domain material, accepted decisions, history, and generated Markdown stay in
  the workflow's destination, not in Pi Tejun.

The implementation uses Python and its standard library, TOML workflow
definitions, and a small Pi extension for exact-model and response-error checks.
A verification definition declares either a relative input file or fixed
`result_text`. Both use exact Markdown validation. Output directories resolve
inside the configured workspace, with `.` selecting the workspace itself.
There is no plugin framework, workflow inheritance, or general templating
language.

## Pi context and authority

Use the activated Kijun operating contract and relevant skills without copying
or weakening them. Explicitly select the workflow's working directory, model,
thinking level, and required Pi resources. Do not derive them from the caller's
current directory or most recent interactive session. Do not silently substitute
a different model when the requested one is unavailable.

Applicable destination and ancestor context instructions must be loaded. A
workflow reading a different project must identify any additional instructions
it needs; Pi does not automatically load every input directory's instructions.
History consists of declared domain inputs, not automatic session continuation.

Only load executable extensions and tools needed for the workflow and Herdr
integration. Do not inherit every personal extension merely for convenience.
Use TUI mode, with the Herdr integration enabled, rather than print/JSON mode.
Submit the fixed workflow prompt through Herdr's agent interface. The launcher
must not interpret its own piped stdin as additional workflow input. Pi retains
the Herdr terminal needed for TUI operation.

Launching a workflow authorizes its declared effects and writing its Markdown,
not source changes, Git mutations, acceptance, installation, or publication.
Workflow instructions and a working directory are not filesystem or network
access controls. Tools and extensions still operate with the user's permissions.

## Results and basic failure handling

The result is a ready-to-read Markdown file in the destination defined by the
workflow. Use a unique output filename for each run so earlier files are
preserved. Internal uniqueness is an implementation detail, not a user-facing
run-management interface. Report the exact result path on completion.

Do not present an absent, empty, partial, or earlier result as newly completed
work. Check that the current run completed and produced a nonempty Markdown
result; use an exact expected result for the verification workflow. Keep partial
output clearly labelled when work fails or is interrupted. A Herdr idle/done
state alone is not proof that Markdown was produced successfully.

Retain a small local status/diagnostic record identifying the workflow, time,
output path, and success, failure, or incomplete outcome. On failure, include a
useful reason and any partial-output location. Full transcripts, event archives,
content-hash manifests, and a cross-directory publication protocol are not
required. A missing completion record means unconfirmed work, not success.

Reject missing dependencies, inputs, or configuration before launching where
possible. Handle execution failure and cancellation without claiming success.
Use focused checks for discovery, launch failure, result validation, repeated
runs, and conflicting output paths, plus one real end-to-end demonstration.
Do not require a live model call for every failure test or build a monitoring
system around the launcher.

## Feasibility evidence

The existing credential-free probe remains useful for Pi startup behavior:

```sh
python3 tests/probes/s001-pi-contract.py
```

Five cases passed on Pi 1.5.0. They cover JSON framing, fresh ephemeral sessions,
selected resources and destination context, ignored project configuration,
system-prompt behavior, and excluding piped launcher input. This is an
investigation fixture, not the runner or a claim that JSON mode is now selected.

At S001, read-only discovery with Herdr 0.9.1 confirmed that an `agent` session
was running.
Its CLI supports explicit session targeting, terminal creation without focus,
and command submission to a specified pane. No terminals or agents were created,
modified, or closed during that discovery.

The installed `~/.pi/agent/extensions/herdr-agent-state.ts` gates its status
reporting on `ctx.mode === "tui"` and skips print, JSON, and RPC sessions. In the
user's manual print-mode tests, both plugins named Herdr showed the agent but
not its working state. A print-mode test produced Markdown and exited; that
verified execution, not usable status reporting.

The user then ran a normal TUI Pi in a new unfocused tab in the `agent` session.
The supplied test submitted the workflow through Herdr, waited for it to settle,
checked for nonempty Markdown, and sent Ctrl+D. The user reported that the plugin
showed the agent, then `working`, briefly `done`, and finally its disappearance,
and confirmed that this was the expected behavior. This is user-reported manual
integration evidence, not an automated launcher test or a separate verification
of desktop notification delivery.

The diagnostic script waited in the caller's terminal. S002 moved that waiting
and shutdown into the background worker. After the user requested the dedicated
`tejun` session and automatic headless startup, the user ran
`content-smoke-test` inside and outside the repository and confirmed the
expected output destination. Two saved successful runs have exact expected
Markdown, the current model-check extension in their launch arguments, and
successful tab cleanup. This is user-reported live execution supported by
saved artifacts, not an automated desktop notification test.

The current credential-free suite passes 13 tests covering installation,
discovery, context preparation, session startup and reuse, detached launch,
result validation, and safe cleanup. The five startup probes also pass. These
checks support S002; they do not establish full S003 failure/cancellation or
S004 collision/overlap coverage.
