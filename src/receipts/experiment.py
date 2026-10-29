"""Offline frozen repeat plans and complete-denominator comparisons. Apache-2.0.

No inference, command execution, automated review or authentication is provided.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import statistics
import sys

from . import action_review, evaluation_v4 as evaluator
from .evidence import canonical_hash
from .evaluation_v2 import nonempty, require

FORMAT = "receipts-repeat-plan-v0.1"
VARIANTS = ("baseline", "receipts")
POLICY = {
    "case_selection": "all_16_cases_in_every_repeat",
    "aggregation": "strict_correct_receipts_minus_baseline_by_case_and_repeat_v1",
    "uncertainty": "descriptive_repeat_dispersion_and_missing_outcome_bounds_not_population_confidence_intervals",
    "retries": 0,
    "stop_rule": "each_run_stops_on_first_api_error_no_replacement_attempts",
    "endpoint": "https://api.openai.com/v1/responses",
    "transport": "official_openai_responses_api",
    "provider_sampling": "provider defaults; no determinism claim",
    "authorization": "plan_is_not_authorization_for_paid_inference",
    "human_review": "not_performed",
    "held_out": False,
}


def is_digest(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def runtime_hash():
    directory = Path(__file__).resolve().parent
    return canonical_hash({p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(directory.glob("*.py"))})


def timestamp(value):
    require(nonempty(value) and value.endswith("Z"), "Explicit UTC timestamp required")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    require(parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0, "UTC timezone required")
    return parsed


def slots(cases, repeats, seed):
    result = []
    for repeat in range(1, repeats + 1):
        repeat_seed = seed + repeat - 1
        ids = [c["case_id"] for c in cases]
        random.Random(repeat_seed).shuffle(ids)
        order = [[identity, variant] for identity in ids for variant in VARIANTS]
        random.Random(repeat_seed + 1).shuffle(order)
        result.append({"repeat": repeat, "seed": repeat_seed, "selected_case_ids": ids, "call_order": order})
    return result


def build_plan(inputs, model, repeats, seed, tokens, notes, created_at, engine):
    require(isinstance(inputs, dict) and set(inputs) == {"cases", "gold", "suite", "prompts"}, "Unexpected frozen input fields")
    evaluator.validate_suite(inputs["cases"], inputs["gold"], inputs["suite"])
    require(isinstance(inputs["prompts"], dict) and set(inputs["prompts"]) == set(VARIANTS)
            and all(nonempty(p) for p in inputs["prompts"].values()), "Two frozen prompts required")
    require(nonempty(model) and len(model) <= 200 and not model.startswith("-") and "\0" not in model, "Explicit model ID required")
    require(type(repeats) is int and 2 <= repeats <= 5, "Repeats must be 2..5")
    require(type(seed) is int and 0 <= seed <= 2**64 - repeats, "Seed exceeds the unsigned 64-bit repeat range")
    require(type(tokens) is int and 256 <= tokens <= 2048, "Output token limit must be 256..2048")
    require(nonempty(notes) and len(notes) <= 50000, "Design notes required, at most 50000 characters")
    timestamp(created_at)
    require(is_digest(engine), "Runtime digest required")
    return {"format": FORMAT, "created_at_utc": created_at, "suite_version": "v0.4", "scoring_version": "v0.2",
            "model_requested": model, "repeats": repeats, "base_seed": seed,
            "max_output_tokens_per_call": tokens, "planned_calls": 32 * repeats,
            "maximum_output_tokens": 32 * repeats * tokens,
            "cost_limit": "call/output-token limits only; input tokens also billable; no currency cap or spending authorization",
            "design_notes": notes, "engine_sha256": engine, "python_version": sys.version.split()[0], "inputs": inputs,
            "input_sha256": {k: canonical_hash(v) for k, v in inputs.items()},
            "policy": dict(POLICY), "slots": slots(inputs["cases"], repeats, seed)}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def prepare(root, output, model, repeats, seed, tokens, notes_path):
    cases, gold = evaluator.load_suite(root)
    inputs = {"cases": cases, "gold": gold, "suite": evaluator.load_metadata(root),
              "prompts": {name: (root / "prompts" / file).read_text(encoding="utf-8")
                          for name, file in (("baseline", "baseline.txt"), ("receipts", "auditor.txt"))}}
    plan = build_plan(inputs, model, repeats, seed, tokens, notes_path.read_text(encoding="utf-8"),
                      datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), runtime_hash())
    by_id = {c["case_id"]: c for c in cases}
    requests = [{"repeat": slot["repeat"], "requests": [
        evaluator.request_payload(model, inputs["prompts"][variant], by_id[identity], tokens)
        for identity, variant in slot["call_order"]]} for slot in plan["slots"]]
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "plan.json", plan)
    (output / "plan-sha256.txt").write_text(canonical_hash(plan) + "\n", encoding="utf-8")
    write_json(output / "requests.json", requests)
    write_json(output / "run-index-template.json", {"format": "receipts-repeat-index-v0.1", "rows": [
        {"repeat": slot["repeat"], "run_directory": None, "unavailable_reason": "not_submitted",
         "notes": "Record the preserved run path after authorized inference, or explain unavailability."}
        for slot in plan["slots"]]})
    return plan


def load_plan(path, expected):
    require(is_digest(expected), "A previously retained plan digest is required")
    raw = path.read_bytes()
    plan = action_review.strict_json(raw.decode("utf-8"))
    require(canonical_hash(plan) == expected, "Plan differs from supplied digest")
    require(isinstance(plan, dict), "Invalid plan")
    rebuilt = build_plan(plan["inputs"], plan["model_requested"], plan["repeats"], plan["base_seed"],
                         plan["max_output_tokens_per_call"], plan["design_notes"], plan["created_at_utc"], plan["engine_sha256"])
    require(canonical_hash(rebuilt) == expected, "Plan violates the fixed comparison contract")
    require(plan["engine_sha256"] == runtime_hash(), "Use the same Python source snapshot as the frozen plan")
    return plan, raw


def load_index(path, plan):
    raw = path.read_bytes()
    index = action_review.strict_json(raw.decode("utf-8"))
    require(isinstance(index, dict) and set(index) == {"format", "rows"}
            and index["format"] == "receipts-repeat-index-v0.1", "Invalid run index")
    require(isinstance(index["rows"], list) and len(index["rows"]) == plan["repeats"], "Every planned repeat needs an index row")
    paths = set()
    for repeat, row in enumerate(index["rows"], 1):
        require(isinstance(row, dict) and set(row) == {"repeat", "run_directory", "unavailable_reason", "notes"}, "Unexpected index fields")
        require(type(row["repeat"]) is int and row["repeat"] == repeat, "Duplicate, missing or reordered repeat")
        require(isinstance(row["notes"], str), "Index notes must be text")
        if row["run_directory"] is None:
            require(row["unavailable_reason"] in ("not_run", "not_submitted", "blocked", "interrupted")
                    and nonempty(row["notes"]), "Unavailable runs need an explicit reason and notes")
        else:
            require(nonempty(row["run_directory"]) and row["unavailable_reason"] is None, "Submitted runs cannot also be unavailable")
            directory = (path.parent / row["run_directory"]).resolve()
            require(directory not in paths, "A run directory cannot fill multiple repeat slots")
            paths.add(directory)
    return index, raw


def checked_run(directory, plan, slot):
    manifest, cases, gold, records, _ = action_review.load_run(directory)
    require(manifest["suite_version"] == "v0.4" and manifest.get("engine_sha256") == plan["engine_sha256"], "Wrong suite or execution source snapshot")
    require(manifest.get("python_version") == plan["python_version"], "Changed Python version")
    require(manifest["model_requested"] == plan["model_requested"]
            and manifest["max_output_tokens_per_call"] == plan["max_output_tokens_per_call"], "Changed model or output cap")
    require(manifest["seed_for_case_selection_and_call_order"] == slot["seed"]
            and manifest["selected_case_ids"] == slot["selected_case_ids"]
            and manifest["call_order"] == slot["call_order"], "Run differs from the locked repeat schedule")
    require(canonical_hash(cases) == plan["input_sha256"]["cases"]
            and canonical_hash(gold) == plan["input_sha256"]["gold"]
            and manifest["suite_metadata_sha256"] == plan["input_sha256"]["suite"]
            and manifest["prompt_sha256"] == {k: canonical_hash(v) for k, v in plan["inputs"]["prompts"].items()}, "Changed frozen inputs")
    require(all(manifest.get(k) == POLICY[k] for k in ("retries", "endpoint", "transport", "provider_sampling")), "Changed execution policy")
    require(timestamp(plan["created_at_utc"]) <= timestamp(manifest["started_at_utc"])
            <= timestamp(manifest["ended_at_utc"]), "Run timestamps precede plan or are reversed")
    return manifest, records, action_review.receipt(manifest, cases, gold, records)["run_sha256"]


def comparison(plan, runs):
    n = 16 * plan["repeats"]
    records = {(repeat, r["case_id"], r["variant"]): r for repeat, rows in runs.items() for r in rows}
    counts = {variant: {"planned": n, "attempted": 0, "valid": 0, "strict_correct": 0,
                        "invalid_outputs": 0, "api_errors": 0} for variant in VARIANTS}
    for (_, _, variant), record in records.items():
        count = counts[variant]
        count["attempted"] += 1
        count["valid"] += bool(record.get("score", {}).get("valid", False))
        count["strict_correct"] += bool(record.get("score", {}).get("verdict_correct", False))
        count["invalid_outputs"] += record["status"] == "invalid_output"
        count["api_errors"] += record["status"] == "api_error"
    for count in counts.values():
        missing = n - count["attempted"]
        count.update(unattempted=missing,
                     strict_accuracy_among_attempted=count["strict_correct"] / count["attempted"] if count["attempted"] else None,
                     accuracy_bounds_for_planned_calls=[count["strict_correct"] / n, (count["strict_correct"] + missing) / n])
    cells, repeat_metrics = [], []
    lower = upper = matched_delta = matched = wins = losses = ties = 0
    for repeat in range(1, plan["repeats"] + 1):
        complete_deltas = []
        for case in plan["inputs"]["cases"]:
            outcome = {}
            for variant in VARIANTS:
                record = records.get((repeat, case["case_id"], variant))
                outcome[variant] = {"status": record["status"] if record else "unattempted",
                                    "strict_correct": int(bool(record.get("score", {}).get("verdict_correct", False))) if record else None}
            b, r = (outcome[v]["strict_correct"] for v in VARIANTS)
            lo = (r if r is not None else 0) - (b if b is not None else 1)
            hi = (r if r is not None else 1) - (b if b is not None else 0)
            lower += lo
            upper += hi
            delta = None if b is None or r is None else r - b
            if delta is not None:
                matched += 1
                matched_delta += delta
                wins += delta == 1
                losses += delta == -1
                ties += delta == 0
                complete_deltas.append(delta)
            cells.append({"repeat": repeat, "case_id": case["case_id"], **outcome,
                          "paired_difference": delta, "missing_outcome_bounds": [lo, hi]})
        repeat_metrics.append({"repeat": repeat, "matched_pairs": len(complete_deltas), "planned_pairs": 16,
                               "mean_difference_if_all_pairs_observed": sum(complete_deltas) / 16 if len(complete_deltas) == 16 else None})
    full = [r["mean_difference_if_all_pairs_observed"] for r in repeat_metrics if r["matched_pairs"] == 16]
    return {"variants": counts, "paired": {"planned_pairs": n, "observed_pairs": matched,
        "pairs_missing_one_or_both_calls": n - matched, "receipts_only_correct": wins,
        "baseline_only_correct": losses, "tied_strict_outcomes": ties,
        "mean_difference_all_planned_pairs": matched_delta / n if matched == n else None,
        "mean_difference_observed_pairs_only": matched_delta / matched if matched else None,
        "missing_outcome_bounds_all_planned_pairs": [lower / n, upper / n]},
        "repeat_metrics": repeat_metrics, "repeat_dispersion": {
            "fully_observed_repeats": len(full), "mean": statistics.mean(full) if full else None,
            "minimum": min(full) if full else None, "maximum": max(full) if full else None,
            "sample_standard_deviation": statistics.stdev(full) if len(full) >= 2 else None,
            "meaning": "Descriptive variability among fully observed repeats on the same fixed cases. Missing repeats can bias this subset; not a population confidence interval."},
        "case_repeat_outcomes": cells}


def report(plan_path, index_path, output, expected):
    plan, raw_plan = load_plan(plan_path, expected)
    index, raw_index = load_index(index_path, plan)
    runs, provenance, digests = {}, [], set()
    protected = [plan_path.parent.resolve()]
    for row, slot in zip(index["rows"], plan["slots"]):
        if row["run_directory"] is None:
            provenance.append({"repeat": row["repeat"], "status": "unavailable", "reason": row["unavailable_reason"]})
            continue
        directory = (index_path.parent / row["run_directory"]).resolve()
        manifest, records, digest = checked_run(directory, plan, slot)
        require(digest not in digests, "A run snapshot cannot fill multiple repeat slots")
        digests.add(digest)
        protected.append(directory)
        runs[row["repeat"]] = records
        returned = sorted({r["response"]["returned_model"] for r in records
                           if nonempty(r.get("response", {}).get("returned_model"))})
        missing_ids = sum(not nonempty(r["response"].get("returned_model")) for r in records if "response" in r)
        provenance.append({"repeat": row["repeat"], "status": manifest["status"], "run_sha256": digest,
                           "returned_model_ids": returned, "responses_missing_model_id": missing_ids})
    target = output.resolve()
    require(all(target != p and p not in target.parents for p in protected), "Report must be outside the preserved plan and runs")
    metrics = comparison(plan, runs)
    ids = sorted({identity for p in provenance for identity in p.get("returned_model_ids", [])})
    warnings = []
    if len(ids) > 1:
        warnings.append("Multiple returned model IDs occur; the model condition may differ across calls.")
    if any(p.get("responses_missing_model_id", 0) for p in provenance):
        warnings.append("Some responses have no returned model ID; model identity is unavailable for those calls.")
    if any(identity != plan["model_requested"] for identity in ids):
        warnings.append("Returned model IDs differ from the requested ID; any alias mapping is not independently verified.")
    result = {"format": "receipts-repeat-report-v0.1", "plan_sha256": expected,
              "run_index_file_sha256": hashlib.sha256(raw_index).hexdigest(),
              "status": "all_planned_calls_observed" if metrics["paired"]["observed_pairs"] == 16 * plan["repeats"] else "incomplete_coverage",
              "planned_repeats": plan["repeats"], "submitted_terminal_runs": len(runs), "runs": provenance,
              "requested_model": plan["model_requested"], "returned_model_ids": ids,
              "comparability_warnings": warnings,
              "model_identity_note": "Provider fields, not attestation; inspect missing or multiple returned IDs before comparison.",
              "trust": {"plan_digest": "matched_caller_supplied_value_not_authenticated",
                        "artifact_consistency": "checked", "independent_adjudication": "not_established",
                        "source_and_provider_authenticity": "not_established", "unsubmitted_attempts": "not_observable",
                        "preregistration": "timestamp_consistency_only_not_externally_attested"},
              "human_action_and_prose_review": "not_aggregated_use_separate_bound_review_reports",
              "metrics": metrics,
              "limitations": "Public AI-assisted development suite. No model ranking, calibrated confidence interval or reliable improvement claim follows from these counts. Cost approval is not established by this report."}
    lines = ["# Frozen repeated comparison", "", "Development results; no independent adjudication, model ranking or truth certification.",
             "Plan digest matched the supplied value. Its origin, timestamps, sources and provider calls are not authenticated.",
             f"Coverage: {len(runs)}/{plan['repeats']} terminal runs submitted; {metrics['paired']['observed_pairs']}/{16 * plan['repeats']} paired outcomes observed.", "",
             "| Prompt | Planned | Attempted | Unattempted | Strict correct | Invalid | API errors |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for variant, count in metrics["variants"].items():
        lines.append(f"| {variant} | {count['planned']} | {count['attempted']} | {count['unattempted']} | {count['strict_correct']} | {count['invalid_outputs']} | {count['api_errors']} |")
    paired = metrics["paired"]
    lines += ["", "All-planned paired mean difference (RECEIPTS minus baseline): " + str(paired["mean_difference_all_planned_pairs"]),
              "Possible mean-difference bounds for unattempted calls: " + str(paired["missing_outcome_bounds_all_planned_pairs"]),
              "A null mean means missing paired observations, not a tie or a failure imputation.",
              "Bounds describe missing outcomes, not statistical confidence. Repeat dispersion is descriptive and conditional on the same fixed cases.",
              "Inspect report.json for each case/repeat, directional paired counts, repeat variability, returned model IDs and preserved index notes.",
              "Action/prose quality is not inferred here. Keep separate bound human reviews. Hidden additional attempts cannot be detected from submitted files.", ""]
    lines.extend(warnings)
    lines.append("")
    output.mkdir(parents=True, exist_ok=False)
    (output / "plan.json").write_bytes(raw_plan)
    (output / "run-index.json").write_bytes(raw_index)
    write_json(output / "report.json", result)
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Freeze a repeated comparison or report preserved runs offline; no inference.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--model", required=True)
    p.add_argument("--repeats", type=int, required=True)
    p.add_argument("--notes", type=Path, required=True)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max-output-tokens", type=int, default=1200)
    p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("report")
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--runs", type=Path, required=True)
    p.add_argument("--expected-plan-sha256", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            prepare(args.root, args.output, args.model, args.repeats, args.seed, args.max_output_tokens, args.notes)
        else:
            report(args.plan, args.runs, args.output, args.expected_plan_sha256)
    except (ValueError, OSError, KeyError, TypeError, RecursionError, OverflowError):
        print("receipts: invalid experiment inputs, changed plan/runtime, incompatible run, or existing/protected output; check the experiment contract and use a fresh directory.", file=sys.stderr)
        return 2
    print(f"Experiment {args.command} saved to {args.output}. No inference performed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
