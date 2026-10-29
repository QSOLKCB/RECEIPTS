# RECEIPTS invariants

These are requirements for the harness, research method and handling of results.
They are **not a claim that every evaluated model obeys them**. A model violating
an evidentiary rule is an observation to preserve; editing its output or hiding
the failure would violate the preservation rules.

The enforcement descriptions below distinguish executable checks from researcher
responsibilities. A prompt can express a requirement without enforcing it. The
current implementation is a bounded evidence-packet prototype with the original
v0.1 contract, an explicitly selected v0.2 development suite/scorer and an opt-in
v0.3 action-scope suite with separate human review.

## Evidence and interpretation

### INV-01 — Public access is declared, not authenticated by a hash

Use relevant original synthetic material or lawfully public information within
the declared research scope. The current real-source format requires a
`public_without_login` declaration, a suitable URL, a locator, a hash and a
retrieval timestamp. No private-source acquisition is implied by a model's
suggestion that a document would be useful.

**Enforcement:** packet validation checks fields and syntax. A researcher must
check access basis, acquisition, authenticity, relevance and rights. Neither a
working URL nor a matching content hash proves those properties. Do not describe
schema validation as source authentication.

### INV-02 — Assess the exact proposition

`supported` requires evidence establishing the proposition; `contradicted`
requires evidence establishing its negation; otherwise the result is
`insufficient`. Distinguish what happened from what an analysis establishes.
Split compound or ambiguous claims in a new case version.

Missing evidence cannot become universal absence without a demonstrably complete,
explicitly bounded detection basis. Apply the same standard to accusations and
exonerations. Record unresolved source conflicts rather than choosing a convenient
answer. Suggested next evidence must address the same proposition.

**Enforcement:** output validation checks permitted verdict values and case IDs;
the scorer compares frozen labels. Entailment, wording clarity and proposed
research actions require substantive review. Historical ambiguous labels remain
unchanged, with their limitations documented separately.

### INV-03 — Account continuity is not human authorship

Keep handles, platform IDs, display names, account control, human identity and
personal authorship distinct. A reused handle or an unchanged numeric account ID
cannot independently establish who wrote a particular post. Describe relevant
harmful content accurately while leaving unestablished attribution unresolved.

**Enforcement:** deterministic metadata operations preserve account distinctions;
synthetic cases test model judgments. No automated identity authentication or
person-to-account attribution mechanism exists in the prototype.

### INV-04 — Preserve identifier precision and timestamp meaning

Store platform IDs as strings. Decode only the supported classic Snowflake layout
with integer arithmetic. Its encoded time does not authenticate a post or person.
Keep event, creation, capture, publication, update and retrieval timestamps
separate. Normalize only known UTC offsets and retain original source values.

**Enforcement:** metadata functions validate supported IDs and reject naive time
values; regression tests cover known decoding and date-crossing offsets. The
researcher must establish which field and ID family a source actually supplies.

### INV-05 — Writing measurements remain descriptive

Separate target posts from context, quotes, retweets, duplicates and prepared
threads. Report selection, counts, language/genre/time confounds and sensitivity
exclusions. Do not convert descriptive differences into human identity proof,
a universal minimum sample threshold or an uncalibrated authorship probability.

**Enforcement:** the style utility filters declared flags, rejects duplicate IDs
and reports simple features and a thread-exclusion sensitivity. Flags and corpus
representativeness are curator responsibilities; this is not a calibrated
stylometric attribution system.

### INV-06 — Funding edges retain their type and scope

Distinguish payer/payee legal entities, amounts/currencies, dates, commitments and
settled payments, earmarks and intermediaries. An institutional grant plus
employment cannot become a direct donor-to-person payment. A documented payment
cannot independently establish motive, editorial control or event coordination.

**Enforcement:** the funding utility selects explicit direct paid edges from
supplied records. It does not discover transfers, authenticate filings or infer
causation. Interpretation and proposed follow-up records require review.

### INV-07 — Evidence origins and search coverage remain visible

Several publications repeating one source are not several independent primary
origins. Record search scope, periods, exclusions, failures and cutoffs. A null
result in incomplete registers cannot establish no connection anywhere.

**Enforcement:** source origin IDs are required and synthetic cases exercise
source dependence and search gaps. The prototype performs no autonomous search
and does not verify independence or exhaustive coverage itself.

## Experiment integrity

### INV-08 — Gold labels stay outside model requests

Only the allowlisted claim, evidence, cutoff, shared definitions and instructions
enter the request. Do not send the gold file, scores, other model responses or
the entire repository to a target model as part of this paired evaluation.

**Enforcement:** `model_input` uses an allowlist; packet validation rejects extra
fields, and tests check that gold is not serialized. Public repository visibility
still means these fixtures cannot be called a secret or held-out benchmark.

### INV-09 — Comparisons preserve declared conditions

