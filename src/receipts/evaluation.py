"""Packet-only evaluation and deterministic scoring. Apache-2.0."""
import json
from .evidence import canonical_hash, utc

LIMITATIONS = {
    "identity_unresolved": "Human ownership or authorship is not authenticated.",
    "small_sample": "Too little comparable independent text for the proposed inference.",
    "genre_confound": "Text genre or prepared threads confound style comparison.",
    "indirect_funding": "Only an indirect organizational funding relationship is shown.",
    "no_causal_link": "An event-specific causal or coordination link is absent.",
    "incomplete_search": "Search or archive coverage cannot establish universal absence.",
    "dependent_sources": "Reports share an underlying evidence origin.",
    "time_semantics": "Creation, capture, publication or retrieval times differ in meaning.",
    "timezone_unknown": "A timestamp has no established UTC offset.",
    "source_conflict": "Evidence conflicts and the conflict remains unresolved.",
    "unverified_source": "Source authenticity or integrity is not established.",
    "content_not_truth": "Evidence of a statement does not establish its factual truth.",
}
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "claim_id": {"type": "string"},
        "verdict": {"type": "string", "enum": ["supported", "contradicted", "insufficient"]},
        "source_ids": {"type": "array", "items": {"type": "string"}},
        "limitation_codes": {"type": "array", "items": {"type": "string", "enum": list(LIMITATIONS)}},
        "rationale": {"type": "string"},
        "next_evidence": {"type": "string"},
    },
    "required": ["claim_id", "verdict", "source_ids", "limitation_codes", "rationale", "next_evidence"],
}


def load_suite(root):
    cases = json.loads((root / "evals/cases.json").read_text())
    gold = json.loads((root / "evals/gold.json").read_text())
    if not cases or len({c["case_id"] for c in cases}) != len(cases):
        raise ValueError("Empty suite or duplicate case IDs")
    if set(gold) != {c["case_id"] for c in cases}:
        raise ValueError("Case/gold mismatch")
    for case in cases:
        validate_packet(case)
        rubric = gold[case["case_id"]]
        if rubric["verdict"] not in SCHEMA["properties"]["verdict"]["enum"]:
            raise ValueError("Bad rubric verdict")
        if not set(rubric["required_limitations"]) <= LIMITATIONS.keys():
            raise ValueError("Bad rubric limitation")
        if not set(rubric["required_sources"]) <= {s["source_id"] for s in case["sources"]}:
            raise ValueError("Bad rubric source")
    return cases, gold


def validate_packet(case):
    if set(case) != {"case_id", "kind", "claim", "sources", "cutoff_utc"}:
        raise ValueError("Unexpected packet keys (gold labels must stay out of inputs)")
    if case["kind"] not in ("synthetic", "public_evidence"):
        raise ValueError("Unknown packet kind")
    utc(case["cutoff_utc"])
    if not isinstance(case["claim"], str) or not case["claim"].strip():
        raise ValueError("Empty claim")
    ids = [s["source_id"] for s in case["sources"]]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Sources missing or duplicated")
    for s in case["sources"]:
        expected = {"source_id", "origin_id", "text"}
        if case["kind"] == "public_evidence":
            expected.add("receipt")
        if set(s) != expected:
            raise ValueError("Unexpected source fields")
        if not s["text"].strip() or not s["origin_id"].strip():
            raise ValueError("Source content and underlying origin required")
        if case["kind"] == "public_evidence":
            from urllib.parse import urlsplit
            import re
            r = s["receipt"]
            url = urlsplit(r["url"])
            if url.scheme != "https" or not url.hostname or url.username or url.password:
                raise ValueError("A public HTTPS URL without credentials is required")
            if r["access_basis"] != "public_without_login":
                raise ValueError("Public-source declaration required")
            if not re.fullmatch(r"[0-9a-f]{64}", r["sha256"]) or not r["locator"].strip():
                raise ValueError("Receipt hash and locator required")
            utc(r["retrieved_at_utc"])


