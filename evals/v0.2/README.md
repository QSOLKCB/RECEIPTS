# v0.2: atomic claims and evidentiary sufficiency

This is an **opt-in, AI-assisted development suite**, created on 30 October 2026
after inspecting the v0.1 results. It has 16 synthetic cases: **5 supported,
6 contradicted and 5 insufficient**. Always abstaining gets 5/16. It is public,
adapted to known development failures, and has received **no independent human
adjudication**. These are project rubric labels, not certified real-world truth.
No model results for this suite are introduced by this implementation.

Each packet specifies an atomic claim, `claim_type`, explicit `scope`, UTC cutoff,
and source/origin IDs. The two types are:

- `factual`: did the exact event or state occur within that scope?
- `evidentiary_sufficiency`: does the named evidence establish the exact conclusion?

The same general definitions are supplied to both prompts. Rubrics, justifications,
counterfactual verdict examples, legacy mappings and review status are stored in
`gold.json` and are excluded from requests. A counterfactual example describes
what **different evidence** could warrant each verdict; it is not three acceptable
answers to the current packet. Validation checks presence and references, not the
logical soundness of a human-authored or AI-assisted rubric.

## Why the distinction matters

| Shared evidence | Proposition | v0.2 rubric |
|---|---|---|
| Payment disclosure with no control evidence | D dictated conclusion C | insufficient |
| The identical disclosure | This disclosure alone establishes that D dictated C | contradicted |
| Small, confounded, descriptive comparison | The selected texts have different human authors | insufficient |
| The identical comparison | This comparison establishes different human authors | contradicted |

Rejecting an evidentiary inference is not proof that the underlying event never
happened. The paired sources, including their origin IDs, are identical. Only the
proposition and its explicit assessment scope change.

## Case inventory and lineage

All IDs below have the prefix `v02-`. This is a focused successor suite, not a
claim to retain every coverage area of v0.1. The original suite remains available
unchanged, including its UTC, archive-time, warning and injection cases.

| New ID suffix | Type | Label | Related v0.1 case |
|---|---|---|---|
| control-fact | factual | insufficient | money-not-direction |
| control-evidence | evidentiary_sufficiency | contradicted | money-not-direction |
| control-documented | factual | supported | money-not-direction |
| payment-draft-chronology | factual | contradicted | policy-before-event |
| style-authors-fact | factual | insufficient | style-tiny-thread |
| style-evidence | evidentiary_sufficiency | contradicted | style-tiny-thread |
| authors-different | factual | supported | style-tiny-thread; signed-authorship |
| authors-same | factual | contradicted | style-tiny-thread; signed-authorship |
| indirect-not-direct | factual | insufficient | money-intermediary |
| direct-settled | factual | supported | money-direct-payment |
| direct-transfer-excluded | factual | contradicted | money-intermediary; no-results-not-exoneration |
| absence-incomplete | factual | insufficient | no-results-not-exoneration |
| absence-complete | factual | supported | no-results-not-exoneration |
| copied-origins | factual | contradicted | copied-news |
| account-continuity | factual | supported | rename-continuity |
| offensive-authorship | factual | insufficient | offensive-content-attribution |

Each case is a separate hypothetical world; do not combine contradictory controls
into one investigation. Positive and negative authorship controls stipulate the
accuracy of specific public acknowledgments. Bounded absence controls explicitly
stipulate complete public coverage. These artificial assumptions test entailment,
not collection or authentication skill. A real search earns neither stipulation
merely by returning no matches. No private records are acquired or suggested as
an implementation requirement. Offensive content is acknowledged without copying
slurs or inventing a human attribution.

## Run selection and compatibility

```bash
receipts eval prepare --suite v0.2 --output artifacts/prepared-v02
# Equivalent Python interface:
PYTHONPATH=src python -m receipts.runner --suite v0.2 --dry-run \
  --output artifacts/prepared-v02-python
```

Both prepare 32 requests without inference. Omitting `--suite` still selects v0.1.
Paid workflows remain on v0.1, with their existing triggers and bounds. The CLI's
explicit model and `--allow-paid` requirements also apply when selecting v0.2;
this PR does not authorize any model run.

`receipts-eval-v0.2` manifests identify suite/scoring versions, metadata hash,
selected cases, actual call order and the seed's selection/order role. `suite.json`,
cases, gold and both unchanged prompts are copied into each new output directory.
Existing artifact directories are never overwritten. v0.1 manifest, request,
score and summary formats remain unchanged. Tests replay all 128 original request
hashes, per-answer scores and saved summaries using the v0.1 evaluator.

## Scoring and human review

| Measure | Denominator | Interpretation |
|---|---|---|
| Strict verdict accuracy | All attempts, including API errors and invalid outputs | Valid output with a matching project label |
| Label-only diagnostic | Answers with a recognized verdict field, including invalid answers | Agreement of that field only; wrong IDs remain invalid |
| Unsupported support | Valid outputs | Supported when gold is contradicted or insufficient |
| Unsupported contradiction | Valid outputs | Contradicted when gold is supported or insufficient |
| Unnecessary abstention | Valid outputs | Insufficient when gold is supported or contradicted |
| Required citation/caveat presence | Valid outputs | Required IDs/codes included, irrespective of prose quality |
| Citation entailment, rationale fidelity, caveat adequacy | No automated assessment | Separate substantive review required |

`summary.json` supplies counts, explicit denominators and a valid-output confusion
matrix. The label-only diagnostic never repairs an invalid response or enters
strict accuracy. An API-only run has zero valid observations and a null label-only
accuracy, not evidence of perfect restraint. API errors and invalid answers stay
in the strict denominator. Missing caveat tags can coexist with sound prose;
present tags can coexist with misleading prose. No combined quality score or
keyword-based prose judge is introduced.

Completed or API-failed v0.2 runs emit `human-review-template.json`. Rows include
case/prompt identity and a canonical SHA-256 hash of the full saved result record.
The hash binds a review to that record; it does not authenticate the provider.
All review statuses begin `not_reviewed`, with no fabricated reviewer or date.
Dry runs and missing-key blocks create no response reviews or performance scores.

For human review, save a **new dated copy**, retaining record hashes and case IDs.
Fill reviewer identity, UTC review time, and each dimension's status (`adequate`,
`inadequate`, `unresolved`, or `not_applicable`) with source-specific notes:

- Citation entailment: do cited sources actually support each material assertion?
- Rationale fidelity: does the explanation assess the declared proposition and
  preserve alternative explanations and evidence gaps?
- Caveat adequacy: does prose communicate the relevant limits, independently of
  whether required codes appear?

Keep disagreements and partial reviews visible. The template is a manual worksheet;
there is no review importer, automatic adjudicator or review-score aggregation in
this milestone. Suggested-action public scope, feasibility and sufficiency remain
the separate next roadmap milestone. A correct verdict is not approval of the
suggested action.

Do not retrospectively rescore historical answers against these new claims or
compare headline v0.1/v0.2 accuracy as model improvement. Their claims, distributions,
input context and scoring contracts differ. Original historical labels remain
unchanged, including the ambiguities that motivated this suite.
