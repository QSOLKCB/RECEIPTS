"""Behavioral regressions and adversarial checks. SPDX-License-Identifier: Apache-2.0."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from receipts.evidence import (snowflake_utc, utc, timestamp_delta_seconds,
                               receipt, direct_funding, summarize_posts)
from receipts.evaluation import load_suite, model_input, score, validate_answer
from receipts.runner import run

ROOT = Path(__file__).resolve().parents[1]


class MetadataTests(unittest.TestCase):
    def test_known_snowflake(self):
        # Fixed ID fixture; timestamp checked using integer arithmetic.
        self.assertEqual(snowflake_utc("1273816504776982529"), "2020-06-19T03:14:55.762Z")

    def test_timezone_crosses_date(self):
        self.assertEqual(utc("2026-09-01T00:30:00+09:30"), "2026-08-31T15:00:00.000Z")

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            utc("2026-09-01T00:30:00")

    def test_id_numeric_coercion_rejected(self):
        for value in (1273816504776982529, 1.27e18, "1e18", "-1", str(2**63)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                snowflake_utc(value)

    def test_capture_delta_is_not_creation(self):
        self.assertEqual(timestamp_delta_seconds("1273816504776982529", "2020-06-20T03:14:55.762Z"), 86400)

    def test_receipt_hash_and_access_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "capture.txt"
            p.write_text("abc")
            r = receipt(p, "https://example.org/post", "2026-10-29T00:00:00Z", "public_without_login", "post 123")
            self.assertEqual(r["sha256"], "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
            self.assertEqual(r["access_verification"], "researcher_attested")
            with self.assertRaises(ValueError):
                receipt(p, "https://example.org/post", "2026-10-29T00:00:00Z", "private_message", "post 123")
            with self.assertRaises(ValueError):
                receipt(p, "https://user:password@example.org/post", "2026-10-29T00:00:00Z", "public_without_login", "post 123")


class AnalysisTests(unittest.TestCase):
    def test_indirect_grant_is_not_personal_payment(self):
        edges = [{"payer": "D", "payee": "L", "amount": "100000", "currency": "USD", "status": "paid", "source_ids": ["S1"]}]
        result = direct_funding(edges, "D", "P")
        self.assertEqual(result["direct_payment_edges"], [])
        self.assertEqual(result["finding"], "not_established_in_supplied_edges")

    def test_commitment_is_not_payment(self):
        edge = {"payer": "D", "payee": "P", "amount": "5000", "status": "committed", "source_ids": ["S1"]}
        self.assertEqual(direct_funding([edge], "D", "P")["direct_payment_edges"], [])

    def test_direct_payment_does_not_prove_direction(self):
        edge = {"payer": "D", "payee": "P", "amount": "5000", "status": "paid", "source_ids": ["S1"]}
        result = direct_funding([edge], "D", "P")
        self.assertEqual(len(result["direct_payment_edges"]), 1)
        self.assertFalse(result["direction_or_coordination_established"])

    def test_nonfinite_payment_is_not_evidence(self):
        for amount in ("NaN", "Infinity", "-Infinity"):
            edge = {"payer": "D", "payee": "P", "amount": amount, "status": "paid", "source_ids": ["S1"]}
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                direct_funding([edge], "D", "P")

    def posts(self):
        base = {"platform": "x", "account_id": "111", "is_target": True,
                "is_retweet": False, "is_quote": False, "is_partial": False,
                "thread_id": None, "text": "hello world"}
        return [dict(base, post_id=str(i)) for i in range(1, 6)]

    def test_style_excludes_context_quotes_and_threads_sensitivity(self):
        posts = self.posts()
        posts[0]["is_target"] = False
        posts[1]["is_retweet"] = True
        posts[2]["is_quote"] = True
        posts[3]["thread_id"] = "thread1"
        result = summarize_posts(posts)
        row = result["groups"][0]
        self.assertEqual(row["posts"], 2)
        self.assertEqual(row["without_threads_posts"], 1)
        self.assertEqual(row["without_threads_tokens"], 2)
        self.assertIsNone(row["authorship_probability"])

    def test_duplicate_posts_rejected(self):
        posts = self.posts()
        posts.append(posts[0])
        with self.assertRaises(ValueError):
            summarize_posts(posts)

    def test_distinct_account_ids_remain_separate(self):
        posts = self.posts()
        posts[0]["account_id"] = "222"
        self.assertEqual(len(summarize_posts(posts)["groups"]), 2)

    def test_rounded_numeric_account_id_rejected(self):
        posts = self.posts()
        posts[0]["account_id"] = 1.2738165047769825e18
        with self.assertRaises(ValueError):
            summarize_posts(posts)


class EvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases, cls.gold = load_suite(ROOT)

    def answer(self, case):
        rubric = self.gold[case["case_id"]]
        return {"claim_id": case["case_id"], "verdict": rubric["verdict"],
                "source_ids": rubric["required_sources"], "limitation_codes": rubric["required_limitations"],
                "rationale": "Synthetic answer used to test the scorer, not a model result.",
                "next_evidence": ""}

    def test_gold_is_not_serialized_to_model(self):
        for case in self.cases:
            payload = model_input(case)
            self.assertNotIn("verdict", payload)
            self.assertNotIn("required_sources", payload)
            self.assertNotIn("gold", payload)
        bad = dict(self.cases[0], gold=self.gold)
        with self.assertRaises(ValueError):
            model_input(bad)

    def test_suite_requires_both_restraint_and_commitment(self):
        counts = {v: sum(g["verdict"] == v for g in self.gold.values())
                  for v in ["supported", "contradicted", "insufficient"]}
        self.assertEqual(counts, {"supported": 4, "contradicted": 4, "insufficient": 8})

    def test_always_abstain_scores_only_half(self):
        count = 0
        for case in self.cases:
            answer = self.answer(case)
            answer["verdict"] = "insufficient"
            count += score(answer, case, self.gold[case["case_id"]])["verdict_correct"]
        self.assertEqual(count, 8)

    def test_fabricated_citation_invalidates_answer(self):
        case = self.cases[0]
        answer = self.answer(case)
        answer["source_ids"] = ["invented"]
        self.assertIn("fabricated_citation", validate_answer(answer, case))
        self.assertFalse(score(answer, case, self.gold[case["case_id"]])["valid"])

    def test_wrong_claim_and_empty_rationale_rejected(self):
        case = self.cases[0]
        answer = self.answer(case)
        answer.update(claim_id="other", rationale="")
        self.assertEqual(set(validate_answer(answer, case)), {"wrong_claim_id", "empty_rationale"})

    def test_citation_presence_does_not_fix_wrong_verdict(self):
        case = self.cases[0]
        answer = self.answer(case)
        answer["verdict"] = "supported"
        result = score(answer, case, self.gold[case["case_id"]])
        self.assertTrue(result["required_citations_present"])
        self.assertTrue(result["unsupported_support"])
        self.assertFalse(result["verdict_correct"])

    def test_missing_key_never_counts_as_inference(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            output = Path(directory) / "run"
            with patch("receipts.runner.api_call") as api:
                self.assertEqual(run(ROOT, output, "test-model", 1, 42, 1200), 2)
                api.assert_not_called()
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "blocked_missing_api_key")
            self.assertEqual(manifest["completed_calls"], 0)

    def test_dry_run_has_no_model_calls_or_fake_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            with patch("receipts.runner.api_call") as api:
                self.assertEqual(run(ROOT, output, "test-model", 16, 42, 1200, True), 0)
                api.assert_not_called()
            self.assertFalse((output / "summary.json").exists())
            self.assertEqual(len(json.loads((output / "requests.json").read_text())), 32)
            with self.assertRaises(FileExistsError):
                run(ROOT, output, "test-model", 1, 42, 1200, True)

    def test_mock_transport_scores_outputs_and_preserves_receipts(self):
        by_id = {c["case_id"]: c for c in self.cases}
        def response(payload, key):
            case_id = json.loads(payload["input"])["case_id"]
            return {"status": "completed", "text": json.dumps(self.answer(by_id[case_id])),
                    "response_id": "mock-only", "returned_model": "mock", "usage": None,
                    "response_sha256": "0" * 64}
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"OPENAI_API_KEY": "test-placeholder"}), patch("receipts.runner.api_call", side_effect=response):
            output = Path(directory) / "run"
            self.assertEqual(run(ROOT, output, "mock", 2, 42, 1200), 0)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["receipts"]["verdict_correct"], 2)
            self.assertTrue((output / "prompts.json").exists())

    def test_api_failure_stops_without_retries(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"OPENAI_API_KEY": "test-placeholder"}), patch("receipts.runner.api_call", side_effect=RuntimeError("http_401")) as api:
            output = Path(directory) / "run"
            self.assertEqual(run(ROOT, output, "mock", 16, 42, 1200), 1)
            self.assertEqual(api.call_count, 1)
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "completed_with_errors")
            self.assertEqual(manifest["attempted_calls"], 1)
            self.assertEqual(manifest["completed_calls"], 0)


if __name__ == "__main__":
    unittest.main()
