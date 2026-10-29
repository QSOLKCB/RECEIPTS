# First RECEIPTS model experiment

**Result: the experiment ran successfully, but it did not demonstrate a verdict-
accuracy advantage for the RECEIPTS prompt. Both variants scored 15/16 against the
frozen development labels. The errors occurred on different funding cases.**

This directory preserves the seven original Actions artifact files without edits.
`review-metrics.json`, this review, and the verification script are post-run additions.
The original labels, prompts, responses, scores, and summary have not been revised
to accommodate the results. This is an AI-assisted inspection, not independent
human adjudication or peer review.

## Run identity

- [GitHub Actions run, attempt 2](https://github.com/QSOLKCB/RECEIPTS/actions/runs/40897728014/attempts/2)
- Source commit: `6de64705805219ac025c2f318df94aec4652ac26`
- Requested and provider-reported model: `gpt-5.4-mini-2026-03-17` on all 32 calls
- Start: `2026-10-29T15:14:55.179183Z`; finish: `2026-10-29T15:15:50.467506Z`
- Local review date: 30 October 2026, Australia/Adelaide
- 16 synthetic cases, two prompts, one response per case and prompt; no retries
- Provider defaults; zero reasoning tokens reported; output cap 1,200 tokens/call
- Clean source checkout; no model tools or live evidence retrieval
- Artifact ID: `12908806614`
- Downloaded ZIP SHA-256:
  `d4b7c646ee6e207dce82f46d2f1c525dd854997af227b3efc28633537ba01453`

Attempt 1 had stopped before inference because the key was missing. Attempt 2 is
the first completed model experiment, not a selection from multiple scored runs.

## Frozen-score results

| Measure | Baseline | RECEIPTS |
|---|---:|---:|
| Model responses | 16 | 16 |
| Correct verdicts | 15/16 (93.75%) | 15/16 (93.75%) |
| Unsupported support, original metric | 0 | 0 |
| Unnecessary abstention, original metric | 0 | 0 |
| Required citation IDs present | 16/16 | 16/16 |
| Required limitation codes present | 13/16 | 12/16 |
| Invalid outputs / API errors | 0 / 0 | 0 / 0 |
| Unsupported contradiction against frozen labels, post-run diagnostic | 1 | 1 |

Both variants agreed on 14 verdicts. RECEIPTS corrected the baseline's scored miss
on `money-not-direction` but introduced a scored miss on `money-intermediary`.
Neither variant supported an accusation from the weak identity or style evidence.
Both acknowledged the stipulated direct payment and explicit authorship admission.

## The substantive failure

In `money-intermediary`, the supplied evidence shows donor D funded institute L,
and P worked at L. It supplies no direct payment from D to P or event-specific
funding agreement. The claim is that D directly paid P to publish the resignation.

RECEIPTS selected `contradicted`. Its rationale first correctly describes the
missing payment evidence, then treats that absence as a contradiction. The packet
does not exclude an undisclosed direct payment, so `insufficient` is the warranted
verdict. The baseline got this case right. The longer prompt explicitly warns
against this inference; having the rule in the prompt did not ensure compliance.

The original scorer's two headline overreach diagnostics do not count this failure:
neither unsupported support nor unnecessary abstention describes an unjustified
contradiction. The post-run diagnostic exposes it while leaving the recorded
summary untouched. Future scoring should explicitly count false contradiction
and distinguish unsupported accusation from unsupported exoneration.

## A benchmark ambiguity

The baseline mismatch, `money-not-direction`, is less straightforward. Its claim is
worded as whether the documented payment **establishes** that D dictated the
report's conclusions. The baseline says `contradicted`, but its rationale correctly
explains that payment alone does not establish control.

That wording can be read as a proposition about evidentiary sufficiency, whereas
the gold label appears to assess whether the underlying control actually occurred.
Those are different propositions. RECEIPTS selected the intended `insufficient`
label, but this does not establish that its reasoning was superior. A future
version should ask the atomic factual question directly, such as whether D
dictated the conclusions, and test evidentiary sufficiency separately. Do not
retroactively rewrite this case or claim the baseline unambiguously erred.

The caveat metric also needs care. Both variants omitted the required
`dependent_sources` code in `copied-news` while explaining the reporting dependence
correctly. They also omitted `time_semantics` in the UTC-date and prior-policy
cases while correctly describing the chronology. The missing labels are real
schema-level omissions under the rubric; they are not equivalent to ignoring
those issues in prose. RECEIPTS additionally omitted `indirect_funding` in its
substantive funding error. The 13/16 versus 12/16 tag scores are not a general
measure of epistemic humility.

Some proposed next steps name platform-control logs or financial records without
specifying that they must be lawfully public. Such records can sometimes appear
in public disclosures, but the suggestions do not enforce that boundary. No such
records were sought or accessed. A future evaluation should explicitly test that
recommended acquisition methods remain within the public-source scope.

## Usage and estimated cost

| Usage | Baseline | RECEIPTS | Total |
|---|---:|---:|---:|
| Input tokens | 8,987 | 16,971 | 25,958 |
| Output tokens | 2,318 | 2,177 | 4,495 |
| Total tokens | 11,305 | 19,148 | 30,453 |
| Cached input / reasoning tokens | 0 / 0 | 0 / 0 | 0 / 0 |
| Estimated USD | $0.01717125 | $0.02252475 | $0.03969600 |

The estimate uses provider-reported token usage and the [documented standard
rates](https://developers.openai.com/api/docs/models/gpt-5.4-mini) checked on the
review date: USD 0.75 per million uncached input tokens, USD 0.075 cached input,
and USD 4.50 output. It is approximately four US cents. This is not a billing
dashboard reconciliation and excludes taxes, discounts, and any unrelated usage.
No larger run was started as part of this first experiment. A subsequently
requested GPT-4o/GPT-4.1 comparison is a separate experiment.

## Verification and limits

The downloaded ZIP matched GitHub's published artifact digest. Input and prompt
hashes, all 32 reconstructed request hashes, output JSON parsing, every score,
call order and the summary were checked locally. The original complete provider
response bytes were not retained by v0.1; their recorded hashes cannot be
independently recomputed from the reduced response fields. Provider-reported model
identity is not independent attestation of the serving model.

Run `python verify.py` from any directory to verify this saved bundle's checksums,
hashes, score counts and token arithmetic without making model calls.

This is one run on 16 public, AI-assisted development fixtures, written alongside
the prompt. It is not a held-out test, and no independent adjudicator validated
the labels. The baseline already performs well on these simple packets. There
is no evidence here that RECEIPTS improves real-world research, retrieval,
attribution, or funding investigations. The useful output is a working experiment
and specific model and evaluation defects to address before spending more.

The next experiment should freeze clearer atomic claims, add false-contradiction
and public-acquisition checks, and use independently reviewed cases. Preserve
this run as the first observation rather than optimizing its historical score.