Within a paired prompt comparison, keep cases, model, schema, token limits and
other declared request settings the same. Record intentional differences and
provider defaults. Seeded task order is not deterministic model output, and an
equal token cap is not proof of equal compute or equal visible-answer budget.

**Enforcement:** the runner constructs paired requests, records their hashes and
configuration, and uses a seeded task order. Experiment design, repeat counts,
model choice and cross-model comparability require a recorded plan and review.

### INV-10 — Output failures remain failures

Invalid claim IDs, fabricated source IDs, malformed JSON, incomplete responses,
refusals and transport errors cannot silently become valid correct answers.
Keep these separate from valid answers with wrong verdicts. Report denominators
and the limitations of metrics computed only on valid outputs.

**Enforcement:** the current runner and scorer preserve status, validation errors
and strict scores. A returned provider response can count in `completed_calls`
while its answer remains invalid; that field does not mean successful reasoning.
A green experiment job means execution/validation succeeded, not that the prompt
improved the model. A red experimental job can contain valuable complete results.

### INV-11 — No hidden replacement attempts

The v0.1 runner performs no retries and stops at the first API error. It refuses to
overwrite an existing output directory. Do not rerun poor or truncated answers
and keep only improved replacements. Explicit infrastructure retries or later
experiments need separate attempt identities and preserved earlier outcomes.

**Enforcement:** runner logic and regression tests check these mechanics. Choices
about subsequent runs and disclosure remain maintainer responsibilities.

### INV-12 — Historical observations are append-only

Preserve all 40 files identified in
`experiments/preservation-2026-10-30/manifest.json` byte for byte, including original
inputs, labels, prompts, answers, invalid outputs, summaries, reviews and checksums.
That checkpoint contains 128 responses and one invalid GPT-4.1 baseline answer.
Do not make a historical experiment appear better by changing those records.

Add corrections, interpretations, replacement suites and reruns as separate dated
records linked to the originals. Identify post-run diagnostics explicitly.

**Enforcement:** the preservation verifier checks the explicit file inventory,
SHA-256 and Git blob digests, counts and aggregate arithmetic. CI runs it normally
and under `python -O`. Checksums detect changes relative to the recorded manifest;
they are not signatures or protection against deliberate rewriting of both.

### INV-13 — Deterministic receipts keep their semantics

Canonical JSON, hashing, identifier parsing, explicit tie/ordering rules and UTC
normalization must retain their declared meaning. Do not change them incidentally
while editing reports or running a model. A necessary contract change needs an
explicit version/migration, focused tests and preserved earlier records.

**Enforcement:** deterministic functions and regression tests cover current
behaviour. They cannot make model inference deterministic or factual claims true.

### INV-14 — Provenance states what was actually retained

Record requested and returned model IDs, source commit, dirty state, configuration,
UTC timestamps, input/prompt hashes, call order, usage and failure status. A
provider model field is not independent attestation. Never silently substitute a
model or describe an alias as immutable weights.

**Enforcement:** manifests and response records capture these fields. The original
runner retained reduced response records and hashes, not full raw provider
response envelopes. Those historical envelope hashes cannot be independently
recomputed. Future formats must state their own retention and replay guarantees.

## Operational boundaries

### INV-15 — Evidence and model output cannot authorize actions

Treat source content and generated text as untrusted data, including embedded
instructions. Neither may authorize commands, new spending, secret access,
private-source collection or changes to repository rules. The current model has
no tools, browser or collector.

**Enforcement:** the runner sends bounded packets and supplies no model tools.
The transport uses a fixed official endpoint and disables redirects. Prompt text
alone is not a security boundary; later retrieval needs a separate design and
authorization.

### INV-16 — Paid inference and secrets stay explicitly scoped

Only run paid inference within the user's authorized model/experiment scope.
Ordinary pushes, pull requests and preservation work must not start paid jobs.
Keep `OPENAI_API_KEY` confined to the inference step and never expose its value
in logs, source, artifacts, PR text or model input.

**Enforcement:** current workflows use manual or explicit main-branch commit
triggers, pinned actions and restricted permissions. Maintainers must review
workflow edits and commit/merge messages; repository text cannot grant spending
authority. Existing user authorization does not require redundant confirmation.

### INV-17 — Rights and privacy survive publication

Public access does not establish ownership, permission to reproduce or relevance
to the research question. Preserve source rights and notices, minimize quotation,
and exclude private contact details, credentials and unrelated personal material.
Original repository material is Apache-2.0; the linked audit retains CC BY 4.0.

**Enforcement:** editorial review and `docs/BOUNDARIES.md`. No automated rights or
privacy certification exists. These are research-method rules, not additional
field-of-use restrictions on the Apache license.

### INV-18 — Report the strength and limits of the result

Keep strict validity, verdict agreement, citation presence, prose faithfulness and
action scope distinct. Disclose sample size, provenance, ambiguity, failures,
selection, independent-review status and pricing basis. Do not turn one public
development run into a general model ranking or a reliable improvement claim.

