# Rust CLI control surface

`receipts` is a native command-line entry point for humans, scripts and AI agents.
Rust selects commands, validates evaluation options and starts Python. Python
continues to own evidence calculations, validation, request construction, scoring
and artifact formats. There is no second implementation of those semantics.

## Build and install

Use a trusted checkout, Python 3.10+ and Rust via rustup. `rust-toolchain.toml` pins
the tested Rust toolchain to 1.85.1. The Rust crate has no third-party dependencies;
`Cargo.lock` is committed. The first toolchain installation may require a download.
Once the toolchain is installed, the following Cargo build needs no registry access:

```bash
cargo build --release --locked --offline
./target/release/receipts --help
./target/release/receipts verify
```

For a first offline experiment without installing the command:

```bash
cargo run --locked --offline -- eval prepare --suite v0.3 --output artifacts/prepared-v03
```

To install the command into Cargo's binary directory:

```bash
cargo install --path . --locked --offline
receipts --help
```

Cargo's binary directory (normally `~/.cargo/bin`) must be on `PATH`. A repository
clone alone does not install `receipts`. After pulling CLI changes, use
`cargo install --path . --locked --offline --force` to refresh the installed binary,
or use `cargo run --locked --offline -- ...` directly from the checkout.

Installation copies the binary, not the Python package, fixtures or archives.
Keep the repository checkout available. From its root, the CLI uses that checkout.
From elsewhere, specify it explicitly:

```bash
receipts --root /path/to/RECEIPTS --python /path/to/python3 verify
```

Global options precede the command. `--python` is an executable name or path, not
a shell command containing additional flags. The default is `python3` on Unix
and `python` on Windows. Linux is tested in CI; other operating systems have not
yet received the same integration validation. No shell completion or TUI is included.

## Commands

| Command | Backend | Output / effect |
|---|---|---|
| `snowflake ID` | `receipts` Python CLI | Existing JSON decoding result |
| `utc TIMESTAMP` | `receipts` Python CLI | Existing JSON timestamp result |
| `receipt FILE ...` | `receipts` Python CLI | Existing JSON source receipt; does not fetch a URL |
| `style FILE` | `receipts` Python CLI | Existing JSON descriptive statistics |
| `funding FILE --payer X --payee Y` | `receipts` Python CLI | Existing JSON direct paid-edge selection |
| `verify` | Preservation verifier | Text verification result for the fixed four-model checkpoint |
| `eval prepare --output DIR` | `receipts.runner --dry-run` | JSON request/input/manifest artifacts; no inference |
| `eval run --model ID --output DIR --allow-paid` | `receipts.runner` | Paid inference when authorized and credentials are configured |
| `review report --run DIR --review FILE --output DIR` | `receipts.action_review` | Offline v0.3 consistency checks and aggregation of declared human action judgments |

Examples from the checkout root:

```bash
receipts snowflake 1273816504776982529
receipts utc '2026-09-01T00:30:00+09:30'
receipts style examples/posts.json
receipts funding examples/funding.json --payer donor-d --payee person-p
receipts receipt captures/example.txt \
  --url https://example.org/public-record \
  --retrieved-at '2026-10-30T00:00:00Z' \
  --locator 'paragraph 3' --access-basis public_without_login
receipts eval prepare --output artifacts/prepared-cli --cases 4
```

The receipt example assumes you already lawfully acquired the named local file.
A public-source declaration and hash do not authenticate that file. The CLI adds
no retrieval capability or identity-inference method.

Use `receipts COMMAND --help`, `receipts eval --help` or
`receipts eval run --help` to inspect options without starting Python.

## Evaluation controls

`eval prepare` always sets `--dry-run`. `eval run` requires both an explicit model
ID and `--allow-paid`, plus a fresh `--output` directory. A configured key alone
cannot select paid mode. The flag expresses operator intent; an agent still needs
the user's authorization under `AGENTS.md`. Adding this control surface does not
authorize a new experiment.

Additional evaluation options are `--cases 1..16`, `--seed N` (unsigned integer,
case selection and call order), and `--max-output-tokens 256..2048`. Defaults remain
16 cases, seed 42 and 1,200 maximum output tokens per call. Each case produces two planned calls.
The current CLI caps requests at 32 calls; token/call bounds are not a currency
budget. Duplicate or unknown evaluation options are rejected before Python starts.
Pass flags and values as separate arguments; `--option=value` is not supported
by the Rust global/evaluation parser.

`--suite v0.1|v0.2|v0.3` selects an allowlisted suite; the default remains `v0.1`.
All contain 16 cases, so existing call limits apply. For the atomic-claim
development suite, prepare offline with:

```bash
receipts eval prepare --suite v0.2 --output artifacts/prepared-v02
```

The [v0.2 contract](../evals/v0.2/README.md) documents its typed claims, distinct
scoring fields and pending human review. [v0.3](../evals/v0.3/README.md) adds action
rubrics and review artifacts while reusing the v0.2 verdict scorer. Selecting a
suite does not enable paid mode.

