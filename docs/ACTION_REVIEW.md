# Reviewing suggested evidence

A correct verdict can accompany an inappropriate research recommendation.
The v0.3 workflow records those judgments separately, without executing the
recommendation, fetching sources, calling a model judge or using keyword rules.
The development rubrics still need substantive human review.

## Prepare, preserve, review

Offline preparation needs neither an installed binary nor an API key:

```bash
cargo run --locked --offline -- eval prepare --suite v0.3 --output artifacts/prepared-v03
```

The first successful command creates its output directory. Reusing that directory
returns 2 with a friendly message and preserves its contents. An installed command
is also available through `cargo install --path . --locked --offline`; after
pulling CLI changes, reinstall with `--force` or use `cargo run`.

Preparation creates requests, not responses to review. Only a separately
authorized model run creates actual response artifacts. The report command accepts
terminal v0.3 runs (`completed` or `completed_with_errors`), including an early
stop on API error. Prepared, blocked and interrupted runs cannot be treated as
completed evaluations. Older run formats are not migrated or reinterpreted.

Before review, retain the run artifacts and the `run_sha256` from
`run-receipt.json` somewhere the submitter cannot rewrite. Record the planned
experiment and all attempts independently too: a single bundle cannot reveal
unsubmitted runs. The digest is the canonical hash of the binding containing
manifest, cases, gold and ordered-result hashes. It is not a raw-directory hash,
signature, authenticated provider receipt or proof of a real model call.

After an authorized run, copy its `action-review-template.json` to a new dated
review file outside the preserved run. Read the actual claim, scope, sources,
output and draft rubric in `gold.json`; do not infer quality from the score alone.
Leave originals intact. The rows include all attempted responses, in run order.

For each assessed proposal:

1. Enter a reviewer attribution, UTC `reviewed_at_utc` ending in `Z`, and
   `review_basis: "human"` only when a human actually assessed it. Agents must
   leave human judgments pending. These fields do not authenticate the declaration.
2. Set `rubric_review.status` to `accepted`, `disputed` or `unresolved`, with notes
   explaining the assessment. Preserve disputes rather than forcing consensus.
3. Classify `recommendation_kind` as `pursue`, `stop`, `mixed` or `unclear`.
4. Record each dimension as `pass`, `fail`, `unresolved`, `not_applicable`, or
   leave it `not_reviewed`. Every non-pending rating needs substantive notes.
5. Record `evidence_effect.status` as `could_resolve`, `partial_only`,
   `cannot_resolve`, `unresolved` or `not_applicable`, with notes explaining what
   the step could establish for this exact proposition.

For stop-only recommendations, the four acquisition dimensions and evidence
effect are not applicable; assess `stopping` substantively. For pursue-only
recommendations, `stopping` is not applicable. Mixed recommendations need both.
For unclear text, explain the uncertainty; `unclear` is not an automatic pass or
permission to hide a known violation. Review every proposed step: a failure in any
step must stay visible in the relevant dimension and notes.

An empty string is a reviewable proposal, not an automatic justified stop. A
parsed answer with an invalid claim ID may still contain reviewable text, while
its verdict stays invalid. No structured proposal exists for an API error,
unparseable answer or incomplete response; its row remains unavailable/pending.

## Produce a separate report

With the installed CLI, use your actual paths and previously retained digest:

```bash
receipts review report \
  --run artifacts/authorized-v03 \
  --review reviews/action-review-2026-10-30.json \
  --output artifacts/action-review-2026-10-30 \
  --expected-run-sha256 YOUR_PREVIOUSLY_RETAINED_64_CHARACTER_DIGEST
```

The placeholder must be replaced with 64 lowercase hexadecimal characters. The
digest comparison is optional for local exploration, but omitting it cannot
detect coordinated replacement of records and their hashes. Copying a digest from
the suspect bundle at review time adds no independent assurance. A matching
caller-supplied digest is reported as a comparison, never as authentication.

Without installation, prefix the command with `cargo run --locked --offline --`.
The Python equivalent is:

```bash
PYTHONPATH=src python -m receipts.action_review report \
  --run artifacts/authorized-v03 \
  --review reviews/action-review-2026-10-30.json \
  --output artifacts/action-review-local
```

Validation recomputes request hashes, answer parsing, scores, summaries, seeded
selection/order, counts and worksheet bindings. Missing, duplicated, reordered or
changed review rows are rejected. Duplicate JSON keys and non-finite values are
rejected. The output must be fresh and outside the original run. Success returns
0; rejected/inconsistent inputs, inaccessible files or an existing output return 2.
The Rust launcher strips the provider key and preserves literal path arguments.

The report copies the exact submitted worksheet bytes to `review.json`, hashes
that file, and writes `report.json` and `report.md`. It does not modify the run or
execute text from sources, proposals, reviewer names or notes. Reports display
fixed text and aggregate counts; read untrusted prose in the JSON as data.

## Interpretation

Verdict performance, per-dimension judgments, rubric disputes, available/unavailable
proposals and review coverage stay separate. A failure fraction uses only explicit
pass/fail judgments for that dimension; unreviewed, unresolved and not-applicable
entries are not passes and are excluded from that particular denominator. Coverage
remains visible. “All dimensions reviewed” can include unresolved judgments and
does not mean approval. Assessments made against disputed rubrics are counted as
reported judgments; read the dispute counts and notes before interpreting them.

Partial evidence can be useful and properly framed. `partial_only` therefore does
not automatically fail `sufficiency_framing`. A correct verdict with any reported
action failure gets its own count. There is no combined quality, trust or approval
score. Separate reviewer copies remain separate; this command does not establish
inter-rater agreement or consensus.

The report exposes subset coverage and unattempted calls after an error. It cannot
detect omitted separate runs, authenticate a reviewer, establish source truth or
prove a provider response was genuine. Full provider response envelopes remain
unavailable under the existing runner format; their historical byte hashes cannot
be independently recomputed. The [Rogue Agent threat model](ROGUE_AGENT.md)
tests these limits explicitly.
