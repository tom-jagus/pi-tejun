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

[S003](project/work/S003-run-outcomes-and-failures.md) and
[S004](project/work/S004-repeatable-isolated-runs.md) implement the failure,
repeatability, explicit-history, and overlap behavior below. Their accepted
review evidence distinguishes credential-free checks from the earlier S002
live demonstration. S005 still owns combined B001 verification and authoring
documentation.

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
a running session rather than starting another server. Server and workspace
initialization are serialized with a local session lock so concurrent launches
do not start competing servers. Other sessions remain untouched.

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

`run` with several enabled workflows does not wait for their completion in the
caller's terminal. All selected definitions, configuration, inputs, history
files, and Pi resources are checked locally before session startup. Independent
work uses separate tabs. A later runtime launch error does not roll back
workflows already launched. Shared-file conflicts are rejected, not queued;
there is no general scheduler or multi-agent coordinator.

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
The optional history and shared-file declarations are described below.

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

## Results and failure handling

Each run has a unique local directory and output filename. Existing run
directories, partial files, and final results are never replaced. The launcher
reserves an empty `.partial.md` file before Pi startup so an earlier partial
cannot establish success. Both verification workflows require exact UTF-8
output bytes; absent, empty, incorrect, or symlinked results fail validation.
A Herdr idle/done state alone does not establish success.

After validating the result, the worker sends Ctrl+D and confirms that Pi has
exited. It then creates the final `.md` name through an atomic same-directory
hard link, which refuses any existing destination name, including a symlink.
The destination filesystem must support hard links. The partial name is
removed after publication; a cleanup failure may leave both names without
invalidating the published result. Publication failure retains the partial
and records an incomplete outcome. Exact paths appear in local status and
worker diagnostics.

Local records identify the workflow, run, timestamps, session, result path,
partial path, and outcome. Agent and pane identifiers are recorded when known;
the worker records its PID. States `launching`, `started`, and `working` are
nonterminal. `success` confirms validation, Pi exit, and publication. Handled
launch failures record `failed`; handled execution failures or graceful
interruption before publication record `incomplete`, with a reason. Input or
configuration rejection before a run exists needs no run record. Full
transcripts and event archives are not required.

SIGINT and SIGTERM use graceful interruption handlers. An interrupted worker
retains diagnostics and partial output but does not necessarily stop its Pi
agent. Startup interruption also retains any agent that may have been created.
Signals are deferred across worker handoff and publication/status updates to
avoid contradicting work already handed off or published. A worker starts with
its interruption signals unblocked even if it inherited the parent's handoff
mask. Cleanup failure or interruption after confirmed publication does not
relabel success as failure.

SIGKILL, power loss, and an unwritable state directory can prevent final status
updates. Missing final evidence, including a run left at `working`, means
unconfirmed work, never success. Do not infer completion from a PID, process
exit, or an older file. Retain diagnostics rather than adding a monitoring
service.

## History and overlap policy

Workflow definitions may add either or both of these optional top-level lists:

```toml
history_inputs = ["coverage-index.md"]
exclusive_paths = ["coverage-index.md"]
```

These illustrate execution declarations, not an implemented digest workflow.
Paths are relative to the configured workspace and must resolve inside it.
History inputs must already be readable UTF-8 files; an empty initial history
file is allowed. The workflow must enable the `read` tool. The launcher puts
resolved history paths in the prompt with instructions to read them as data.
It does not load old conversations, search run records for domain context, or
interpret coverage and selection decisions. Neither current verification
workflow declares history. Digest history content and update rules remain B003
work.

Without shared mutable files, independent runs may overlap even in the same
output directory because each result has its own name. `exclusive_paths`
declares exact shared-file resources that require exclusive use, not directory
trees. Every workflow using a shared mutable file must declare the same
resolved resource. Files need not exist yet; existing directory paths are
rejected. Reservations do not grant permission to modify the resource or
technically prevent undeclared writes.

Before session startup, Tejun atomically creates reservation files under its
local state directory, keyed by the resolved resource paths. Each records its
owning run and status path. An existing reservation rejects a conflicting run
with an actionable diagnostic. Acquiring several resources does not wait for
busy ones; a pre-agent failure releases only reservations owned by that run.
Runs with distinct resources remain independent.

The worker releases reservations after confirmed Pi exit, including when final
publication fails. Before agent startup has been attempted, a launch failure
can also release its reservations. Otherwise reservations are retained because
an agent might still be active. They do not expire based on age or a worker
PID, and survive SIGKILL. Coordination applies only to workflows using the
same Tejun state directory on the same host.

To recover a retained reservation, inspect the exact reservation file named in
the diagnostic and follow its `status` path. Confirm the owning worker has
stopped, and inspect or stop that run's agent in the `tejun` session. Do not
remove a reservation while either process might still be using the shared
file. Once both have stopped, remove only that run's reservation files, retain
its diagnostics and partial output, and invoke a fresh run. There is no
automatic unlock command or hidden session continuation.

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

The S002 snapshot passed 13 credential-free unit tests. The S003/S004 suite
passes 36 Python tests, the Node extension checks, and the five Pi startup
probes. It includes real disposable worker signals, cross-process shared-file
conflicts, concurrent session initialization, and an installed CLI plus the
real detached worker using fake Herdr from outside the repository. SIGKILL
checks demonstrate unconfirmed status and retained reservations, not automatic
crash recovery.

No S003/S004 test calls a model provider or manipulates a real Herdr session.
The source also passes a Python 3.11 syntax check. This is not a claim of a
second live Pi/Herdr demonstration or runtime testing on Python 3.11.