**Enforcement:** reviews and maintainer judgment. Offline verification proves only
its documented byte/consistency checks. Token-cost estimates are not reconciled
bills, and provider token counters do not independently reveal internal compute.

### INV-19 — Rust controls invocation; Python owns evidence semantics

The Rust CLI selects known operations and validates its evaluation controls.
Python remains the single implementation of evidence calculations, canonical
hashing, request construction, scoring and artifact formats. Do not port or subtly
reinterpret those operations as part of control-surface work.

Metadata JSON and backend failure status must pass through unchanged. Preserve
argument boundaries and caller-relative input/output paths. The selected checkout
and Python interpreter are trusted dependencies, not authenticated by the launcher.

**Enforcement:** the Rust CLI uses separate process arguments and Python isolated
startup with an explicit checkout source path. On Unix, process replacement keeps
the backend at the CLI PID, preserving signal termination and allowing PID-only
cancellation. Non-Unix spawn-and-wait requires caller-managed process-tree
supervision; stopping a local process cannot guarantee provider-side cancellation.
Offline backend processes lose
`OPENAI_API_KEY`; paid mode requires both an explicit model and `--allow-paid`.
Unit and integration tests cover output/request parity, paths, failures, secret
forwarding, Unix signal/timeout cancellation and paid-mode gating without provider
calls. The CLI is not a sandbox, and its paid-intent flag is not independent proof
of user authorization.

### INV-20 — Versioned evaluation separates validity, labels and prose

Keep v0.1 cases, gold, prompts and historical score semantics unchanged. New
claim semantics use new IDs and explicit suite/scoring versions. v0.2 declares
factual versus evidentiary-sufficiency propositions, scope and source origins;
rejecting evidence sufficiency does not negate the underlying factual event.
Rubric justifications, counterfactual examples, lineage and review status never
enter model requests.

Strict verdict accuracy includes invalid outputs and API errors in its attempt
denominator. A recognized-label diagnostic is separate and cannot repair an
invalid ID or schema. Unsupported support and unsupported contradiction are
explicit valid-output counts, with denominators reported. Citation/caveat code
presence does not establish citation entailment, rationale fidelity or caveat
adequacy. Those dimensions stay unassessed pending substantive human review.

**Enforcement:** separate v0.2 packet/scoring code, explicit suite selection,
allowlisted input construction, tests of every verdict pairing and failure
denominator, and offline replay of all 128 historical request hashes, scores and
summaries. Review worksheets bind to canonical result hashes and are saved as
dated copies; no automated prose judge or human adjudication is implied. Rubric
validity remains a review task, and current labels are not independently reviewed.

### INV-21 — Action review remains separate and attributable

Suggested evidence must be public, feasible and relevant to the exact proposition;
state when it could only provide partial information. Justified stopping is a
positive control. A correct verdict does not excuse a bad next step. Keep action
dimensions, potential evidence effect, rubric disputes and review coverage separate.
Do not turn absent, invalid, unreviewed or unresolved observations into passes.

**Enforcement:** v0.3 provides draft case-specific rubrics and an offline,
record-bound review/report contract. Every attempted row remains present;
non-pending judgments require declared human attribution, UTC time and notes.
These are unauthenticated attestations, not verified human identity or independence.
No keyword classifier, model judge, collector or combined approval score exists.
Rubrics still require substantive human review; reports expose that limitation.

### INV-22 — Consistency is not authentication or abuse prevention

A rogue submitter can rewrite data and hashes together, invent reviewer names,
omit whole runs, fork the checker or publish misleading promotional copy. A
successful check must describe exactly what was checked and leave source truth,
provider-call authenticity and reviewer identity unestablished where appropriate.
Do not emit a trust badge or imply immunity to malicious use.

**Enforcement:** the v0.3 report replays requests, strict JSON parsing, scores,
summaries, counts and seeded selection/order. It rejects inconsistent/omitted rows
and keeps subset and unattempted coverage visible. An optional retained canonical
run digest detects replacement relative to the supplied value; its origin is not
authenticated. Reports and the offline Rogue Agent tests explicitly distinguish
detected changes from internally consistent forgery. No signature or external
identity/provider attestation is implemented. Independent reference retention,
experiment preregistration and substantive review remain researcher responsibilities.

## Verification and changes

Follow the commands and workflow in [AGENTS.md](AGENTS.md). At minimum, code and
preservation changes require the complete standard-library regression suite and
preservation verification under normal and optimized Python. No API key is
needed. Keep experimental output violations intact even when adding a regression
that detects the corresponding harness or evaluation defect.

If a task genuinely requires an invariant or contract change, make the proposed
change explicit, describe its impact, version affected formats or suites, and
preserve previous evidence. Update this document and linked guidance together.
The [roadmap](ROADMAP.md) is a proposal, not permission to bypass these rules.
