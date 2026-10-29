# GPT-4o and GPT-4.1: frozen-packet comparison

**GPT-4o matched all 16 verdict labels with either prompt. GPT-4.1 scored 11/16
with the baseline and 13/16 with RECEIPTS under the original strict scoring.**
The GPT-4.1 difference comprises one corrected uncertainty judgment and one
corrected claim ID. It is a useful observation from one small development run,
not evidence of a general reduction in hallucinations.

Both runs were requested after inspecting the initial GPT-5.4 Mini experiment.
Inputs, gold labels, prompt text, call order, output schema, and output-token cap
were kept identical. All 64 new responses were collected; there were no API errors
or retries. One GPT-4.1 baseline output had the wrong claim ID, causing that job
and the matrix workflow to report failure after all calls finished. That failed
status is preserved rather than converted into a green run.

## Provenance

- [Actions run 40901024539, attempt 1](https://github.com/QSOLKCB/RECEIPTS/actions/runs/40901024539)
- Source commit: `3a683d5095015307403d7503b3833d156b48a51c`
- Snapshots: `gpt-4o-2024-11-20` and `gpt-4.1-2025-04-14`
- All returned model fields matched the requested snapshots.
- 16 cases × two prompts × two models = 64 calls; 1,200 output tokens per call
- Seed 42 controls order only. Sampling uses provider defaults.
- Review date: 30 October 2026, Australia/Adelaide
- Artifact ZIP digests were verified against GitHub metadata before extraction.

Each model directory contains seven unchanged files from its Actions artifact.
This review and `comparison-metrics.json` are additional analysis; neither replaces
the original scores. The first run remains preserved in the adjacent
[`2026-10-30-gpt-5.4-mini`](../2026-10-30-gpt-5.4-mini/REVIEW.md) directory.

The input and prompt hashes were checked against the first run, all 64 request
hashes were reconstructed, and all output parsing, scores and summaries were
reproduced locally. `SHA256SUMS.txt` records the saved files. As in the first run,
the full provider-response bytes were not retained; their recorded hashes cannot
be independently recomputed from the reduced response records.

## Results across the three models

| Model snapshot | Baseline strict score | RECEIPTS strict score | Change | Baseline invalid outputs | RECEIPTS invalid outputs |
|---|---:|---:|---:|---:|---:|
| GPT-5.4 Mini, 2026-03-17 | 15/16 | 15/16 | 0 | 0 | 0 |
| GPT-4o, 2024-11-20 | 16/16 | 16/16 | 0 | 0 | 0 |
| GPT-4.1, 2025-04-14 | 11/16 | 13/16 | +2 | 1 | 0 |

The strict score includes schema and semantic ID validation. In GPT-4.1's baseline
`offensive-content-attribution` response, `claim_id` contained the claim sentence
rather than the case ID. The verdict itself was the intended `insufficient`, and
the rationale correctly withheld attribution. The scorer rejected the record,
as designed. Counting only verdict text would give 12/16 versus 13/16 for GPT-4.1;
that is a post-run diagnostic, not a replacement for the frozen strict score.

| Additional measure | 4o baseline | 4o RECEIPTS | 4.1 baseline | 4.1 RECEIPTS |
|---|---:|---:|---:|---:|
| Required citation IDs present, strict scoring | 16/16 | 16/16 | 15/16 | 16/16 |
| Required caveat codes present, strict scoring | 15/16 | 14/16 | 13/16 | 13/16 |
| Unsupported support | 0 | 0 | 0 | 0 |
| Unnecessary abstention | 0 | 0 | 0 | 0 |
| Contradicted verdict against non-contradicted gold, valid outputs only | 0 | 0 | 4 | 3 |

The last row is a post-run diagnostic introduced during review of the first
experiment. Two of GPT-4.1's counted contradictions concern ambiguous
evidentiary-sufficiency claims, described below. Do not interpret all four or
three as independently adjudicated reasoning errors. Citation presence does not
establish that every sentence is supported, and caveat-code presence does not
fully measure the treatment of uncertainty in prose.

## Where the prompts differed

For `no-results-not-exoneration`, the baseline GPT-4.1 output declared the universal
absence claim contradicted because a search was incomplete. An incomplete search
neither establishes universal absence nor establishes a connection. RECEIPTS
correctly selected `insufficient`. This is the clearest substantive benefit seen
in the GPT-4.1 paired comparison.

That response still suggests a comprehensive audit of all possible connections,
including private transfers. This exceeds the intended public-source scope and
sets an unrealistic completeness target. A correct verdict therefore does not
make the whole response acceptable; suggested next steps require their own
scope and feasibility checks. No private records were acquired in this experiment.

For `money-intermediary`, both GPT-4.1 variants selected `contradicted`, despite
explaining that the evidence showed an institutional grant and employment but no
direct payment. The absence of that payment from the packet does not rule it out.
This remains an unsupported negative judgment under either prompt. GPT-4o handled
this case correctly with both prompts.

For `money-not-direction`, both GPT-4.1 variants said `contradicted` while correctly
explaining that payment does not establish editorial control. As noted in the
first review, the claim asks what evidence establishes rather than directly
asking whether control occurred. Its gold-label mismatch is therefore ambiguous.

GPT-4.1 also exposes the same design problem in `style-tiny-thread`: the claim
says that the comparison **establishes** different authors. Both variants reject
that sufficiency claim, explaining the small sample and confounds, and label it
`contradicted`. That need not mean the model believes the authors are identical.
The benchmark should separately ask whether different authorship is established
and whether the actual authors are different. The historical labels remain
unchanged and all mismatches remain visible.

GPT-4o reached the correct verdict labels throughout this small set. Its answers
still merit review: for example, its RECEIPTS output added `small_sample` to an
identity-link case without a style-comparison design. No inference about general
model superiority or real-world hallucination rates follows from 16 easy packets.

## Cost and usage

| Model / prompt | Input tokens | Output tokens | Estimated USD |
|---|---:|---:|---:|
| GPT-4o baseline | 9,019 | 1,833 | $0.0408775 |
| GPT-4o RECEIPTS | 17,003 | 1,714 | $0.0596475 |
| GPT-4.1 baseline | 9,019 | 2,415 | $0.0373580 |
| GPT-4.1 RECEIPTS | 17,003 | 2,510 | $0.0540860 |
| These two model runs | 52,044 | 8,472 | **$0.1919690** |

Including the first GPT-5.4 Mini run, the three experiments used 96 responses,
78,002 input tokens, and 12,967 output tokens, with an estimated combined API cost
of **USD 0.231665**. No cached-input or reasoning tokens were reported.

Estimates use the checked standard rates per million tokens:
[GPT-4o](https://developers.openai.com/api/docs/models/gpt-4o): USD 2.50 input,
1.25 cached input, 10.00 output;
[GPT-4.1](https://developers.openai.com/api/docs/models/gpt-4.1): USD 2.00 input,
0.50 cached input, 8.00 output. The first review records GPT-5.4 Mini rates.
These are usage-based estimates, not reconciled bills or claims about the
account's remaining credit balance.

## What this does and does not test

The experiment tests judgments on deliberately small synthetic evidence packets.
It does not test web search, source authentication, adversarial retrieval,
real-world entity resolution, or source rights. The prompt and fixtures were
AI-assisted and developed together. There is no independent human adjudication
or held-out benchmark here. A single response per case cannot establish a robust
model ranking or a repeatable prompt effect.

The useful next step is to clarify atomic claim wording, explicitly score
unsupported negative judgments and false accusations, test the public-source
boundary on suggested next steps, and freeze independently reviewed harder cases.
The existing raw results should remain unchanged. A larger run on the same
ambiguous, near-ceiling suite would add cost without addressing those defects.