The runner shuffles the suite before taking `--cases`, then shuffles the paired
calls. Changing the seed can therefore change which cases a reduced run covers,
as well as their call order. It does not seed model sampling or make responses
deterministic. The v0.1 manifest key `seed_for_order_only` is retained for format
compatibility; v0.2/v0.3 use `seed_for_case_selection_and_call_order`. Inspect
`selected_case_ids` and `call_order` for actual coverage and sequence in every version.

For an explicitly authorized run, with `OPENAI_API_KEY` already supplied through
the environment or secret mechanism:

```bash
receipts eval run --model YOUR_EXACT_MODEL_ID \
  --output artifacts/authorized-run-001 --cases 16 --allow-paid
```

Never put a key in an argument. Missing credentials produce the Python runner's
existing blocked manifest and zero model calls. Existing output directories are
never overwritten: a repeated run returns 2 with a concise fresh-directory
message. Successful preparation prints its output path and confirms no model
calls were made. The runner's stopping and retry policies are unchanged.

## Offline action-review reports

`review report` requires one each of `--run`, `--review` and `--output`. It optionally
accepts `--expected-run-sha256` with 64 lowercase hex characters from a previously
retained `run-receipt.json`. Duplicate, unknown or incomplete flags are rejected
before Python starts. The provider key is removed from its environment.

The report validates a terminal v0.3 run and a record-bound review worksheet,
replays saved scores and summaries, and writes `review.json`, `report.json` and
`report.md` in a fresh directory outside the run. It never judges recommendations
automatically or collects their suggested evidence. Success returns 0 and a short
text message; validation/access/output errors return 2 without echoing untrusted
input text. See [the full review contract](ACTION_REVIEW.md), including required
ratings and the limits of unauthenticated reviewer declarations and run digests.

## Automation contract

Metadata JSON is passed through byte for byte. Rust does not wrap it, add banners,
round values or change evidence semantics. Parse JSON only on successful metadata
commands; backend failures may include diagnostic tracebacks on stderr.

Verification uses text stdout. Evaluation uses the Python runner's progress
stdout and structured files in the selected output directory; it is not a JSONL
stdout protocol. Automation should inspect the exit status and saved manifest,
including invalid outputs, API errors and incomplete responses. A successful
experiment process does not mean the model's conclusions were correct.

Stdout, stderr and ordinary backend exit codes are inherited/preserved. Rust usage,
checkout and process-launch errors return 2. On Unix, the launcher replaces itself
with Python using `exec`: the backend keeps the CLI PID, so killing that PID or
using `subprocess.run(..., timeout=...)` also stops the local backend. Signal
termination remains an OS signal, rather than a launcher-generated exit code.
For example, Python's `subprocess` reports SIGTERM as `-15`; a shell typically
reports `143` (`128 + 15`).

On non-Unix platforms the launcher still spawns and waits. Killing only the
launcher there may leave Python running; callers need process-tree supervision
for reliable cancellation. No cross-platform supervisor or retry loop is included.
Stopping a local process does not guarantee cancellation or reversal of a request
already accepted by the provider. Interrupted artifact directories may be incomplete;
preserve them and inspect their status before planning any separately authorized run.

Relative input and output paths stay relative to the caller's working directory.
`--root` chooses code, fixtures and the archive; it does not change that directory.

The backend starts with Python `-I -S` and an explicit source directory from the
selected checkout. Ambient `PYTHONPATH`, current-directory imports and Python site
customization do not choose another backend. Arguments are separate process
arguments, not interpolated shell text or Python source. Offline backend processes
have `OPENAI_API_KEY` removed; only explicitly selected paid mode inherits it.
Other environment variables are not comprehensively scrubbed. The chosen Python
executable and checkout must be trusted: the CLI is not a sandbox and does not
make malicious local backend code safe.

## Verify changes

```bash
cargo fmt --all -- --check
cargo test --locked --offline
cargo clippy --locked --offline --all-targets -- -D warnings
cargo build --locked --offline
python -m unittest discover -s cli/tests -v
PYTHONPATH=src python -m unittest discover -s tests -v
python experiments/preservation-2026-10-30/verify.py
python -O experiments/preservation-2026-10-30/verify.py
```

Integration tests use the compiled debug binary by default. To check a release
build, set `RECEIPTS_CLI` to its path. Paid-mode forwarding is tested only against
a synthetic local stub; the real runner is exercised without a key to verify
that it blocks before inference. Tests never send provider requests.
Unix regression tests also check backend signal status, PID-only SIGTERM/SIGKILL
and caller timeouts against a waiting local stub, with no surviving backend.

The existing 40 preserved experiment files and the v0.1 evidence/scoring module
remain unchanged. v0.2 has a separate Python evaluator selected by the runner;
Rust owns no scoring logic. New runs still need new directories, plans and provenance.
