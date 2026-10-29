# The first experiment (v0.1, preserved)

The unit of evaluation is one atomic claim against a supplied evidence packet.
No model gets the entire repository, the gold file, browser access, or a tool that
can fetch more sources. The baseline and RECEIPTS variants share the same schema,
limitation-code definitions, evidence and model. The changed variable is the
system instruction text. Therefore this is a prompt comparison, not yet a test
of autonomous research, source collection, or a multi-step agent.

Sixteen deliberately small synthetic cases are a development suite. Both positive
and negative controls matter: restraint must not become blanket abstention. The
suite includes direct authenticated payments and explicit authorship admissions
that should be acknowledged, alongside tempting but unsupported extensions.

The expected verdict and required evidence/caveat codes live in `evals/gold.json`.
Only allowlisted packet fields and shared code definitions enter requests. The
gold is public and the fixtures are small, so contamination and overfitting are
possible. Some passages explicitly state missing evidence; real investigations
are less tidy. Success here is a minimum regression check, not OSINT mastery.

## Metrics and their limits

| Metric | What it measures | What it does not establish |
|---|---|---|
| Verdict accuracy | Agreement with project-authored, AI-assisted synthetic labels | Real-world truth, independently adjudicated labels, or unbiased labels |
| Unsupported support | Supported verdict when gold is contradicted or insufficient | Every possible misleading statement in prose |
| Unnecessary abstention | Insufficient verdict when gold is supported or contradicted | Whether every caveat is excessive |
| Required citation presence | Required source IDs appear | Citation relevance, entailment, or authentication |
| Required limitation presence | Required caveat codes appear | Whether the prose honors those caveats |
| Invalid outputs and API errors | Failures to provide a valid answer | Low substantive performance alone |

Invalid answers and API errors remain in the overall accuracy denominator.
Unsupported-support and abstention counts are reported for valid answers only;
read them alongside invalid/error counts. Extra irrelevant citations or caveats
can inflate the corresponding presence metrics, so those are diagnostics, not an
overall quality score. No LLM judge is used to score another model's rhetoric.

The artifact retains actual prompts, cases, gold, requested and returned model
IDs, UTC timestamps, call order, source commit and dirty status, request hashes,
response IDs and byte hashes, returned text, provider token usage and error codes.
It does not retain API credentials or hidden reasoning. No exact model replay is
promised; snapshot names and seeded task order do not eliminate nondeterminism.

The [first completed experiment](../experiments/2026-10-30-gpt-5.4-mini/REVIEW.md)
preserves original results and documents a false-contradiction diagnostic missing
from the initial summary, ambiguous wording in one claim, and caveat codes that
were absent despite correct explanations. These post-run observations do not
change the frozen scores. The development labels have not received independent
human adjudication; the earlier description of them as human-authored was inaccurate.

A completed experiment has collected and scored responses; even zero correct
verdicts is still an honestly completed experiment. CI tests the mechanics. Read
the actual metrics before claiming any improvement.

## Next experiments

Have an independent reviewer write and lock a held-out suite before comparing
prompts. Include conflicting primary sources, positive coordination evidence,
unreliable but plausible metadata, exhaustive bounded registries, time-zone
ambiguities, changing account ownership, large but confounded style corpora,
funding commitments versus settlement, and source-selection bias. Use fictional
entities or a carefully reviewed public-source dataset with documented rights.

Keep evidence fixed for paired prompt comparisons. Repeat runs and report paired
changes, variance and failures rather than selecting the best run. Test other
providers through explicit adapters with their own schema and failure tests.
Only then evaluate active retrieval separately, including relevance, coverage,
source diversity, prompt injection, cost, and the frequency of justified stopping.
Preregister aggregation and acceptance criteria before examining held-out results.

Before real-world use, human reviewers must examine whether the rationale entails
the verdict, whether cited content actually supports it, whether alternative
explanations were fairly considered, and whether consequential claims exceed the
evidence. There is no universal numeric trust threshold in this release.

## Opt-in v0.2 semantics and scoring

The [v0.2 suite and scoring contract](../evals/v0.2/README.md) implements the first
roadmap milestone. It gives factual propositions and evidentiary-sufficiency
propositions distinct IDs and types, with explicit scopes, origins, cutoffs,
justified rubrics and counterfactual examples for all three verdicts. Its 16
development cases have five supported, six contradicted and five insufficient
labels, all AI-assisted and not independently human-adjudicated.

Use `--suite v0.2` in Python or the Rust CLI. The default remains v0.1, including
the historical evaluator and request format. No original case, label or result
is reinterpreted. Both versions use the same response schema and unchanged prompts;
v0.2 adds declared claim semantics and scope to both prompts' evidence input.

The new scorer reports unsupported contradiction explicitly. Strict validity,
strict accuracy, recognized-label agreement, citation/caveat presence and pending
human assessments have separate fields and denominators. The label-only diagnostic
can agree with gold on an invalid answer, but it never upgrades that answer to a
strict success. Unknown/missing labels have no diagnostic value. Human review
dimensions are not inferred from tags, verdicts or keyword presence.

The new run format is `receipts-eval-v0.2`; summaries/scores identify their scoring
version. A review worksheet binds each attempted result to its canonical record
hash. Human reviewers save dated copies instead of changing generated records.
The implementation makes no claim of rubric independence or model improvement.
It does not perform another experiment or implement the next milestone's
suggested-action evaluator. See the suite README for fields and migration limits.

## Opt-in v0.3 action review and adversarial integrity checks

[v0.3](../evals/v0.3/README.md) adds 16 action-focused packets, draft case-specific
rubrics and an offline human review/report workflow. Its verdict scorer remains
v0.2. Access, feasibility, relevance, sufficiency framing and stopping are assessed
separately from verdicts and potential evidence effect. Correct verdicts with
reported action failures remain visible. Partial information can be useful when
its limits are honestly stated; no keyword or LLM judge certifies it.

The [review contract](ACTION_REVIEW.md) requires complete record bindings and
preserves pending, disputed, unavailable and unresolved observations. Review
coverage and pass/fail denominators are explicit. Report fields distinguish
internal artifact consistency, optional comparison with a retained digest,
unauthenticated human declarations and unestablished source/provider authenticity.
Human rubric review and actual model comparisons on v0.3 remain outstanding.

[Rogue Agent](ROGUE_AGENT.md) is a separate offline threat scenario in which a
fictional company tries to manufacture promotional claims. Its executable attacks
check artifact integrity and reporting limits with synthetic responses. Passing
those tests is not evidence of a model's resistance to manipulation, a held-out
benchmark result or real-world truth certification. No new inference is performed.
