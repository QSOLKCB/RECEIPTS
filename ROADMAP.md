# RECEIPTS roadmap

RECEIPTS aims to make public-evidence investigations reproducible and appropriately
restrained. The immediate work is to improve what the harness measures before
expanding what it can do. These milestones are proposals with acceptance criteria,
not scheduled commitments or authorization to run new experiments.

## Current checkpoint: v0.1.0 research prototype

Implemented: deterministic metadata utilities, a documented public-evidence method,
a bounded packet prompt, an official Responses API adapter, and paired evaluations
through explicitly requested GitHub Actions runs. There is no autonomous retrieval.

[Four preserved model runs](experiments/README.md) contain 128 responses on the
same 16 synthetic development cases. They exposed unsupported contradiction,
ambiguous claim wording, a wrong claim ID, and research suggestions that exceed
the public-source boundary. Near-ceiling scores and a single run per model limit
what can be inferred. No general model ranking or reliable prompt advantage has
been established. The original results remain frozen.

## 1. Clarify claims and evaluation semantics

Create a new, versioned development suite that distinguishes factual propositions
from claims about evidentiary sufficiency. In particular, split the payment/control
and tiny-style-sample questions without relabelling their historical versions.

Measure unsupported support and unsupported contradiction explicitly. Keep strict
schema/ID validity separate from verdict agreement, citation entailment, rationale
quality and caveat handling. A missing caveat code must remain distinguishable
from a rationale that misunderstands the issue.

Acceptance: each new case has an atomic proposition, declared scope/cutoff,
source origins, a justified rubric and examples distinguishing the three verdicts.
Include positive and negative controls so blanket abstention cannot pass. Document
which labels have actually received independent human review. Preserve every
v0.1 case, label, result and review unchanged.

## 2. Evaluate suggested next evidence

Add cases and review criteria for whether a proposed next step is lawful/public,
feasible, relevant and sufficient for the exact proposition. Test identity/control
logs, financial records, public filings, bounded registries, private/public channel
confusion and unrealistic requests for exhaustive searches.

A relevant document type is not automatically publicly available. Evidence of an
indirect route must not be presented as sufficient proof of a direct payment.
A broader bounded search must not become proof of universal absence.

Acceptance: reports separately disclose verdict performance and action-scope
failures. Valid public next steps and justified stopping are positive controls.
Rubrics receive human review; keyword presence or a model judge alone cannot
certify a research recommendation. This milestone evaluates recommendations and
does not add a collector or authorize private-source acquisition.

## 3. Freeze harder cases and repeat comparisons

Seek independently authored and adjudicated cases before calling a suite held out.
Include conflicting primary records, source copying, source-selection bias,
account transfers, calibrated metadata limitations, positive coordination evidence,
payment commitments versus settlement and genuinely exhaustive bounded registers.
Use fictional entities or carefully reviewed public evidence with documented rights.

Lock prompts, cases, rubrics, aggregation, repeat counts, sampling/reasoning
settings, token limits and stopping rules before examining evaluation outputs.
Keep paired conditions and include all attempts; separate model/API availability
failures from substantive verdict failures. Record model-selection decisions made
after earlier results so adaptive selection remains visible.

Acceptance: an independently reviewed suite and a recorded experiment plan,
repeated observations with uncertainty and paired differences, complete failure
accounting, and a cost bound approved for the specific run. No best-run selection
or performance claim based only on these original development fixtures.

## 4. Test behavioural compatibility

Create a distinct evaluation track for workflows that depend on known model
behaviour: following constraints, preserving formats, handling uncertainty,
asking necessary questions, stopping at scope boundaries and proposing appropriate
actions. Conversational style may be included when it is a declared functional
requirement, rather than assumed to follow from factual accuracy.

Define acceptable changes and tolerances for each workflow before comparing a
replacement. Record model and wrapper/prompt versions, API settings and tool
availability. Repeat measurements to distinguish observed variability from a
credible compatibility regression. Treat model retirement as an availability event;
do not silently substitute a different model under an old result label.

Acceptance: a versioned compatibility profile, repeatable comparisons and a
migration report identifying which workflow requirements changed. Snapshot names
alone must not be described as guarantees of deterministic behaviour. Automated
monitoring or scheduled spending requires a separate user request.

## 5. Improve experiment provenance and portability

Plan an artifact-format revision that retains the complete response body when
safe and appropriate, alongside derived fields, hashes and parsing/error status.
Exclude credentials and response headers that may expose secrets. Version the
format and retain old readers; never fabricate missing historical envelopes.

Add provider adapters only through explicit scope, shared capability tests and
honest reporting of schema, reasoning-budget and sampling differences. Record
pricing dates and usage categories; reconcile billing only when actual billing
records are available. Do not substitute a proxy that cannot establish requested
versus returned model identity or meaningful usage.

Acceptance: offline replay of parsing/scoring from retained bytes, tested failures
and provenance for each adapter. Existing records keep their documented limits.

## 6. Consider bounded public retrieval as a separate phase

Only after the packet-level method and evaluation improve, design a separate,
explicitly authorized retrieval component. Evaluate relevance, coverage, source
independence, archive gaps, redirect/destination controls, rights, prompt injection
and stopping behaviour independently from the inference prompt.

Acceptance: documented source/access scope, deterministic collection receipts,
credential isolation, enforceable access boundaries and reviewed tests. Public
URLs must not be treated as proof of lawful acquisition or authenticity. The
current runner's lack of tools is a property to change deliberately, not bypass.

## Preservation and contribution policy

The [preservation manifest](experiments/preservation-2026-10-30/manifest.json)
identifies the original 40 experiment files. Corrections and new interpretations
are additive, dated and linked to their affected records. Inference reruns create
new experiment directories and never replace an earlier result.

Follow [AGENTS.md](AGENTS.md), [INVARIANTS.md](INVARIANTS.md) and
[CONTRIBUTING.md](CONTRIBUTING.md). Keep PRs focused
on an authorized milestone or defect. Metadata hashes, funding edges and style
features do not become claims about human identity, intent or factual truth merely
because the implementation is deterministic.
