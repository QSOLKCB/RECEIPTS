# ZeroKey: relevance to RECEIPTS

Reviewed on 30 October 2026 (Australia/Adelaide), at repository tree
`d8887a633dbf4b7b70b225d5b6adcbaf964279a5`:
https://github.com/Cyberpradeep/ZeroKey

This was a source review, not a runtime test or a comprehensive security audit.
No ZeroKey code or dependency was copied, installed, or executed in RECEIPTS.

The README declares MIT. The complete, non-truncated tree retrieved at review time
contained no full LICENSE file. The source files inspected also had no copyright
and MIT permission header. Before copying substantial code, resolve the applicable
copyright and full license notice and preserve them. This observation is not a
claim that the project's stated license is invalid.

## Relevant observations

| Component | Source observation | Implication for this experiment |
|---|---|---|
| `providers/base_provider.py` | Separates provider lifecycle, sending and readiness | Useful general architecture for future adapters |
| `core/prompt_compiler.py` | Flattens role messages into one text prompt with delimiters | A framed system block is not the API's instruction channel |
| `providers/chatgpt/provider.py` | Navigates to chatgpt.com and submits text through a logged-in browser | The bridge runs locally; inference still uses a remote service |
| `server/routes.py` | Returns `request.model` while provider invocation has no corresponding model-selection argument | Echoed model names are not observations of the serving model |
| `server/schemas.py` | Usage counters default to zero | Zero must not be interpreted as measured token consumption |
| `server/schemas.py` and routes | Expose Chat Completions-style messages; no Responses API JSON-schema enforcement is shown | Compatibility with one endpoint does not guarantee this harness's output contract |

These source observations do not establish how the project behaves under every
configuration, nor whether its web bridge currently works. They are enough to
avoid using it as the transport for the initial controlled model comparison.

RECEIPTS keeps requested model and returned model separate, retains provider usage
when supplied, represents missing usage as null, and records transport provenance.
Even an official API's model field is a provider report, not independent attestation.
Future adapters must report their actual observability limits rather than filling
missing measurements with plausible-looking values.

The provider/request/result separation is a common architectural pattern. Its use
here does not imply copied code, integration with, or endorsement by ZeroKey.
