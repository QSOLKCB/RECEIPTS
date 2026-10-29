"""Verify saved experiment without network or provider credentials. Apache-2.0."""
from pathlib import Path
from decimal import Decimal
import hashlib
import json

ROOT = Path(__file__).resolve().parent


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def canonical(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def main():
    for line in (ROOT / "SHA256SUMS.txt").read_text().splitlines():
        digest, name = line.split("  ", 1)
        assert Path(name).name == name
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    manifest, cases, gold, prompts = [load(x + ".json") for x in ("manifest", "cases", "gold", "prompts")]
    rows = [json.loads(line) for line in (ROOT / "results.jsonl").read_text().splitlines()]
    assert canonical(cases) == manifest["cases_sha256"]
    assert canonical(gold) == manifest["gold_sha256"]
    assert {k: canonical(v) for k, v in prompts.items()} == manifest["prompt_sha256"]
    assert len(rows) == manifest["completed_calls"] == manifest["attempted_calls"] == 32
    assert len({(r["case_id"], r["variant"]) for r in rows}) == 32
    assert [[r["case_id"], r["variant"]] for r in rows] == manifest["call_order"]
    assert {r["response"]["returned_model"] for r in rows} == {manifest["model_requested"]}
    summaries, review = load("summary.json"), load("review-metrics.json")
    for row in rows:
        assert row["status"] == "scored" and row["response"]["status"] == "completed"
        assert json.loads(row["response"]["text"]) == row["answer"]
        a, g, s = row["answer"], gold[row["case_id"]], row["score"]
        assert a["claim_id"] == row["case_id"]
        assert s["verdict_correct"] == (a["verdict"] == g["verdict"])
        assert s["required_citations_present"] == (set(g["required_sources"]) <= set(a["source_ids"]))
        assert s["required_limitations_present"] == (set(g["required_limitations"]) <= set(a["limitation_codes"]))
        assert s["unsupported_support"] == (a["verdict"] == "supported" and g["verdict"] != "supported")
        assert s["unnecessary_abstention"] == (a["verdict"] == "insufficient" and g["verdict"] != "insufficient")
    cost = Decimal(0)
    for variant in ("baseline", "receipts"):
        selected = [r for r in rows if r["variant"] == variant]
        summary, usage = summaries[variant], review["variants"][variant]
        assert len(selected) == summary["attempted"] == 16
        for field in ("verdict_correct", "unsupported_support", "unnecessary_abstention", "required_citations_present", "required_limitations_present"):
            assert sum(r["score"][field] for r in selected) == summary[field]
        assert summary["accuracy_over_all_attempts"] == summary["verdict_correct"] / 16
        for field in ("input_tokens", "output_tokens", "total_tokens"):
            assert sum(r["response"]["usage"][field] for r in selected) == usage[field]
        assert usage["cached_input_tokens"] == sum(r["response"]["usage"]["input_tokens_details"]["cached_tokens"] for r in selected)
        assert usage["reasoning_tokens"] == sum(r["response"]["usage"]["output_tokens_details"]["reasoning_tokens"] for r in selected)
        dollars = (Decimal(usage["input_tokens"] - usage["cached_input_tokens"]) * Decimal("0.75") + Decimal(usage["cached_input_tokens"]) * Decimal("0.075") + Decimal(usage["output_tokens"]) * Decimal("4.50")) / Decimal(1000000)
        assert dollars == Decimal(usage["estimated_usd"])
        cost += dollars
        assert usage["unsupported_contradiction_against_frozen_gold"] == sum(r["answer"]["verdict"] == "contradicted" and gold[r["case_id"]]["verdict"] != "contradicted" for r in selected)
    assert cost == Decimal(review["total_estimated_usd"])
    print("PASS: bundle hashes, 32 outputs, frozen scores and token/cost arithmetic. No inference performed.")


if __name__ == "__main__":
    main()