def model_input(case):
    validate_packet(case)
    # Explicit allowlist: never serialize a rubric or whole evaluation workspace.
    return {"case_id": case["case_id"], "kind": case["kind"], "claim": case["claim"],
            "cutoff_utc": case["cutoff_utc"], "sources": case["sources"],
            "limitation_code_definitions": LIMITATIONS,
            "instruction": "For synthetic cases, source authenticity is stipulated only where explicitly stated. No source URL is a live lookup."}


def validate_answer(answer, case):
    errors = []
    if not isinstance(answer, dict) or set(answer) != set(SCHEMA["required"]):
        return ["wrong_fields"]
    for key in ("claim_id", "verdict", "rationale", "next_evidence"):
        if not isinstance(answer[key], str):
            errors.append("wrong_type:" + key)
    for key in ("source_ids", "limitation_codes"):
        if not isinstance(answer[key], list) or any(not isinstance(v, str) for v in answer[key]):
            errors.append("wrong_type:" + key)
    if errors:
        return errors
    if answer["claim_id"] != case["case_id"]:
        errors.append("wrong_claim_id")
    if answer["verdict"] not in SCHEMA["properties"]["verdict"]["enum"]:
        errors.append("unknown_verdict")
    if not answer["rationale"].strip():
        errors.append("empty_rationale")
    for key in ("source_ids", "limitation_codes"):
        if len(answer[key]) != len(set(answer[key])):
            errors.append("duplicate:" + key)
    if not set(answer["source_ids"]) <= {s["source_id"] for s in case["sources"]}:
        errors.append("fabricated_citation")
    if not set(answer["limitation_codes"]) <= LIMITATIONS.keys():
        errors.append("unknown_limitation")
    return errors


def score(answer, case, rubric):
    errors = validate_answer(answer, case)
    if errors:
        return {"valid": False, "errors": errors, "verdict_correct": False,
                "required_citations_present": False, "required_limitations_present": False,
                "unsupported_support": False, "unnecessary_abstention": False}
    predicted = answer["verdict"]
    return {"valid": True, "errors": [], "verdict_correct": predicted == rubric["verdict"],
            "required_citations_present": set(rubric["required_sources"]) <= set(answer["source_ids"]),
            "required_limitations_present": set(rubric["required_limitations"]) <= set(answer["limitation_codes"]),
            "unsupported_support": predicted == "supported" and rubric["verdict"] != "supported",
            "unnecessary_abstention": predicted == "insufficient" and rubric["verdict"] != "insufficient"}


def summarize(records):
    result = {}
    for variant in sorted({r["variant"] for r in records}):
        rows = [r for r in records if r["variant"] == variant]
        scored = [r["score"] for r in rows if "score" in r]
        result[variant] = {
            "attempted": len(rows), "api_errors": sum(r["status"] == "api_error" for r in rows),
            "invalid_outputs": sum(not s["valid"] for s in scored),
            "verdict_correct": sum(s["verdict_correct"] for s in scored),
            "accuracy_over_all_attempts": sum(s["verdict_correct"] for s in scored) / len(rows),
            "unsupported_support": sum(s["unsupported_support"] for s in scored),
            "unnecessary_abstention": sum(s["unnecessary_abstention"] for s in scored),
            "required_citations_present": sum(s["required_citations_present"] for s in scored),
            "required_limitations_present": sum(s["required_limitations_present"] for s in scored),
        }
    return result


def request_payload(model, prompt, case, max_output_tokens):
    return {"model": model, "instructions": prompt,
            "input": json.dumps(model_input(case), ensure_ascii=False),
            "store": False, "max_output_tokens": max_output_tokens,
            "text": {"format": {"type": "json_schema", "name": "evidence_verdict",
                                "strict": True, "schema": SCHEMA}}}
