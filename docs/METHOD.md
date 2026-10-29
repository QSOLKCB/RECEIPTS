# A claim-level public-evidence method

RECEIPTS starts with a question, not a suspect or a preferred answer. Write the
exact proposition, time window, entities, and available source classes before
searching. Break compound allegations into separate claims. Whether an account
posted a statement, whether a person controlled the account, whether that person
wrote the statement, and whether the statement is true are different questions.

## Acquire receipts, then assess them

For each public source record its URL, publisher, underlying origin, access basis,
retrieval time in UTC, original timestamps, capture method, content hash, rights,
and a precise locator. Preserve the minimum lawful material needed to reproduce
the observation. A hash records which bytes were examined; it does not prove that
those bytes are authentic. A screenshot, an archive copy, and an official API
response have different evidentiary properties, and none is automatically true.

The included `receipt` command hashes an already acquired local capture. Its
`public_without_login` declaration is researcher-attested. The tool neither checks
the website nor proves that the local file came from the supplied URL. A researcher
must check that correspondence. Real evidence packets require receipts, but a
syntactically valid receipt is not authenticated evidence. Do not describe this
validation as source verification.

Log the searches that produced no result: query, domain or register, dates,
coverage, access failures, and cutoff. A missing page, blocked endpoint, deleted
post, or empty search result is a retrieval outcome. It becomes evidence against
a proposition only when the search should reliably have detected what the
proposition predicts. Explain that detection assumption explicitly.

## Keep identity links typed and local

Maintain separate nodes for platform accounts, handles, names, people, and legal
entities. A handle-to-account observation has a platform, time, and source. A
person-to-account assertion needs its own evidence. Never transfer an identity
claim across an entire connected graph merely because nodes share a name or
username. Account transfers, shared access, impersonation, and changing names
remain possible unless the relevant evidence addresses them.

Authenticated public self-attribution can strengthen a specific link. It need not
authenticate every historical post or every other account with a similar name.
Keep the exact scope of what is established. Offensive or embarrassing content
should be described accurately when relevant, while an unresolved link to a person
remains unresolved. Attribution restraint is compatible with acknowledging harm.

## Use metadata arithmetic without turning it into magic

Store platform IDs as strings to avoid numeric precision loss. For the classic
X/Twitter Snowflake layout, decode milliseconds as:

`(integer_id >> 22) + 1288834974657`

The implementation accepts the positive signed 63-bit range of that classic
layout. It is not a decoder for every platform ID, older sequential user IDs,
alphanumeric Space IDs, or future formats. Verify the ID family first. The result
is an encoded time for a supplied identifier. It cannot authenticate the identifier,
its claimed content, or the human behind it.

Normalize only timestamps with known offsets. Keep event time, post creation,
archive capture, article publication, article update, retrieval, and access times
separate. Explain discrepancies; a capture after an event is not its creation
time. Record original values alongside transformations and never guess a timezone.

## Compare writing only within a defensible design

First separate target authors from conversation context. Deduplicate post IDs and
identify retweets, quotations, incomplete captures, and prepared threads. Count
posts, tokens, time span, language, genre, and the number of independent documents.
Repeat descriptive comparisons after removing prepared threads and other major
confounds. The prototype reports an explicit without-threads sensitivity count.

Its feature extraction is deliberately modest: ASCII-Latin word tokens, median
length, and first-letter case. Quotation flags depend on the curator; unmarked
copied prose may remain. This is not a universal tokenizer, linguistic fingerprint,
stylometric classifier, or calibrated probability of shared authorship. A tiny
resignation sample cannot be rescued simply by counting more superficial features.
Large samples do not solve selection bias, genre confounds, or identity problems.

## Follow documented transfers, not imagined control

Each funding edge needs resolved legal entities, payer, payee, amount, currency,
relevant dates, status, source IDs, and any documented purpose or earmark. Separate
pledges, commitments, awards, disbursements, refunds, and reported balances. Do not
sum different currencies or duplicated disclosures. Researcher annotations must
be distinguishable from quoted source statements.

The prototype's funding command selects direct paid edges already supplied by a
researcher. It does not discover transfers or authenticate filings. A donor-to-lab
edge plus a lab-to-employee relationship does not create a donor-to-employee
payment. Even an established payment does not by itself show editorial control,
intent, timing instructions, or orchestration. Those are separate propositions.

## Test alternatives before writing the conclusion

Ask whether the observations could also arise from ordinary institutional ties,
independent responses to the same event, reused handles, changed opinions, shared
sources, or a deliberate prepared statement. Also ask what would distinguish
those explanations. An alternative is not established merely because it is
possible, and evidence of preparation does not automatically establish a broader
coordination theory.

Count source origins rather than headlines. Several articles quoting one witness
are several publications but one underlying testimony. Do not silently resolve
conflicts by choosing the source most congenial to the hypothesis.

## Report what could change your mind

For each atomic claim state a verdict, source locators, short supporting rationale,
material limitations, and the specific missing evidence that could change it.
Use supported, contradicted, and insufficient relative to the declared packet and
scope. Do not append numerical confidence unless it comes from a specified,
validated calibration procedure; this prototype supplies none.

A reviewer should be able to reproduce the calculation and disagree with the
interpretation. Preserve unresolved contradictions, corrections, provenance,
cutoffs, and prior versions. Publish only after a human checks consequential
claims, context, source rights, and the difference between absence of evidence
and evidence of absence. This is an editorial checkpoint, not a new restriction
on the Apache license.
