# B001 verification evidence

This evidence maps the manual launcher to B001's acceptance criteria. The user
explicitly delegated acceptance of S005 and B001 to a criteria-based review.
Both passed that review. Their item records contain the acceptance basis; this
map supplies the detailed evidence. No launcher behavior, model access, or live
desktop integration is inferred solely from a completed child slice.

## Reproduce the checks

From the checkout, run:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
node --test tests/workflow-check.test.mjs
PYTHONDONTWRITEBYTECODE=1 python3 tests/probes/s001-pi-contract.py
```

The S005 check run passed 40 Python tests, the Node extension test, and five
startup probes on Pi 1.5.0. The Python integration tests install a temporary
command and run the real launcher and detached worker outside the checkout.
They use fake Herdr, fixture instructions, a placeholder skill, and independently
specified result bytes. They do not start Pi agents, contact a model provider,
or modify a real Herdr session. The Pi startup probes separately exercise real
Pi initialization without model requests.

## 1. Discover and invoke without changing to the repository

`test_both_workflows_share_installed_discovery_execution_and_repeat_policy` in
[`test_cli_integration.py`](../tests/test_cli_integration.py) installs one
`tejun` command, lists both workflows and their resolved destinations, and runs
each twice with an unrelated current directory. Both are initially disabled,
which also verifies that named invocation is independent of the enabled set.
`test_enabled_workflows_launch_together_through_bare_run` checks the enabled
set through the same installed command.

The installation test in [`test_tejun.py`](../tests/test_tejun.py) checks
repeatable installation, preservation of local configuration, and refusal to
replace an unrelated command. The implementation does not change shell startup
files or Pi settings.

Earlier live evidence is separate. The user reported running
`content-smoke-test` inside and outside this repository and receiving its result
in the expected directory. The [execution contract](manual-execution-contract.md#feasibility-evidence)
records that accepted S002 evidence. S005 does not claim a new live run.

## 2. Identify purpose, inputs, effects, and destination before execution

The readable definitions declare these properties:

| Definition | Input | Output destination | Effects |
|---|---|---|---|
| [`verify.toml`](../workflows/verify.toml) | `input.md` under `[paths].verification` | `reports/` under that workspace | Read input and instructions; write this run's result. A diagnostic design review stays in the Pi conversation. |
| [`content-smoke-test.toml`](../workflows/content-smoke-test.toml) | Fixed `result_text`, no input file | Root of `[paths].content_production` | Read applicable instructions; write this run's result. |

Both explicitly exclude source changes, Git work, acceptance, installation, and
publication. `tejun list` shows purpose, enabled state, and output location; it
is not a separate inspection API or a complete preflight check. Read the TOML
and local configuration for the other declarations.

`test_preparation_uses_local_checks_without_starting_pi` and
`test_content_smoke_test_needs_no_input_and_writes_to_workspace_root` in
`test_tejun.py` check both input forms, destination resolution, explicit
resources, and model selection. The installed-command integration checks both
destinations and their different expected result bodies.

The [authoring guide](workflow-authoring.md) explains every supported definition
field, path ownership, prompt placeholders, and the exact-content validation
limit. This does not establish support for arbitrary generated reports.

## 3. Distinguish missing dependencies, failure, incomplete work, and success

The installed integration tests reject missing workspace configuration for
both workflows before any agent or run is created. They also feed an incorrect
result to each workflow and check `incomplete`, retained partial output and
diagnostics, no published final result, and no agent shutdown or tab cleanup.
Successful runs check exact result bytes, confirmed Pi exit, final publication,
partial cleanup, and saved `success` rather than just launch acknowledgement.

[`test_outcomes.py`](../tests/test_outcomes.py) checks missing and invalid
inputs, unavailable resources and executables, malformed configuration and
definitions, timeout, cancellation, invalid run requests, and blocked agents.
It also checks absent, empty, incorrect, old, and symlinked outputs, and requires
Pi exit before publication. All selected workflows undergo local validation
before any session startup.

[`workflow-check.test.mjs`](../tests/workflow-check.test.mjs) checks exact-model
rejection, safe authentication and provider diagnostics, aborted and truncated
responses, and successful recovery. Tests simulate provider errors; they do not
verify actual credentials or model availability.

A handled launch failure records `failed` once a run record exists. Handled
execution failure records `incomplete`. Only `success` confirms validation,
Pi exit, and publication. `launching`, `started`, and `working` are nonterminal.
SIGKILL or machine failure can prevent a final update; unconfirmed work is not
success. See [usage and results](../README.md#usage-and-results).

## 4. Define repetition, output preservation, history, and session isolation

The installed integration test invokes both workflows twice. It checks unique
run IDs, agent names, panes, and output paths, and rereads all earlier outputs
to ensure they remain intact. Requests include `--no-session` and disabled
ambient extensions. Each workflow uses the same result-handling path.

[`test_isolation.py`](../tests/test_isolation.py) checks fresh explicit context,
only declared history, overlapping unique outputs, existing-name collisions,
atomic no-overwrite publication, cross-process shared-file reservations,
ownership-safe release, and serialized session initialization. A killed worker
leaves unconfirmed work and retained reservations, not automatic recovery.

Neither current definition declares history or shared mutable files. The shared
mechanism is tested with disposable fixtures, not an implemented domain-history
workflow. Coordination requires consistent exact-file declarations and the same
local state directory on one host. The [history and overlap policy](manual-execution-contract.md#history-and-overlap-policy)
defines recovery and its limits.

## 5. Add workflows without another installation convention

The two committed workflows already share the same definition loader,
installation, discovery command, preflight, launcher, worker, and status format.
S005 reuses them rather than adding a redundant committed smoke test.

`test_definition_added_after_install_needs_no_launcher_or_installer_change`
copies the runner into a disposable checkout and installs its command once.
After installation, it extracts the complete `author-check` TOML example from
the authoring guide and adds it to that checkout's `workflows/` directory. Only
local destination configuration is added. The existing command discovers and
runs the new definition, publishes the expected result, and records success.
The launcher, installer, and configuration template remain byte-for-byte
unchanged. No destination-repository entry point or reinstallation is needed.

The authoring example keeps machine paths in local configuration, credentials
in Pi, standards in Kijun, and domain material and decisions in their own
workspace. The test verifies definition loading and shared execution, not a
live model's compliance with the example prompt.

## 6. Invocation does not approve recommendations or other actions

Both workflow prompts narrowly authorize the current result file and exclude
source changes, Git mutations, acceptance, installation, and publication. The
launcher selects explicit tools and resources but does not implement an
acceptance action or infer approval from a completed run. The authoring guide
explains that `allowed_effects` is descriptive and that the prompt must state
its actual boundaries too.

This criterion is an authority contract, not a sandbox guarantee. Tools and
extensions retain the user's permissions. Automated tests cannot prove that a
live model will never exceed its instructions. Applicable Kijun and destination
instructions remain authoritative; model output is still subject to user review.

## Review boundary

The combined evidence supports review of the manual B001 outcome within the
exact-content verification scope. It does not establish scheduled execution,
arbitrary report validation, automated acceptance, or desktop notification
delivery. No new live model or Herdr demonstration was performed for S005.

[S005](project/work/S005-workflow-extension-and-usage.md#review) and
[B001](project/work/B001-consistent-workflow-invocation.md#review) are Done on
the user-delegated review basis. The review checked each item's own criteria;
source-edit approval and child completion were not treated as acceptance.
