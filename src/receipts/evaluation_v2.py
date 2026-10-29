"""Opt-in v0.2 claim semantics and scoring; v0.1 remains unchanged. Apache-2.0."""
import json

from . import evaluation as legacy
from .evidence import canonical_hash

VERSION = "v0.2"
VERDICTS = tuple(legacy.SCHEMA["properties"]["verdict"]["enum"])
PACKET_KEYS = {"case_id", "kind", "claim", "sources", "cutoff_utc", "claim_type", "scope"}
RUBRIC_KEYS = {"verdict", "required_sources", "required_limitations", "justification",
               "verdict_examples", "legacy_case_ids", "review_status"}
HUMAN_DIMENSIONS = ("citation_entailment", "rationale_fidelity", "caveat_adequacy")
SEMANTICS = {
    "factual": "Assess whether the specified event or state occurred within the declared scope.",
    "evidentiary_sufficiency": "Assess whether the named evidence establishes the specified conclusion. Rejecting its sufficiency does not establish that the underlying event did not happen.",
    "supported": "The packet establishes the exact proposition being assessed.",
    "contradicted": "The packet establishes the negation of that exact proposition.",
    "insufficient": "The packet establishes neither the proposition nor its negation.",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def string_list(value):
    return (isinstance(value, list) and all(nonempty(v) for v in value)
            and len(value) == len(set(value)))


def validate_packet(case):
    require(isinstance(case, dict) and set(case) == PACKET_KEYS,
            "Unexpected v0.2 packet fields; rubrics must stay outside model input")
    require(nonempty(case["case_id"]) and case["case_id"].startswith("v02-"), "Expected v02 case ID")
    require(case["claim_type"] in ("factual", "evidentiary_sufficiency"), "Unknown claim type")
    require(nonempty(case["scope"]) and nonempty(case["claim"]), "Claim and scope required")
    require(case["kind"] == "synthetic", "v0.2 development suite accepts synthetic packets only")
    require(nonempty(case["cutoff_utc"]), "Cutoff required")
    require(isinstance(case["sources"], list) and bool(case["sources"]), "Sources required")
    for source in case["sources"]:
        require(isinstance(source, dict) and set(source) == {"source_id", "origin_id", "text"},
                "Unexpected synthetic source fields")
        require(all(nonempty(v) for v in source.values()), "Source ID, origin and content required")
    legacy.validate_packet({key: case[key] for key in PACKET_KEYS - {"claim_type", "scope"}})


def load_metadata(root):
    metadata = json.loads((root / "evals/v0.2/suite.json").read_text(encoding="utf-8"))
    require(isinstance(metadata, dict) and metadata.get("suite_version") == VERSION,
            "Wrong suite metadata version")
    require(metadata.get("independent_human_review") == "not_performed",
            "This development suite has no recorded independent human adjudication")
    require(metadata.get("held_out") is False, "This development suite is not held out")
    require(metadata.get("case_count") == 16, "Expected the declared 16-case v0.2 suite")
    return metadata


def load_suite(root):
    metadata = load_metadata(root)
    directory = root / "evals/v0.2"
    cases = json.loads((directory / "cases.json").read_text(encoding="utf-8"))
    gold = json.loads((directory / "gold.json").read_text(encoding="utf-8"))
    require(isinstance(cases, list) and len(cases) == metadata["case_count"], "Bad v0.2 case count")
    for case in cases:
        validate_packet(case)
    ids = [case["case_id"] for case in cases]
    require(len(ids) == len(set(ids)), "Duplicate case IDs")
    require(isinstance(gold, dict) and set(gold) == set(ids), "Case/gold mismatch")
    legacy_cases, _ = legacy.load_suite(root)
    legacy_ids = {case["case_id"] for case in legacy_cases}
    for case in cases:
        rubric = gold[case["case_id"]]
        require(isinstance(rubric, dict) and set(rubric) == RUBRIC_KEYS, "Unexpected rubric fields")
        require(rubric["verdict"] in VERDICTS, "Bad rubric verdict")
        require(string_list(rubric["required_sources"]), "Bad required source list")
        require(set(rubric["required_sources"]) <= {s["source_id"] for s in case["sources"]},
                "Rubric cites an unknown source")
        require(string_list(rubric["required_limitations"]), "Bad required limitation list")
        require(set(rubric["required_limitations"]) <= legacy.LIMITATIONS.keys(), "Unknown limitation")
        require(nonempty(rubric["justification"]), "Rubric justification required")
        examples = rubric["verdict_examples"]
        require(isinstance(examples, dict) and set(examples) == set(VERDICTS)
                and all(nonempty(v) for v in examples.values()), "Three verdict examples required")
        require(string_list(rubric["legacy_case_ids"])
                and set(rubric["legacy_case_ids"]) <= legacy_ids, "Unknown legacy case lineage")
        require(rubric["review_status"] == "not_independently_reviewed", "Unsupported review status")
    require({r["verdict"] for r in gold.values()} == set(VERDICTS), "All verdict controls required")
    return cases, gold


def model_input(case):
    validate_packet(case)
    packet = legacy.model_input({key: case[key] for key in PACKET_KEYS - {"claim_type", "scope"}})
    packet.update(claim_type=case["claim_type"], scope=case["scope"], claim_semantics=SEMANTICS)
    return packet


def request_payload(model, prompt, case, max_output_tokens):
    # Reuse the same transport/schema contract; only the versioned input changes.
    validate_packet(case)
    base = {key: case[key] for key in PACKET_KEYS - {"claim_type", "scope"}}
    payload = legacy.request_payload(model, prompt, base, max_output_tokens)
    payload["input"] = json.dumps(model_input(case), ensure_ascii=False)
    return payload


def score(answer, case, rubric):
    result = legacy.score(answer, case, rubric)
    label = answer.get("verdict") if isinstance(answer, dict) else None
    observed = isinstance(label, str) and label in VERDICTS
    result.update(
        scoring_version=VERSION,
        expected_verdict=rubric["verdict"],
        predicted_verdict=label if observed else None,
        verdict_label_observed=observed,
        verdict_label_correct=(label == rubric["verdict"]) if observed else None,
        unsupported_contradiction=(result["valid"] and label == "contradicted"
                                   and rubric["verdict"] != "contradicted"),
        human_review={dimension: "not_assessed" for dimension in HUMAN_DIMENSIONS},
    )
    return result


def summarize(records):
    summary = legacy.summarize(records)
    for variant, row in summary.items():
        scores = [r["score"] for r in records if r["variant"] == variant and "score" in r]
        require(all(s.get("scoring_version") == VERSION for s in scores), "Mixed scoring versions")
        valid = [s for s in scores if s["valid"]]
        observed = [s for s in scores if s["verdict_label_observed"]]
        correct = sum(s["verdict_label_correct"] for s in observed)
        confusion = {expected: {predicted: 0 for predicted in VERDICTS} for expected in VERDICTS}
        for item in valid:
            confusion[item["expected_verdict"]][item["predicted_verdict"]] += 1
        row.update(
            scoring_version=VERSION,
            valid_outputs=len(valid),
            unsupported_contradiction=sum(s["unsupported_contradiction"] for s in valid),
            verdict_label_diagnostic={"observed": len(observed), "correct": correct,
                                      "accuracy_among_observed": correct / len(observed) if observed else None},
            confusion_matrix_valid_outputs=confusion,
            metric_denominators={"strict_accuracy": row["attempted"],
                                 "verdict_label_diagnostic": len(observed),
                                 "unsupported_support": len(valid),
                                 "unsupported_contradiction": len(valid),
                                 "unnecessary_abstention": len(valid),
                                 "required_citations_present": len(valid),
                                 "required_limitations_present": len(valid)},
            human_review={dimension: "not_assessed" for dimension in HUMAN_DIMENSIONS},
        )
    return summary


def review_template(records):
    return {"format": "receipts-human-review-v0.2", "status": "not_reviewed", "rows": [
        {"case_id": r["case_id"], "variant": r["variant"], "record_sha256": canonical_hash(r),
         "response_status": r["status"], "reviewer": None, "reviewed_at_utc": None,
         **{dimension: {"status": "not_reviewed", "notes": ""} for dimension in HUMAN_DIMENSIONS}}
        for r in records
    ]}


def summary_lines(summary):
    lines = ["# RECEIPTS v0.2 development evaluation", "",
             "AI-assisted synthetic labels; no independent human adjudication or held-out evaluation.", "",
             "| Prompt | Attempts | Valid | Strict correct | Label-only correct/observed | Unsupported support | Unsupported contradiction | Unnecessary abstention | Invalid | API errors |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for variant, row in summary.items():
        label = row["verdict_label_diagnostic"]
        lines.append(f"| {variant} | {row['attempted']} | {row['valid_outputs']} | {row['verdict_correct']} | {label['correct']}/{label['observed']} | {row['unsupported_support']} | {row['unsupported_contradiction']} | {row['unnecessary_abstention']} | {row['invalid_outputs']} | {row['api_errors']} |")
    lines += ["", "Strict accuracy uses all attempts, including invalid outputs and API errors.",
              "The label-only diagnostic ignores other validation failures; it does not repair an invalid answer.",
              "Unsupported verdicts, abstention and citation/caveat presence use valid outputs only.",
              "Full denominators and the valid-output confusion matrix are in summary.json.", "",
              "Citation entailment, rationale fidelity and caveat adequacy are NOT ASSESSED by these counters.",
              "Complete a separate dated copy of human-review-template.json; do not edit original results or scores.",
              "A missing caveat code does not establish incorrect reasoning, nor does a present code establish sound reasoning.",
              "This suite and scorer differ from v0.1; do not compare headline scores as evidence of model improvement.", ""]
    return lines
