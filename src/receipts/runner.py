"""Bounded inference, immutable request receipts, and honest run status. Apache-2.0."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import urllib.error
import urllib.request

from .evidence import canonical_hash
from . import evaluation, evaluation_v2

ENDPOINT = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5.4-mini-2026-03-17"


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def api_call(payload, key):
    request = urllib.request.Request(ENDPOINT, json.dumps(payload).encode(),
                                     headers={"Authorization": "Bearer " + key,
                                              "Content-Type": "application/json"})
    # No redirects: never forward a credential to a server named in a redirect.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request, timeout=90) as response:
            raw = response.read(4_000_001)
            if len(raw) > 4_000_000:
                raise RuntimeError("oversized_response")
            data = json.loads(raw)
    except urllib.error.HTTPError as exc:
        # Do not echo provider bodies, headers, or exception representations.
        raise RuntimeError("http_" + str(exc.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError("network_error") from None
    except (ValueError, UnicodeError):
        raise RuntimeError("invalid_provider_json") from None
    try:
        if not isinstance(data, dict) or not isinstance(data.get("output", []), list):
            raise ValueError("Unexpected response shape")
        text = "".join(part.get("text", "") for item in data.get("output", [])
                       if item.get("type") == "message" for part in item.get("content", [])
                       if part.get("type") == "output_text")
    except (AttributeError, TypeError, ValueError):
        raise RuntimeError("invalid_provider_shape") from None
    return {"response_id": data.get("id"), "returned_model": data.get("model"),
            "status": data.get("status"), "usage": data.get("usage"),
            "response_sha256": hashlib.sha256(raw).hexdigest(), "text": text}


def run(root, output, model, case_limit, seed, max_output_tokens, dry_run=False, suite="v0.1"):
    if not 1 <= case_limit <= 24 or not 256 <= max_output_tokens <= 2048:
        raise ValueError("case_limit must be 1..24 and max_output_tokens 256..2048")
    if suite not in ("v0.1", "v0.2"):
        raise ValueError("Unknown suite; choose v0.1 or v0.2")
    evaluator = evaluation if suite == "v0.1" else evaluation_v2
    cases, gold = evaluator.load_suite(root)
    selected = list(cases)
    random.Random(seed).shuffle(selected)
    selected = selected[:case_limit]
    prompts = {name: (root / "prompts" / (file + ".txt")).read_text()
               for name, file in [("baseline", "baseline"), ("receipts", "auditor")]}
    tasks = [(case, variant) for case in selected for variant in prompts]
    random.Random(seed + 1).shuffle(tasks)
    # Refuse to overwrite an existing experiment.
    output.mkdir(parents=True, exist_ok=False)
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                         stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit, dirty = None, None
    manifest = {"format": "receipts-eval-v0.1", "started_at_utc": now(),
                "status": "prepared", "dry_run": dry_run,
                "model_requested": model, "endpoint": ENDPOINT,
                "max_output_tokens_per_call": max_output_tokens,
                "planned_calls": len(tasks), "attempted_calls": 0, "completed_calls": 0, "retries": 0,
                "transport": "official_openai_responses_api",
                "model_identity_basis": "provider response field; not independent model attestation",
                "seed_for_order_only": seed, "provider_sampling": "provider defaults; no determinism claim",
                "commit": commit, "working_tree_dirty": dirty,
                "cases_sha256": canonical_hash(cases), "gold_sha256": canonical_hash(gold),
                "prompt_sha256": {k: canonical_hash(v) for k, v in prompts.items()},
                "selected_case_ids": [c["case_id"] for c in selected],
                "call_order": [[c["case_id"], v] for c, v in tasks],
                "limitation": "Synthetic development suite, not a held-out benchmark or truth certification."}
    if suite == "v0.2":
        metadata = evaluator.load_metadata(root)
        manifest.update(format="receipts-eval-v0.2", suite_version=suite,
                        scoring_version=suite, suite_metadata_sha256=canonical_hash(metadata),
                        seed_for_case_selection_and_call_order=seed,
                        independent_human_review=metadata["independent_human_review"])
        del manifest["seed_for_order_only"]
        save(output / "suite.json", metadata)
    save(output / "manifest.json", manifest)
    # Preserve the actual inputs and rubrics, not just their hashes.
    save(output / "cases.json", cases)
    save(output / "gold.json", gold)
    save(output / "prompts.json", prompts)
    if dry_run:
        save(output / "requests.json", [evaluator.request_payload(model, prompts[v], c, max_output_tokens) for c, v in tasks])
        manifest.update(status="dry_run_no_inference", ended_at_utc=now())
        save(output / "manifest.json", manifest)
        return 0
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        manifest.update(status="blocked_missing_api_key", ended_at_utc=now())
        save(output / "manifest.json", manifest)
        print("Inference blocked: configure repository secret OPENAI_API_KEY. No model calls made.", file=sys.stderr)
        return 2
    records, failed = [], False
    with (output / "results.jsonl").open("w", encoding="utf-8") as stream:
        for case, variant in tasks:
            payload = evaluator.request_payload(model, prompts[variant], case, max_output_tokens)
            record = {"case_id": case["case_id"], "variant": variant,
                      "request_sha256": canonical_hash(payload), "started_at_utc": now()}
            start = time.monotonic()
            try:
                reply = api_call(payload, key)
                record["response"] = reply
                if reply["status"] != "completed":
                    answer = None
                else:
                    try:
                        answer = json.loads(reply["text"])
                    except (ValueError, TypeError):
                        answer = None
                record["answer"] = answer
                record["score"] = evaluator.score(answer, case, gold[case["case_id"]])
                record["status"] = "scored" if record["score"]["valid"] else "invalid_output"
                failed = failed or not record["score"]["valid"]
            except RuntimeError as exc:
                record.update(status="api_error", error_code=str(exc))
                failed = True
            record["elapsed_seconds"] = round(time.monotonic() - start, 3)
            records.append(record)
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            stream.flush()
            manifest["attempted_calls"] = len(records)
            manifest["completed_calls"] = sum("response" in r for r in records)
            save(output / "manifest.json", manifest)
            print(f"{len(records)}/{len(tasks)} {case['case_id']} {variant}: {record['status']}", flush=True)
            if record["status"] == "api_error":
                break  # Stop on auth/rate/network errors; no expensive retry loop.
    summary = evaluator.summarize(records)
    save(output / "summary.json", summary)
    lines = ["# RECEIPTS model evaluation", "", "Synthetic development cases; human review of rationales remains necessary.", "",
             "| Prompt | Attempts | Correct verdicts | Unsupported support | Unnecessary abstention | Invalid | API errors |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for variant, s in summary.items():
        lines.append(f"| {variant} | {s['attempted']} | {s['verdict_correct']} | {s['unsupported_support']} | {s['unnecessary_abstention']} | {s['invalid_outputs']} | {s['api_errors']} |")
    lines += ["", "A completed experiment is not evidence that the harness improved the model. Compare actual results, inspect failures, and repeat on independently authored held-out cases.", ""]
    if suite == "v0.2":
        lines = evaluator.summary_lines(summary)
        save(output / "human-review-template.json", evaluator.review_template(records))
    (output / "summary.md").write_text("\n".join(lines))
    manifest.update(status="completed_with_errors" if failed else "completed", ended_at_utc=now())
    save(output / "manifest.json", manifest)
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--suite", choices=("v0.1", "v0.2"), default="v0.1")
    parser.add_argument("--cases", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-output-tokens", type=int, default=1200)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    return run(args.root, args.output, args.model, args.cases, args.seed, args.max_output_tokens, args.dry_run, args.suite)


if __name__ == "__main__":
    sys.exit(main())
