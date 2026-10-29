# v0.4: complex evidence and repeated comparisons

This opt-in development suite adds 16 fictional cases: **5 supported, 5
contradicted and 6 insufficient**. It targets the third roadmap milestone's more
complex evidence situations. Increased empirical difficulty has not been measured.
Cases and draft rubrics are AI-assisted, public and **not independently authored,
human-adjudicated or held out**. No new model results accompany this implementation.

| Case suffix (IDs begin `v04-`) | Verdict | Distinction |
|---|---|---|
| conflicting-balances | insufficient | Authentic primary publications can still disagree about net retained funds |
| correction-precedence | contradicted | An accurate authoritative correction resolves a preliminary paid-status error |
| pledge-versus-settlement | insufficient | Commitment plus an earlier filing does not settle later payment |
| complete-bounded-register | supported | Stipulated complete coverage supports bounded absence |
| settled-direct-payment | supported | A separate institutional grant does not erase a documented direct transfer |
| positive-editorial-direction | supported | Specific public instruction and compliance establish bounded editorial direction |
| documented-account-transfer | contradicted | The same numeric account can have different exclusive human controllers |
| post-transfer-authorship | insufficient | Transfer timing and resemblance do not identify a post's writer |
| copied-company-evidence | contradicted | Three articles can report the same single company trial |
| bounded-independent-replication | supported | Two independent small trials support their bounded observations |
| selected-successes | insufficient | Selected good outputs establish neither complete success nor an actual failure |
| complete-failure-accounting | contradicted | Malformed outputs and refusals cannot vanish from a locked denominator |
| large-confounded-style | insufficient | More text does not eliminate genre and attribution confounds |
| unverified-snowflake | insufficient | Correct integer arithmetic does not authenticate a depicted publication |
| utc-date-boundary | supported | An explicit event-time offset moves the UTC date across midnight |
| capture-versus-creation | contradicted | A later archive capture does not change an established creation date |

Sources are separate synthetic worlds. Authenticity, accuracy, completeness or
independence is stipulated only where stated. These are not assertions about real
people, private records or actual products. Each rubric includes a justification,
three counterfactual verdict examples, action criteria, effect limits and stopping
conditions. New cases have no asserted direct historical case lineage.

## Contracts

Select `--suite v0.4`; the default remains v0.1. The verdict scorer stays v0.2, and
both prompts, the output schema and the shared next-evidence guidance are unchanged.
The new input packets and case IDs are distinct. Existing v0.1–v0.3 fixtures,
rubrics and historical scores are preserved. Do not compare headline scores
across suites as evidence of model improvement.

v0.4 uses strict answer JSON parsing, including overflow rejection. Run artifacts
identify `receipts-eval-v0.4`, suite v0.4 and scoring v0.2, plus a digest of the
executing Python package source files and the Python version. These are local
consistency declarations, not execution attestation or proof of provider origin.
The existing action-review worksheet/report schema remains v0.3 and accepts these
new, record-bound v0.4 runs. No review is fabricated or automatically performed.

To prepare one paired run offline:

```bash
cargo run --locked --offline -- eval prepare --suite v0.4 --output artifacts/prepared-v04
```

To freeze all inputs and a schedule of 2–5 full-suite repeats, use
[`experiment prepare`](../../docs/EXPERIMENTS.md). Repeats vary the case/call order
seed while retaining all 16 cases, model, prompts and output-token cap. This is
repeated observation of a fixed development suite, not new independent case samples.

Substantive independent case authorship/adjudication, an approved costed run plan
and repeated provider observations remain outstanding acceptance work. Passing
software tests does not complete those research tasks.
