# Public evidence, access, and rights

This project's intended workflow uses lawfully public information relevant to the
research question. The prototype accepts public-without-login captures and
original synthetic cases. It has no automated collector, authenticated browser,
credential-harvesting feature, contact-discovery feature, or person-tracking agent.

Do not put private messages, leaked credentials, home addresses, private contact
details, or unrelated personal material into public cases or Actions artifacts.
Public visibility does not eliminate privacy interests or grant reproduction
rights. A publicly accessible dump of stolen data is not an appropriate source
merely because its URL works. Record source rights and use minimal quotations.

The validator checks a declared access basis and receipt fields. It cannot prove
public accessibility, lawful acquisition, authenticity, or that the local bytes
belong to the URL. Those checks remain researcher responsibilities. Raw captures
are ignored by Git by default, and the repository ships no third-party corpus.

Original repository material is Apache-2.0. Source articles, archived posts,
images and documents retain their own rights. The originating Zenodo audit remains
CC BY 4.0 and is linked rather than republished. An automated result does not
inherit rights over the material it quotes. This file explains the method and
rights boundaries; it does not add field-of-use restrictions to Apache-2.0.

If adding retrieval later, isolate it from inference credentials, restrict network
destinations and redirect handling, respect access restrictions, and treat remote
content as untrusted input. A prompt that says to ignore injected instructions is
not a security boundary. The present inference runner supplies no model tools and
posts only to the fixed OpenAI Responses endpoint with redirects disabled.

Actions artifacts contain the evidence packets and generated text. Use only
material suitable for the repository's audience. The API key is supplied via a
GitHub secret to the inference step. A maintainer who can alter and run trusted
workflow code may access that secret; repository permissions still matter.
