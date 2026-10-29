# Frozen repeated comparisons

`receipts experiment prepare` freezes a v0.4 paired-comparison design before
observations, and `receipts experiment report` checks submitted terminal runs
against that design. **Both commands are offline.** They neither launch paid calls
nor authorize them. Existing `eval run` remains the separate inference entry point.

The workflow exposes missing repeats, invalid outputs, API stops, incompatible
conditions and paired differences. It cannot discover unsubmitted attempts,
authenticate an externally retained digest, prove that timestamps are honest or
turn public AI-assisted labels into independently adjudicated truth.

## Prepare an offline design

From a trusted checkout with the pinned Rust toolchain and Python 3.10+ available:

```bash
cargo run --locked --offline -- experiment prepare \
  --model offline-placeholder --repeats 3 \
  --notes examples/repeat-design.md \
  --output artifacts/repeat-plan
```

This prepares **96 calls, zero attempted**, using the example's explicitly unpriced,
unauthorized model placeholder. It is useful for inspecting the workflow. For a
future real experiment, write your actual model-selection rationale, dated pricing
basis and assumptions, cost bound, authorization and review status in a separate
notes file, select the exact intended model, and create a new plan. The tool
preserves the notes verbatim; it cannot authenticate their declarations or infer
a credible budget from arbitrary prose.

Required options are `--model`, `--repeats` (2–5), `--notes` and fresh `--output`.
Optional `--seed` defaults to 42 and `--max-output-tokens` defaults to 1200 within
256–2048. The seed must allow all repeat seeds to fit unsigned 64-bit range.
All 16 cases are included in each repeat, so 64–160 calls are planned. Input tokens
are also billable: the output-token ceiling is **not a currency cap**.

The directory contains:

| File | Purpose |
|---|---|
| `plan.json` | Actual cases, gold, suite metadata, both prompts, notes, model, token limits, repeat schedule, policies, UTC creation time, Python version and source digest |
| `plan-sha256.txt` | Canonical JSON hash of the full plan |
| `requests.json` | Exact request payloads for inspection, grouped by repeat; no gold or design notes are sent to a model |
| `run-index-template.json` | Every planned repeat, initially unavailable/not submitted |

The source digest covers the executing `src/receipts/*.py` files by filename and
byte SHA-256, using the existing canonical hash operation. It does not cover the
interpreter binary, installed OS or provider. Plan replay requires the same Python
version and package source snapshot. Keep that trusted checkout available; do not
pull implementation changes into it mid-experiment. The digest is a consistency
check, not authenticated execution provenance.

Retain the plan and its digest in a location outside the submitter's control before
any calls. A same-folder checksum is not independent preregistration. Editing the
plan, prompts, labels or notes requires a new plan and a separate retained digest.
The report checks that run timestamps follow the plan, but those timestamps are
self-reported and do not establish external preregistration.

## Run only a separately authorized experiment

There is deliberately no `experiment run` command. Once an actual model, costed
scope and operator authorization are established, the existing `eval run` can
collect each planned repeat in a fresh directory. Match the plan's model, all
16 cases, token cap and the slot's seed. For repeat number `r`, the seed is
`base_seed + r - 1`; it varies case/call order, not provider sampling.

For illustration only, after authorization, replace both placeholders with the
exact frozen values and use a fresh output path:

```bash
receipts eval run --suite v0.4 --model YOUR_FROZEN_MODEL_ID \
  --cases 16 --seed YOUR_SLOT_SEED --max-output-tokens 1200 \
  --output artifacts/repeat-01 --allow-paid
```

Use the plan's actual token cap if it differs from 1200. This command does not read
or preflight the plan itself; verify its inputs before spending. The comparison
report rejects mismatched conditions afterwards. No new scheduler, retry loop or
paid GitHub workflow is added. Keys stay in the established environment/secret
mechanism, never in arguments or design notes.

Every run stops at its first API error. Preserve invalid answers, refusals,
incomplete responses and the error record. Never replace an unfavourable repeat
with a new attempt. If infrastructure prevents a repeat, preserve its partial
artifacts and disclose it in the index. Additional attempts require a separately
declared design; this first contract does not merge retries into original slots.

## Index all repeats and report

Copy `run-index-template.json` to a new index outside the frozen plan. Do not delete,
duplicate or reorder rows. For a submitted terminal run, set `run_directory` to its
path, `unavailable_reason` to `null`, and record useful notes. Relative run paths
are resolved against the **index file's directory**, not the shell's directory.

For an unavailable repeat, retain `run_directory: null`, choose `not_run`,
`not_submitted`, `blocked` or `interrupted`, and explain it in `notes`. Keep any
blocked/interrupted artifacts separately and record their location in those notes.
These reasons are operator declarations, not verified diagnoses. The comparison
does not reinterpret partially written directories as terminal runs.

```bash
receipts experiment report \
  --plan artifacts/repeat-plan/plan.json \
  --runs reviews/repeat-index.json \
  --expected-plan-sha256 YOUR_PREVIOUSLY_RETAINED_64_CHARACTER_DIGEST \
  --output artifacts/repeat-comparison
```

The expected digest is required and must be 64 lowercase hex characters. Supplying
a newly computed digest from a suspect plan does not create independent assurance.
The report directory must be fresh and outside the plan directory and all submitted
runs. Copying a run into another repeat cannot satisfy the locked seed/order and
snapshot checks. All observations must match the plan's full case set, rubrics,
prompts, model, cap, source digest, Python version and provider settings. Submitted
results must also pass normal run replay: counts, request hashes, response parsing,
scores, summaries and call order.

The output preserves exact submitted `plan.json` and `run-index.json` bytes and
writes `report.json` plus a readable `report.md`. Original runs remain unchanged.
Success returns 0; invalid/incompatible inputs, inaccessible files or existing or
protected outputs return 2. No untrusted text is executed. The Rust launcher
strips `OPENAI_API_KEY` for both experiment operations.

## What the arithmetic means

Each `(case, repeat)` has a baseline and RECEIPTS slot. A valid correct verdict is
1; an observed wrong verdict, invalid output or API error is 0 for strict success.
An unattempted/unsubmitted call is **unknown**, not an invented success or failure.
The paired difference is RECEIPTS minus baseline, in `{-1, 0, 1}` when both calls
were observed. Ties include both-correct and both-non-success outcomes; inspect
the separate accuracy/failure counts and per-case rows.

The primary mean difference over **all planned pairs** is present only when every
planned pair is observed. Otherwise it is `null`. The report separately labels a
mean over observed pairs as a partial diagnostic; it must not be promoted as the
complete planned experiment's result.

For unknown calls, the report calculates the lowest and highest possible mean
under binary strict outcomes. For example, two unknown outcomes permit a paired
difference from -1 to +1. These are missing-outcome bounds, **not confidence
intervals**. Fully observed repeats also have individual differences, minimum,
maximum, mean and sample standard deviation when at least two exist. That is
descriptive run variability on the same 16 cases; incomplete-repeat selection can
bias it. The cases are reused, so repeated calls are not independent new case
samples and no population confidence or significance claim is produced.

Multiple/missing returned model IDs and differences from the requested ID are
reported as comparability warnings. Provider IDs are not independent model
attestation; an alias does not guarantee the same underlying behavior.

Verdict arithmetic does not assess citation entailment, rationale quality, action
scope, rubric validity or human independence. Keep separate bound action/prose
reviews. Independent authorship/adjudication, approved costed live experiments and
the resulting provider observations remain outstanding roadmap acceptance work.
