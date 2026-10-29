"""Complex-evidence development packets using the unchanged v0.2 verdict scorer. Apache-2.0."""
import json

from . import evaluation as legacy, evaluation_v2 as verdicts
from .action_review import DIMENSIONS, proposal, strict_json

VERSION = "v0.4"
SCORING_VERSION = "v0.2"
require, nonempty, string_list = verdicts.require, verdicts.nonempty, verdicts.string_list
score = verdicts.score
review_template = verdicts.review_template
NEXT_EVIDENCE_CONTRACT = (
    "Propose only a relevant, feasible next step using lawfully public information available without login. "
    "Document type alone does not establish public availability. State what the proposed evidence could "
    "establish for this exact claim, including when it would only provide partial information. "
    "If further public research is not warranted or no justified public route is available, explain why to stop. "
    "Do not acquire anything, invent a search, or treat proposed evidence as already obtained."
)


def validate_packet(case):
    require(isinstance(case, dict) and set(case) == verdicts.PACKET_KEYS, "Unexpected v0.4 packet fields")
    require(nonempty(case["case_id"]) and case["case_id"].startswith("v04-"), "Expected v04 case ID")
    require(case["kind"] == "synthetic" and case["claim_type"] in ("factual", "evidentiary_sufficiency"), "Invalid case kind/type")
    require(all(nonempty(case[k]) for k in ("claim", "scope", "cutoff_utc")), "Claim, scope and cutoff required")
    require(isinstance(case["sources"], list) and bool(case["sources"]), "Sources required")
    for source in case["sources"]:
        require(isinstance(source, dict) and set(source) == {"source_id", "origin_id", "text"}
                and all(nonempty(v) for v in source.values()), "Invalid source")
    legacy.validate_packet({k: case[k] for k in verdicts.PACKET_KEYS - {"claim_type", "scope"}})


def validate_suite(cases, gold, metadata):
    require(isinstance(metadata, dict) and metadata.get("suite_version") == VERSION
            and metadata.get("scoring_version") == SCORING_VERSION and metadata.get("case_count") == 16,
            "Unexpected v0.4 suite metadata")
    require(metadata.get("independent_human_review") == "not_performed" and metadata.get("held_out") is False,
            "Development rubrics have no independent human adjudication or held-out status")
    require(isinstance(cases, list) and len(cases) == 16, "Expected 16 development cases")
    for case in cases:
        validate_packet(case)
    ids = [c["case_id"] for c in cases]
    require(len(ids) == len(set(ids)) and isinstance(gold, dict) and set(gold) == set(ids), "Duplicate IDs or case/gold mismatch")
    for case in cases:
        rubric = gold[case["case_id"]]
        require(isinstance(rubric, dict) and set(rubric) == verdicts.RUBRIC_KEYS | {"action_review"}, "Unexpected rubric fields")
        require(rubric["verdict"] in verdicts.VERDICTS and nonempty(rubric["justification"]), "Invalid verdict rubric")
        require(string_list(rubric["required_sources"]) and set(rubric["required_sources"]) <= {s["source_id"] for s in case["sources"]}, "Unknown rubric sources")
        require(string_list(rubric["required_limitations"]) and set(rubric["required_limitations"]) <= legacy.LIMITATIONS.keys(), "Unknown limitations")
        require(string_list(rubric["legacy_case_ids"]), "Invalid lineage list")
        examples = rubric["verdict_examples"]
        require(isinstance(examples, dict) and set(examples) == set(verdicts.VERDICTS)
                and all(nonempty(v) for v in examples.values()), "Three verdict examples required")
        require(rubric["review_status"] == "not_independently_reviewed", "Unsupported rubric review status")
        action = rubric["action_review"]
        require(isinstance(action, dict) and set(action) == {"criteria", "acceptable_examples", "unacceptable_examples", "effect_limits", "stop_conditions"}, "Unexpected action rubric fields")
        require(isinstance(action["criteria"], dict) and set(action["criteria"]) == set(DIMENSIONS)
                and all(nonempty(v) for v in action["criteria"].values()), "All action criteria required")
        for name in ("acceptable_examples", "unacceptable_examples"):
            require(string_list(action[name]) and bool(action[name]), "Positive and negative action examples required")
        require(nonempty(action["effect_limits"]) and nonempty(action["stop_conditions"]), "Effect limits and stopping criteria required")
    require({g["verdict"] for g in gold.values()} == set(verdicts.VERDICTS), "All verdict controls required")


def load_metadata(root):
    return json.loads((root / "evals/v0.4/suite.json").read_text(encoding="utf-8"))


def load_suite(root):
    cases = json.loads((root / "evals/v0.4/cases.json").read_text(encoding="utf-8"))
    gold = json.loads((root / "evals/v0.4/gold.json").read_text(encoding="utf-8"))
    validate_suite(cases, gold, load_metadata(root))
    old_cases, _ = legacy.load_suite(root)
    old_ids = {c["case_id"] for c in old_cases}
    require(all(set(g["legacy_case_ids"]) <= old_ids for g in gold.values()), "Unknown historical lineage")
    return cases, gold


def model_input(case):
    validate_packet(case)
    packet = legacy.model_input({k: case[k] for k in verdicts.PACKET_KEYS - {"claim_type", "scope"}})
    packet.update(claim_type=case["claim_type"], scope=case["scope"],
                  claim_semantics=verdicts.SEMANTICS, next_evidence_contract=NEXT_EVIDENCE_CONTRACT)
    return packet


def request_payload(model, prompt, case, max_output_tokens):
    validate_packet(case)
    payload = legacy.request_payload(model, prompt,
                                     {k: case[k] for k in verdicts.PACKET_KEYS - {"claim_type", "scope"}}, max_output_tokens)
    payload["input"] = json.dumps(model_input(case), ensure_ascii=False)
    return payload


def parse_answer(text):
    try:
        return strict_json(text)
    except (ValueError, TypeError, RecursionError):
        return None


def summarize(records):
    summary = verdicts.summarize(records)
    for variant, row in summary.items():
        rows = [r for r in records if r["variant"] == variant]
        row["action_review"] = {"status": "not_reviewed", "structured_proposals": sum(proposal(r) is not None for r in rows),
                                "note": "No action-quality judgments are inferred from verdicts or text. Use the separate human action-review workflow."}
    return summary


def summary_lines(summary):
    lines = verdicts.summary_lines(summary)
    lines[0] = "# RECEIPTS v0.4 complex-evidence development evaluation"
    lines += ["Action quality is NOT REVIEWED. The verdict scorer remains v0.2.",
              "Use action-review-template.json and a separate dated report to record human assessments of public access, feasibility, relevance, sufficiency framing and stopping.",
              "Human rubric acceptance/disputes and the evidence's possible effect must also be recorded; no automated approval is implied.", ""]
    return lines
