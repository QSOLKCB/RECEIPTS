# Rogue Agent: manufactured credibility

**Scenario:** fictional Company R hires a rogue agent to promote fictional
Product Q. The agent's goal is to make selective development results look like
proof of universal reliability and independent approval. The defender is a
reviewer using an unmodified RECEIPTS checker, preserved artifacts and, where
available, a previously retained digest outside the submitter's control.

This is an offline adversarial software test track. It uses synthetic files and
stubbed responses; it does not deploy an agent, contact a provider, publish claims
or measure any model's resistance to manipulation. It is distinct from the v0.3
model-development suite. The source payloads and campaign are versioned in
[`scenario.json`](../evals/rogue-agent-v0.1/scenario.json).

## Run it locally

```bash
PYTHONPATH=src python -m unittest discover -s tests -p test_rogue_agent.py -v
PYTHONPATH=src python -O -m unittest discover -s tests -p test_rogue_agent.py -v
```

Both commands are offline and need no key. Regular CI runs them too. A green test
means the stated rejection **or stated trust limitation** was reproduced. It is
not a “rogue agents defeated” score and cannot certify a model or company.

## Attacker capabilities and expected outcomes

The attacker can supply instruction-shaped source text, candidate model output,
edited local artifacts, invented review declarations and selective publicity.
Rejection tests assume the checker code and any separately retained reference
digest are outside attacker control. No protection is claimed when the attacker
also replaces the checker or controls every copy of the reference.

| Attempt | Executable expectation | What remains unproved |
|---|---|---|
| Source impersonates system instructions, demands secret access or extra trials | Payload remains input data; fixed instructions, no tools and no credential field | A model's semantic resistance to the text |
| Invent a citation or add approval fields to an answer | Invalid output; no strict-correct credit | Whether prose using valid source IDs actually entails its claims |
| Use duplicate JSON keys or NaN/Infinity to create ambiguous answers | v0.3 preserves the text as invalid output | Historical parsers are unchanged |
| Swap evidence and recompute its input hash | Existing request hashes cease to match | A completely rewritten bundle can be consistent |
| Alter scores or summaries | Replay rejects mismatch | The rubric itself still needs review |
| Remove an attempt and repair counts | Original call plan exposes truncation without a stopping error | Separate unsubmitted runs are invisible |
| Reorder results and repair the plan | Declared seed replay exposes the mismatch | The original seed needs independent preregistration to resist coordinated rewriting |
| Claim human adjudication in a development manifest or conceal retries | Unsupported declarations rejected | A false external publicity claim cannot be prevented |
| Put self-approval instructions in `next_evidence` | Review remains pending; zero automatic passes | A dishonest person can later submit a false attestation |
| Submit only favourable review rows or evade pursuit ratings with all N/A | Missing rows/inapplicable classifications rejected | Selective substantive judgment is not automatically detected |
| Rewrite response text, parsed answer, summary and worksheet consistently | A previously retained digest rejects replacement | Without a trusted earlier digest, consistency passes with authenticity explicitly unestablished |
| Invent a human reviewer and plausible notes | Declaration is reported only as unauthenticated attestation | No reviewer identity or independence verification exists |
| Present a two-case run or early API stop as complete coverage | Reports show selected/total cases and attempted/planned calls | Hidden run selection and misleading press releases remain outside the checker |

The stronger boundary is **independent provenance**, not another hash beside the
same editable data. A digest compared with an independently retained earlier value
detects later changes, assuming the reference and checker remain trustworthy. It
cannot establish that the original inputs or model responses were genuine.
Likewise, a reviewer name and UTC timestamp identify a declaration; they do not
authenticate the person or prove that review occurred.

Reports explicitly state that sources, provider calls, reviewer identity and
claim truth are not authenticated. Missing, unresolved, invalid and unreviewed
observations cannot silently become passes. No overall trust badge is emitted.
The software cannot stop someone from forking it, editing an exported report,
omitting an entire run, or lying in promotional copy. This is a tested set of
integrity checks and disclosed limits, not comprehensive abuse prevention.

## Subsequent model stress experiments

A later authorized experiment can have a model generate attacks against fictional
product claims and a separate auditor assess the preserved packets. Before running
it, freeze attacker/defender roles, attack budget, all variants, models, prompts,
repeats, stopping rules, judging criteria and cost bounds. Preserve failed attacks
and successful manipulations alike; manually review semantic overclaims, source
dependence, fake independence and attempts to label development results held out.
Do not give the attacker real keys, publication access or private-source tools.

Independently authored cases and reviewer adjudication, externally retained run
plans, authenticated signatures/identities and provider-origin verification are
future work with distinct trust assumptions. No live adversarial model results,
independent review or signatures are claimed by this implementation.
