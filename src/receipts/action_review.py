"""Offline, record-bound human assessment of research proposals. Apache-2.0.

Validation checks structure and consistency, not reviewer identity or judgment.
No keywords, model judge, network, collection or inference are used here.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys

from .evidence import canonical_hash, utc
from .evaluation_v2 import nonempty, require

FORMAT = "receipts-action-review-v0.3"
DIMENSIONS = ("public_access", "feasibility", "relevance", "sufficiency_framing", "stopping")
RATINGS = ("not_reviewed", "pass", "fail", "unresolved", "not_applicable")
EFFECTS = ("not_reviewed", "could_resolve", "partial_only", "cannot_resolve", "unresolved", "not_applicable")
KINDS = ("not_reviewed", "pursue", "stop", "mixed", "unclear")
RUBRIC_RATINGS = ("not_reviewed", "accepted", "disputed", "unresolved")


def proposal(record):
    answer = record.get("answer")
    if isinstance(answer, dict) and isinstance(answer.get("next_evidence"), str):
        return answer["next_evidence"]
    return None


def binding(manifest, cases, gold, records):
    return {"manifest_sha256": canonical_hash(manifest), "cases_sha256": canonical_hash(cases),
            "gold_sha256": canonical_hash(gold), "records_sha256": canonical_hash(records)}


def receipt(manifest, cases, gold, records):
    bound = binding(manifest, cases, gold, records)
    return {"format": "receipts-run-receipt-v0.3", "run_sha256": canonical_hash(bound), "binding": bound,
            "meaning": "Canonical snapshot digest, not a signature, source authentication or proof of a provider call. Retain independently before review to detect later replacement."}


def template(manifest, cases, gold, records):
    by_id = {c["case_id"]: c for c in cases}
    rows = []
    for record in records:
        case = by_id[record["case_id"]]
        rows.append({"case_id": case["case_id"], "variant": record["variant"],
                     "record_sha256": canonical_hash(record), "claim": case["claim"],
                     "scope": case["scope"], "proposal": proposal(record),
                     "reviewer": None, "reviewed_at_utc": None, "review_basis": None,
                     "recommendation_kind": "not_reviewed",
                     "evidence_effect": {"status": "not_reviewed", "notes": ""},
                     "rubric_review": {"status": "not_reviewed", "notes": ""},
                     "assessments": {d: {"status": "not_reviewed", "notes": ""} for d in DIMENSIONS}})
    return {"format": FORMAT, "binding": binding(manifest, cases, gold, records), "rows": rows}


def validate_rating(value, choices):
    require(isinstance(value, dict) and set(value) == {"status", "notes"}, "Invalid assessment fields")
    require(value["status"] in choices and isinstance(value["notes"], str), "Invalid assessment status/notes")
    if value["status"] == "not_reviewed":
        require(value["notes"] == "", "Unreviewed assessment must not contain a judgment")
    else:
        require(nonempty(value["notes"]), "Every assessment needs substantive notes")


def validate_review(review, expected):
    require(isinstance(review, dict) and set(review) == {"format", "binding", "rows"}, "Unexpected review fields")
    require(review["format"] == FORMAT and review["binding"] == expected["binding"], "Review/run binding mismatch")
    require(isinstance(review["rows"], list) and len(review["rows"]) == len(expected["rows"]), "Missing or extra review rows")
    immutable = ("case_id", "variant", "record_sha256", "claim", "scope", "proposal")
    for row, original in zip(review["rows"], expected["rows"]):
        require(isinstance(row, dict) and set(row) == set(original), "Unexpected review row fields")
        require(all(row[k] == original[k] for k in immutable), "Changed, duplicate, reordered or mismatched review row")
        require(row["recommendation_kind"] in KINDS, "Unknown recommendation kind")
        require(isinstance(row["assessments"], dict) and set(row["assessments"]) == set(DIMENSIONS), "Missing assessment dimensions")
        for value in row["assessments"].values():
            validate_rating(value, RATINGS)
        validate_rating(row["evidence_effect"], EFFECTS)
        validate_rating(row["rubric_review"], RUBRIC_RATINGS)
        statuses = [v["status"] for v in row["assessments"].values()]
        statuses += [row["evidence_effect"]["status"], row["rubric_review"]["status"], row["recommendation_kind"]]
        active = any(s != "not_reviewed" for s in statuses)
        metadata = any(row[k] is not None for k in ("reviewer", "reviewed_at_utc", "review_basis"))
        if original["proposal"] is None:
            require(not active and not metadata, "No structured proposal exists to assess")
        if active or metadata:
            require(nonempty(row["reviewer"]), "Reviewer attribution required")
            require(row["review_basis"] == "human", "Assessments require a declared human review basis")
            require(nonempty(row["reviewed_at_utc"]) and row["reviewed_at_utc"].endswith("Z"), "UTC review time ending in Z required")
            utc(row["reviewed_at_utc"])
        action_started = (any(v["status"] != "not_reviewed" for v in row["assessments"].values())
                          or row["evidence_effect"]["status"] != "not_reviewed"
                          or row["recommendation_kind"] != "not_reviewed")
        if action_started:
            require(row["rubric_review"]["status"] != "not_reviewed", "Record the human rubric review before rating a proposal")
        kind = row["recommendation_kind"]
        if any(v["status"] != "not_reviewed" for v in row["assessments"].values()) or row["evidence_effect"]["status"] != "not_reviewed":
            require(kind != "not_reviewed", "Classify the recommendation before assessing it")
        if kind == "stop":
            require(all(row["assessments"][d]["status"] in ("not_reviewed", "not_applicable") for d in DIMENSIONS[:-1]), "Stop-only proposals use the stopping assessment")
            require(row["evidence_effect"]["status"] in ("not_reviewed", "not_applicable"), "Stop-only proposals have no acquisition effect")
        if kind == "pursue":
            require(row["assessments"]["stopping"]["status"] in ("not_reviewed", "not_applicable"), "Pursue-only proposals have no stopping judgment")
        if kind in ("pursue", "mixed"):
            require(all(row["assessments"][d]["status"] != "not_applicable" for d in DIMENSIONS[:-1]), "Research steps need access, feasibility, relevance and framing assessments")
            require(row["evidence_effect"]["status"] != "not_applicable", "Research steps need an evidence-effect classification")
        if kind in ("stop", "mixed"):
            require(row["assessments"]["stopping"]["status"] != "not_applicable", "Stopping needs its own assessment")


def aggregate(review, records):
    result = {}
    for variant in ("baseline", "receipts"):
        pairs = [(row, record) for row, record in zip(review["rows"], records) if record["variant"] == variant]
        available = [(row, record) for row, record in pairs if row["proposal"] is not None]
        counts = {}
        for dimension in DIMENSIONS:
            statuses = [r["assessments"][dimension]["status"] for r, _ in available]
            values = {s: statuses.count(s) for s in RATINGS}
            judged = values["pass"] + values["fail"]
            values.update(judged_pass_or_fail=judged,
                          failure_fraction_among_judged=values["fail"] / judged if judged else None)
            counts[dimension] = values
        reviewed = [(r, record) for r, record in available if any(v["status"] != "not_reviewed" for v in r["assessments"].values())]
        complete = [r for r, _ in available if r["recommendation_kind"] != "not_reviewed"
                    and r["evidence_effect"]["status"] != "not_reviewed"
                    and all(v["status"] != "not_reviewed" for v in r["assessments"].values())]
        failed = [(r, record) for r, record in reviewed if any(v["status"] == "fail" for v in r["assessments"].values())]
        result[variant] = {
            "attempted_responses": len(pairs), "structured_proposals": len(available),
            "unavailable_proposals": len(pairs) - len(available),
            "proposals_with_any_dimension_reviewed": len(reviewed),
            "proposals_with_all_dimensions_reviewed": len(complete),
            "proposals_with_any_reported_failure": len(failed),
            "strict_correct_responses_with_reported_action_failure": sum(record.get("score", {}).get("verdict_correct", False) for _, record in failed),
            "invalid_outputs_with_structured_proposals": sum(not record.get("score", {}).get("valid", False) for _, record in available),
            "dimensions": counts,
            "evidence_effect": {s: sum(r["evidence_effect"]["status"] == s for r, _ in available) for s in EFFECTS},
            "rubric_review": {s: sum(r["rubric_review"]["status"] == s for r, _ in available) for s in RUBRIC_RATINGS},
            "interpretation": "Reviewer-attested judgments, not automated approval or authenticated human identity. Unreviewed/unresolved observations are not passes.",
        }
    return result


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    def constant(value):
        raise ValueError("Non-finite JSON value")
    def finite_float(value):
        number = float(value)
        require(math.isfinite(number), "Non-finite JSON value")
        return number
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant, parse_float=finite_float)


def load_run(directory):
    from . import evaluation_v3 as evaluator
    values = {name: strict_json((directory / (name + ".json")).read_text(encoding="utf-8"))
              for name in ("manifest", "cases", "gold", "suite", "prompts", "summary")}
    manifest, cases, gold = values["manifest"], values["cases"], values["gold"]
    require(isinstance(manifest, dict) and manifest.get("format") == "receipts-eval-v0.3", "Expected a v0.3 run")
    require(manifest.get("status") in ("completed", "completed_with_errors") and manifest.get("dry_run") is False,
            "Only terminal inference records can be reviewed; preserve partial runs separately")
    require(manifest.get("suite_version") == "v0.3" and manifest.get("scoring_version") == "v0.2", "Unexpected suite/scorer version")
    require(nonempty(manifest.get("model_requested")) and type(manifest.get("max_output_tokens_per_call")) is int
            and 256 <= manifest["max_output_tokens_per_call"] <= 2048, "Invalid model/token configuration")
    require(all(type(manifest.get(k)) is int for k in ("planned_calls", "attempted_calls", "completed_calls")), "Run counts must be integers")
    require(type(manifest.get("retries")) is int and manifest["retries"] == 0, "Retries are not supported by this run contract")
    require(manifest.get("independent_human_review") == "not_performed", "Unsupported independent review claim")
    require(manifest.get("endpoint") == "https://api.openai.com/v1/responses"
            and manifest.get("transport") == "official_openai_responses_api", "Unexpected transport declaration")
    evaluator.validate_suite(cases, gold, values["suite"])
    for name, key in (("cases", "cases_sha256"), ("gold", "gold_sha256"), ("suite", "suite_metadata_sha256")):
        require(canonical_hash(values[name]) == manifest.get(key), "Run input hash mismatch: " + name)
    prompts = values["prompts"]
    require(isinstance(prompts, dict) and set(prompts) == {"baseline", "receipts"}
            and all(isinstance(p, str) for p in prompts.values()), "Invalid saved prompts")
    require({k: canonical_hash(v) for k, v in prompts.items()} == manifest.get("prompt_sha256"), "Prompt hash mismatch")
    records = [strict_json(line) for line in (directory / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    by_id = {c["case_id"]: c for c in cases}
    selected = manifest.get("selected_case_ids")
    require(isinstance(selected, list) and selected and all(isinstance(c, str) and c in by_id for c in selected)
            and len(selected) == len(set(selected)), "Invalid selected cases")
    order = manifest.get("call_order")
    require(isinstance(order, list) and all(isinstance(p, list) and len(p) == 2 and all(isinstance(x, str) for x in p) for p in order), "Invalid call order")
    require(len(order) == len(selected) * 2 and {tuple(p) for p in order} == {(c, v) for c in selected for v in prompts}, "Incomplete or duplicate call plan")
    seed = manifest.get("seed_for_case_selection_and_call_order")
    require(type(seed) is int, "Integer selection/order seed required")
    shuffled = list(by_id)
    random.Random(seed).shuffle(shuffled)
    require(selected == shuffled[:len(selected)], "Selected cases differ from declared seeded selection")
    planned = [[c, v] for c in selected for v in ("baseline", "receipts")]
    random.Random(seed + 1).shuffle(planned)
    require(order == planned, "Call order differs from declared seeded order")
    require(manifest.get("planned_calls") == len(order) and manifest.get("attempted_calls") == len(records)
            and 0 < len(records) <= len(order), "Run count mismatch")
    for index, record in enumerate(records):
        require(isinstance(record, dict) and [record.get("case_id"), record.get("variant")] == order[index], "Results do not match call order")
        case = by_id[record["case_id"]]
        request = evaluator.request_payload(manifest["model_requested"], prompts[record["variant"]], case, manifest["max_output_tokens_per_call"])
        require(canonical_hash(request) == record.get("request_sha256"), "Request hash mismatch")
        if record.get("status") == "api_error":
            require(index == len(records) - 1 and "response" not in record and "score" not in record and "answer" not in record, "Invalid API-error record")
        else:
            require(record.get("status") in ("scored", "invalid_output") and isinstance(record.get("response"), dict), "Invalid response record")
            reply = record["response"]
            answer = None
            if reply.get("status") == "completed":
                answer = evaluator.parse_answer(reply.get("text"))
            require(canonical_hash(answer) == canonical_hash(record.get("answer")), "Saved answer differs from response text")
            expected_score = evaluator.score(answer, case, gold[case["case_id"]])
            require(canonical_hash(record.get("score")) == canonical_hash(expected_score), "Saved score mismatch")
            require(record["status"] == ("scored" if expected_score["valid"] else "invalid_output"), "Output status mismatch")
    require(len(records) == len(order) or records[-1]["status"] == "api_error", "Truncated run without a stopping error")
    require(manifest.get("completed_calls") == sum("response" in r for r in records), "Completed count mismatch")
    failed = any(r["status"] != "scored" for r in records)
    require(manifest["status"] == ("completed_with_errors" if failed else "completed"), "Terminal run status mismatch")
    require(canonical_hash(values["summary"]) == canonical_hash(evaluator.summarize(records)), "Saved verdict summary mismatch")
    return manifest, cases, gold, records, values["summary"]


def report(directory, review_path, output, expected_run_sha256=None):
    run = load_run(directory)
    manifest, cases, gold, records, verdict_summary = run
    snapshot = receipt(manifest, cases, gold, records)
    if expected_run_sha256 is not None:
        require(isinstance(expected_run_sha256, str) and len(expected_run_sha256) == 64
                and all(c in "0123456789abcdef" for c in expected_run_sha256), "Expected digest must be 64 lowercase hex characters")
        require(snapshot["run_sha256"] == expected_run_sha256, "Run differs from supplied snapshot digest")
    raw_review = review_path.read_bytes()
    review = strict_json(raw_review.decode("utf-8"))
    validate_review(review, template(manifest, cases, gold, records))
    require(output.resolve() != directory.resolve() and directory.resolve() not in output.resolve().parents,
            "Write the report outside the preserved run directory")
    result = {"format": "receipts-action-report-v0.3", "binding": review["binding"],
              "run_sha256": snapshot["run_sha256"],
              "trust": {"artifact_consistency": "checked",
                        "supplied_digest_comparison": "matched" if expected_run_sha256 is not None else "not_requested",
                        "digest_origin": "caller_supplied_not_authenticated",
                        "provider_call_authenticity": "not_established",
                        "source_authenticity": "not_established", "claim_truth": "not_certified",
                        "reviewer_identity": "self_attested_not_authenticated",
                        "independent_adjudication": "not_established"},
              "run_coverage": {"suite_cases": len(cases), "selected_cases": len(manifest["selected_case_ids"]),
                               "planned_calls": manifest["planned_calls"], "attempted_calls": len(records),
                               "unattempted_calls": manifest["planned_calls"] - len(records),
                               "selection_seed": manifest["seed_for_case_selection_and_call_order"],
                               "cross_run_selection": "not_observable_from_one_bundle"},
              "review_file_sha256": hashlib.sha256(raw_review).hexdigest(),
              "verdict_performance": verdict_summary, "action_assessments": aggregate(review, records),
              "review_basis": "human_attestation_not_authenticated",
              "rubric_status": "Development rubrics; row-level human acceptance/disputes are reported separately."}
    lines = ["# Suggested-evidence review", "", "Human-attested judgments; no automated certification or reviewer authentication.",
             "Verdict metrics and action assessments are separate. No collection or inference was performed by this report command.", "",
             "File consistency does not authenticate sources, provider calls, reviewers or claim truth. Independent adjudication is not established.",
             "Supplied run digest comparison: " + ("MATCHED (digest origin not authenticated)." if expected_run_sha256 is not None else "NOT REQUESTED; coordinated replacement is not detectable from internal hashes alone."),
             f"Coverage: {len(manifest['selected_case_ids'])}/{len(cases)} suite cases selected; {len(records)}/{manifest['planned_calls']} calls attempted. Omitted separate runs cannot be detected from this bundle.", "",
             "| Prompt | Attempts | Strict correct | Proposals available | Any dimension reviewed | All dimensions reviewed | Any reported failure | Correct verdict with action failure |",
             "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for variant, row in result["action_assessments"].items():
        correct = verdict_summary.get(variant, {}).get("verdict_correct", 0)
        lines.append(f"| {variant} | {row['attempted_responses']} | {correct} | {row['structured_proposals']} | {row['proposals_with_any_dimension_reviewed']} | {row['proposals_with_all_dimensions_reviewed']} | {row['proposals_with_any_reported_failure']} | {row['strict_correct_responses_with_reported_action_failure']} |")
    lines += ["", "Dimension counts and pass/fail denominators are in report.json. Missing, unreviewed, unresolved and not-applicable entries are not passes.",
              "Failure fractions use only explicit pass/fail judgments for that dimension; they are not population rates.",
              "Partial evidence can be useful when described honestly; evidence-effect counts are separate from sufficiency-framing failures.",
              "Review every proposed step. Preserve rubric disputes and consult the copied review.json for notes and attribution.", ""]
    output.mkdir(parents=True, exist_ok=False)
    (output / "review.json").write_bytes(raw_review)
    (output / "report.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Aggregate record-bound human action reviews offline; no automatic judgment.")
    parser.add_argument("command", choices=("report",))
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-run-sha256", help="Previously retained canonical run digest; comparison is not authentication")
    args = parser.parse_args(argv)
    try:
        report(args.run, args.review, args.output, args.expected_run_sha256)
    except (ValueError, OSError, KeyError, TypeError, RecursionError):
        # Do not echo untrusted review content or exception representations.
        print("receipts: invalid or inconsistent run/review, inaccessible files, or an existing output directory; check the documented review contract and use a fresh output outside the run.", file=sys.stderr)
        return 2
    print(f"Action review report saved to {args.output}. No inference or collection performed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
