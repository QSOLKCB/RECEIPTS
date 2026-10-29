# GPT-5.3-Codex comparison: plan recorded before inference

Requested by Trent Slade after distinguishing the retired GPT-5.3 Instant chat
model from the coding variant. Target: exactly `gpt-5.3-codex`. This is a test of
the Codex model, not a reconstruction of GPT-5.3 Instant or its ChatGPT behaviour.

## Frozen procedure

- Use the original 16 development cases and gold labels, both original prompts,
  original schema, runner and scorer from commit
  `5ec1a0aa7eb6dd53d576c392de16fef99fa9ec9d` without modifications.
- Make one call per case per prompt: 32 planned calls, seed 42 for task order only.
- Use the official Responses API, `store: false`, no tools or source retrieval,
  and the same 1,200 maximum output tokens per call as the previous experiments.
- Omit explicit reasoning/sampling settings as the existing runner does. Provider
  defaults can differ between models. Inspect returned reasoning-token usage;
  equal token caps do not imply equal visible-answer budgets or equal compute.
- Preserve incomplete responses and validation failures in the primary results.
  Do not raise the budget or retry because an answer scores poorly or is truncated.
  Stop on the first API transport error under the existing runner policy.
- Retain and report requested and provider-returned model IDs. The documentation
  lists `gpt-5.3-codex` without a separate dated snapshot; no immutable model identity
  or independent attestation is claimed.

## Review and reporting

Recompute saved scores, input/request hashes and token usage offline. Preserve the
original artifact files byte for byte. Inspect all model rationales and proposed
next evidence, including unsupported positive or negative claims. Report strict
valid-answer verdict scores, invalid/incomplete outputs, and provider errors
separately. Additional diagnostics must be labelled post-run and cannot replace
frozen scores. Retain the known ambiguous cases (`money-not-direction` and
`style-tiny-thread`) and discuss their wording without silently relabelling them.

Estimate standard token cost at USD 1.75 input / 0.175 cached input / 14 output per
million tokens, based on the official model page checked before this run. This is
not reconciled billing. The directory date follows Australia/Adelaide; execution
timestamps and provenance records use UTC.

This public, AI-assisted development suite has no independent human adjudication,
is not held out, and previously showed ceiling effects. A single run cannot
establish general rankings, a reliable prompt effect, conversational tone, or
behavioural stability over time.

## Official references checked before inference

- https://developers.openai.com/api/docs/models/gpt-5.3-codex
- https://developers.openai.com/api/docs/deprecations

The model is deprecated with a documented shutdown on 1 April 2027. API project
access remains an empirical question for this run.
