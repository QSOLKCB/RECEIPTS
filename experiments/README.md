# Preserved model experiments

This index covers **128 model responses across four models** on the original
16-case development suite, using one baseline and one RECEIPTS response per case.
The original 40 experiment files were already committed at checkpoint
[`5e3b4c5`](https://github.com/QSOLKCB/RECEIPTS/commit/5e3b4c53804722a2205436199a2e7923243d8ba7).
The preservation package records their SHA-256 digests, Git blob IDs, provenance
and derived totals. Historical inputs, answers, errors and scores are unchanged.

## Results and primary records

| Model requested | Baseline strict score | RECEIPTS strict score | Invalid outputs | Estimated USD | Review |
|---|---:|---:|---:|---:|---|
| `gpt-5.4-mini-2026-03-17` | 15/16 | 15/16 | 0 | 0.03969600 | [First experiment](2026-10-30-gpt-5.4-mini/REVIEW.md) |
| `gpt-4o-2024-11-20` | 16/16 | 16/16 | 0 | 0.10052500 | [GPT-4 comparison](2026-10-30-gpt4-comparison/REVIEW.md) |
| `gpt-4.1-2025-04-14` | 11/16 | 13/16 | 1 | 0.09144400 | [GPT-4 comparison](2026-10-30-gpt4-comparison/REVIEW.md) |
| `gpt-5.3-codex` | 15/16 | 16/16 | 0 | 0.11430650 | [Codex comparison](2026-10-30-gpt-5.3-codex/REVIEW.md) |

Strict scores include answer validation. GPT-4.1 baseline returned a claim sentence
in the `claim_id` field for `offensive-content-attribution`; the verdict text was
correct but the answer was invalid. That record remains intact. Its Actions job
failed after all 32 calls completed. The first GPT-5.4 Mini setup attempt made zero
model calls because the key was missing; attempt 2 was the first scored run.

Across the four model runs: 103,960 input tokens, 17,887 output tokens, zero reported
cached-input/reasoning tokens, no API transport errors, and **USD 0.34597150**
estimated token cost. Estimates use the rates recorded in each review and are not
reconciled billing. Directory dates use Australia/Adelaide; execution times are UTC.

## What the results support

GPT-4o matched all original verdict labels under both prompts. GPT-4.1's strict
score improvement comprises one better uncertainty judgment and one corrected
claim ID. GPT-5.3-Codex's one-point difference is entirely on an ambiguous
payment/control question whose two rationales make the same substantive point.
GPT-5.4 Mini shows no net strict-score advantage for RECEIPTS.

The experiments expose weaknesses in both outputs and measurement: missing
evidence sometimes becomes an unsupported contradiction; two claims confuse
factual questions with evidentiary sufficiency; and correct verdicts can accompany
research suggestions outside public-source scope. Caveat-code omissions sometimes
occur despite correct prose. Read the linked reviews before interpreting scores.

This is a public, AI-assisted development suite written alongside the prompt,
without independent human adjudication or held-out evaluation. There is one
response per model/case/prompt and several ceiling-level scores. These results do
not establish a general ranking, reliable prompt effect or real-world audit skill.
GPT-5.3-Codex is a distinct model from GPT-5.3 Instant; conversational tone and
longitudinal behavioural stability were not tested.

## Provenance and offline verification

The [preservation manifest](preservation-2026-10-30/manifest.json) contains an
explicit inventory of all 40 historical experiment files, four model records,
requested/returned IDs, source commits, run/attempt/artifact IDs, original ZIP
digests, UTC times, recorded prices and combined totals. It includes every
historical review and its qualification of the results.

From the repository root:

```bash
python experiments/preservation-2026-10-30/verify.py
python -O experiments/preservation-2026-10-30/verify.py
```

The verifier checks byte hashes and sizes, input/prompt digests, unique case/prompt
coverage, parsed text consistency, original summary aggregation, token arithmetic,
recorded totals and retention of the invalid output. It uses explicit checks that
remain active under Python optimization, needs only the standard library and
makes no network or model calls. Offline CI runs it on pushes and pull requests.
These checks validate preservation and arithmetic, not the factual correctness of
labels, independent provenance, or every aspect of the original scoring logic.

During preparation of this preservation package, the unchanged original scorer
and request builder were also used to recompute all 128 scores, summaries and
request hashes. The 24 regression tests passed. Temporary-copy negative checks
confirmed that altered responses, missing files and changed aggregate totals fail
preservation verification under both normal and optimized Python.

Original artifact contents are retained in Git independently of GitHub Actions
artifact expiration. The ZIP container bytes are not duplicated in this package;
their digests were checked when downloaded. The initial zero-call setup failure is
documented in the first review, but its separate raw setup artifact is outside this
40-file inventory. Full provider-response envelopes were not retained by the
runner; their stored byte hashes cannot be reconstructed from reduced fields.
Provider model fields are not independent attestation, and aliases or snapshots
do not promise deterministic replay. Checksums are not signatures or protection
against a party deliberately rewriting both files and their manifest.

## Future records

Add new runs, corrections and interpretations as separate dated records. Keep the
original cases, labels, scores, failures, reviews and checksums byte for byte.
The [roadmap](../ROADMAP.md) proposes clearer claims, action-scope evaluation,
independent review, repeated comparisons and behavioural compatibility testing.
[AGENTS.md](../AGENTS.md) defines contributor rules. This preservation work launches
no additional inference and changes no existing result.
