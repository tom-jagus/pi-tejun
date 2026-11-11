---
id: S012
status: Done
parent: B004
depends_on:
  - S010
---

# Enable subagent web research in Tejun

## Outcome

Provide the bounded launcher support needed for a Tejun workflow to coordinate
web research with Pi subagents. Demonstrate the integration without delivering
or accepting the content-topic research workflow itself.

## Acceptance criteria

- A workflow can explicitly load the configured `pi-subagents` extension and
  a compatible web-search provider without enabling unrelated extensions for
  existing workflows. Missing resources or required tools fail visibly.
- A research child can use the selected web-search tool with a restricted
  read-only tool and extension loadout. The parent receives its result; child
  completion does not itself prove the research was accurate or complete.
- The launcher does not publish a successful result or close the parent while
  required child work is running or its terminal state is unknown. Failure,
  timeout, cancellation, and cleanup leave an inspectable outcome rather than
  silently losing or misrepresenting child work.
- Configuration identifies machine-specific plugin and provider resources
  without embedding credentials. Existing workflows retain their declared tools,
  permissions, invocation, and result behaviour.
- Credential-free tests and a representative startup and child-tool probe cover
  extension loading, activation and allowlisting, unavailable resources,
  compatible search access, child settlement, and failure handling. Present
  live-probe limits and results for user review.

## Tasks

- [x] Align the integration with the accepted S010 contract and identify the
  smallest supported plugin and child profile configuration.
- [x] Deliver scoped launcher and configuration support without broadening
  unrelated workflows.
- [x] Test parent and child tool availability, lifecycle, failure, and cleanup.
- [x] Present the integration and evidence for acceptance before S011 uses it.

## Review

The user accepted the delivered integration and authorized S011. Workflows
explicitly opt in, load configured plugin resources, and use a fixed foreground
research profile restricted to read and web_search. Retained child and search
receipts prevent publication on missing, failed, or unknown child settlement
and when no child search succeeded. Timeout and cancellation retain the parent
and partials for inspection rather than claiming cleanup or success.

Credential-free Python and JavaScript tests passed. A live Pi probe using
Tejun's prepared arguments returned a child search result and recorded exactly
read and web_search as active child tools. A missing-plugin startup probe
retained an explicit diagnostic. These probes established startup and search
access, not research accuracy. Full terminal integration is exercised by S011.
See tests/probes/s012-research.py for the repeatable paid probe.
