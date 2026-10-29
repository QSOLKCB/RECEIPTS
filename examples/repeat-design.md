# Offline repeated-comparison design example

Purpose: exercise the freeze/report workflow on the public v0.4 development
suite. The example model ID `offline-placeholder` is not a provider selection.
This file does not authorize spending or assert that any experiment occurred.

Model selection: not yet decided. The repository already contains four historical
model runs; any later choice informed by those results must disclose that history
and the actual selection rationale. Record the exact intended provider model ID
before freezing a plan intended for execution; do not substitute an available
model under a frozen ID.

Review: cases and rubrics are AI-assisted, public and not independently adjudicated.
Human action/prose review is outstanding. This is not held-out evaluation.

Cost: not priced or approved. The tool records maximum calls and output-token caps;
input tokens are also billable. Before any paid experiment, record a dated pricing
basis, input/output assumptions, repeat/call limits, approved budget and the
operator's actual authorization in a new design-note file and freeze a new plan.
The harness does not enforce a currency cap or authenticate that authorization.

Stopping: each run stops at its first API error, with no retries. Preserve every
attempt and interrupted/blocked artifact. Do not replace an unfavourable repeat,
silently resume it, or keep only the best run. Use all 16 cases in every repeat,
the frozen paired prompts, and each slot's recorded seed.

Interpretation: strict verdict outcomes and case/repeat pairing are mechanical
diagnostics. Repeat dispersion is conditional on the same fixed cases. Bounds
for unattempted calls are missing-outcome bounds, not confidence intervals or
evidence of general model reliability. Human judgments stay separate.
