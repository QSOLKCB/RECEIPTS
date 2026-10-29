"""Versioned claim/scoring regressions; every transport is offline. Apache-2.0."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from receipts import evaluation as old, evaluation_v2 as new, runner
from receipts.evidence import canonical_hash

ROOT = Path(__file__).resolve().parents[1]


class ClaimSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases, cls.gold = new.load_suite(ROOT)
        cls.by_id = {c["case_id"]: c for c in cls.cases}

    def answer(self, case, verdict=None):
        rubric = self.gold[case["case_id"]]
        return {"claim_id": case["case_id"], "verdict": verdict or rubric["verdict"],
                "source_ids": list(rubric["required_sources"]),
                "limitation_codes": list(rubric["required_limitations"]),
                "rationale": "Local test fixture, not model evidence.", "next_evidence": ""}

    def record(self, case, answer):
        score = new.score(answer, case, self.gold[case["case_id"]])
        return {"case_id": case["case_id"], "variant": "receipts", "answer": answer,
                "status": "scored" if score["valid"] else "invalid_output", "score": score}

    def test_fact_and_sufficiency_pairs_use_identical_sources_but_distinct_propositions(self):
        for factual, sufficient in (("control-fact", "control-evidence"),
                                     ("style-authors-fact", "style-evidence")):
            a, b = [self.by_id["v02-" + slug] for slug in (factual, sufficient)]
            self.assertEqual(a["sources"], b["sources"])
            self.assertEqual(a["claim_type"], "factual")
            self.assertEqual(b["claim_type"], "evidentiary_sufficiency")
            self.assertEqual(self.gold[a["case_id"]]["verdict"], "insufficient")
            self.assertEqual(self.gold[b["case_id"]]["verdict"], "contradicted")
            self.assertNotEqual(a["claim"], b["claim"])

    def test_positive_negative_and_uncertain_controls_prevent_blanket_abstention(self):
        counts = {v: sum(r["verdict"] == v for r in self.gold.values()) for v in new.VERDICTS}
        self.assertEqual(counts, {"supported": 5, "contradicted": 6, "insufficient": 5})
        self.assertEqual(sum(new.score(self.answer(c, "insufficient"), c, self.gold[c["case_id"]])
                             ["verdict_correct"] for c in self.cases), 5)
        for case in self.cases:
            rubric = self.gold[case["case_id"]]
            self.assertTrue(case["scope"])
            self.assertEqual(set(rubric["verdict_examples"]), set(new.VERDICTS))
            self.assertEqual(rubric["review_status"], "not_independently_reviewed")

    def test_all_nine_verdict_pairs_have_explicit_directional_errors(self):
        case = self.cases[0]
        for expected in new.VERDICTS:
            rubric = {**self.gold[case["case_id"]], "verdict": expected}
            for predicted in new.VERDICTS:
                with self.subTest(expected=expected, predicted=predicted):
                    result = new.score(self.answer(case, predicted), case, rubric)
                    self.assertTrue(result["valid"])
                    self.assertEqual(result["verdict_correct"], predicted == expected)
                    self.assertEqual(result["unsupported_support"], predicted == "supported" and expected != "supported")
                    self.assertEqual(result["unsupported_contradiction"], predicted == "contradicted" and expected != "contradicted")
                    self.assertEqual(result["unnecessary_abstention"], predicted == "insufficient" and expected != "insufficient")

    def test_wrong_id_remains_invalid_even_when_label_diagnostic_is_correct(self):
        case = self.cases[0]
        answer = self.answer(case)
        answer["claim_id"] = "different-case"
        score = new.score(answer, case, self.gold[case["case_id"]])
        self.assertFalse(score["valid"])
        self.assertFalse(score["verdict_correct"])
        self.assertTrue(score["verdict_label_correct"])
        self.assertIn("wrong_claim_id", score["errors"])
        self.assertFalse(score["unsupported_contradiction"])

    def test_malformed_labels_have_no_label_diagnostic(self):
        for answer in (None, [], {}, {"verdict": []}, {"verdict": "unknown"}):
            score = new.score(answer, self.cases[0], self.gold[self.cases[0]["case_id"]])
            self.assertFalse(score["valid"])
            self.assertFalse(score["verdict_label_observed"])
            self.assertIsNone(score["verdict_label_correct"])

    def test_fabricated_citations_cannot_become_valid_directional_scores(self):
        case = self.cases[0]
        answer = self.answer(case, "contradicted")
        answer["source_ids"] = ["invented"]
        result = new.score(answer, case, self.gold[case["case_id"]])
        self.assertFalse(result["valid"])
        self.assertIn("fabricated_citation", result["errors"])
        self.assertFalse(result["unsupported_contradiction"])

    def test_prose_and_caveat_codes_are_not_automatically_equated(self):
        case = self.cases[0]
        answer = self.answer(case)
        answer.update(limitation_codes=[], rationale="Payment establishes neither control nor its absence.")
        result = new.score(answer, case, self.gold[case["case_id"]])
        self.assertTrue(result["verdict_correct"])
        self.assertFalse(result["required_limitations_present"])
        self.assertEqual(set(result["human_review"].values()), {"not_assessed"})
        answer.update(limitation_codes=["no_causal_link"], rationale="The donor definitely controlled everything.")
        result = new.score(answer, case, self.gold[case["case_id"]])
        self.assertTrue(result["required_limitations_present"])
        self.assertEqual(set(result["human_review"].values()), {"not_assessed"})

    def test_summary_keeps_strict_label_validity_and_failure_denominators_separate(self):
        case = self.cases[0]
        wrong_id = self.answer(case)
        wrong_id["claim_id"] = "wrong"
        records = [self.record(case, self.answer(case)),
                   self.record(case, self.answer(case, "supported")),
                   self.record(case, self.answer(case, "contradicted")),
                   self.record(case, wrong_id), self.record(case, None),
                   {"case_id": case["case_id"], "variant": "receipts", "status": "api_error"}]
        result = new.summarize(records)["receipts"]
        self.assertEqual((result["attempted"], result["valid_outputs"], result["invalid_outputs"], result["api_errors"]), (6, 3, 2, 1))
        self.assertEqual(result["accuracy_over_all_attempts"], 1 / 6)
        self.assertEqual(result["verdict_label_diagnostic"], {"observed": 4, "correct": 2, "accuracy_among_observed": 0.5})
        self.assertEqual(result["unsupported_support"], 1)
        self.assertEqual(result["unsupported_contradiction"], 1)
        self.assertEqual(result["metric_denominators"]["unsupported_contradiction"], 3)
        self.assertEqual(result["confusion_matrix_valid_outputs"]["insufficient"],
                         {"supported": 1, "contradicted": 1, "insufficient": 1})

    def test_empty_and_api_only_summaries_do_not_claim_perfect_performance(self):
        self.assertEqual(new.summarize([]), {})
        row = new.summarize([{"variant": "baseline", "status": "api_error"}])["baseline"]
        self.assertEqual(row["valid_outputs"], 0)
        self.assertEqual(row["accuracy_over_all_attempts"], 0)
        self.assertIsNone(row["verdict_label_diagnostic"]["accuracy_among_observed"])
        self.assertEqual(row["metric_denominators"]["unsupported_support"], 0)

    def test_mixed_scoring_versions_are_rejected(self):
        case = self.cases[0]
        record = self.record(case, self.answer(case))
        del record["score"]["scoring_version"]
        with self.assertRaises(ValueError):
            new.summarize([record])

    def test_model_input_excludes_rubrics_examples_lineage_and_review_metadata(self):
        forbidden = {"verdict", "required_sources", "required_limitations", "justification",
                     "verdict_examples", "legacy_case_ids", "review_status", "gold"}
        for case in self.cases:
            packet = new.model_input(case)
            self.assertFalse(forbidden & set(packet))
            self.assertEqual(packet["claim_type"], case["claim_type"])
            self.assertEqual(packet["scope"], case["scope"])
            for key in forbidden:
                with self.assertRaises(ValueError):
                    new.model_input({**case, key: "RUBRIC_LEAK_SENTINEL"})
        payload = new.request_payload("offline", "prompt", self.cases[0], 1200)
        self.assertEqual(payload["text"]["format"]["schema"], old.SCHEMA)
        self.assertFalse(payload["store"])

    def test_packet_rejects_missing_scope_bad_origins_and_unknown_claim_type(self):
        for key, value in (("scope", ""), ("claim_type", "guess"), ("sources", [])):
            with self.assertRaises(ValueError):
                new.model_input({**self.cases[0], key: value})
        case = copy.deepcopy(self.cases[0])
        case["sources"][0]["origin_id"] = ""
        with self.assertRaises(ValueError):
            new.model_input(case)

    def test_suite_rejects_missing_rubric_examples_and_false_review_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "evals/v0.2").mkdir(parents=True)
            for path in ("evals/cases.json", "evals/gold.json", "evals/v0.2/cases.json",
                         "evals/v0.2/gold.json", "evals/v0.2/suite.json"):
                (root / path).write_bytes((ROOT / path).read_bytes())
            bad = copy.deepcopy(self.gold)
            del bad[self.cases[0]["case_id"]]["verdict_examples"]["contradicted"]
            (root / "evals/v0.2/gold.json").write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError, "Three verdict examples"):
                new.load_suite(root)
            (root / "evals/v0.2/gold.json").write_text(json.dumps(self.gold))
            metadata = new.load_metadata(ROOT)
            metadata["independent_human_review"] = "completed"
            (root / "evals/v0.2/suite.json").write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, "independent human adjudication"):
                new.load_suite(root)

    def test_review_template_is_unassessed_and_bound_to_exact_record(self):
        case = self.cases[0]
        record = self.record(case, self.answer(case))
        row = new.review_template([record])["rows"][0]
        self.assertEqual(row["record_sha256"], canonical_hash(record))
        self.assertIsNone(row["reviewer"])
        self.assertIsNone(row["reviewed_at_utc"])
        for dimension in new.HUMAN_DIMENSIONS:
            self.assertEqual(row[dimension], {"status": "not_reviewed", "notes": ""})
        record["answer"]["rationale"] = "different bytes"
        self.assertNotEqual(row["record_sha256"], canonical_hash(record))


class VersionedRunnerTests(unittest.TestCase):
    def test_dry_run_is_explicit_versioned_and_never_sends_gold(self):
        with tempfile.TemporaryDirectory() as directory, patch("receipts.runner.api_call") as api:
            output = Path(directory) / "v02"
            self.assertEqual(runner.run(ROOT, output, "offline", 16, 42, 1200, True, "v0.2"), 0)
            api.assert_not_called()
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["format"], "receipts-eval-v0.2")
            self.assertEqual(manifest["suite_version"], "v0.2")
            self.assertEqual(manifest["seed_for_case_selection_and_call_order"], 42)
            self.assertNotIn("seed_for_order_only", manifest)
            self.assertEqual(manifest["suite_metadata_sha256"], canonical_hash(new.load_metadata(ROOT)))
            self.assertEqual((manifest["planned_calls"], manifest["attempted_calls"]), (32, 0))
            requests = json.loads((output / "requests.json").read_text())
            cases, _ = new.load_suite(ROOT)
            by_id = {c["case_id"]: c for c in cases}
            prompts = json.loads((output / "prompts.json").read_text())
            for payload, (case_id, variant) in zip(requests, manifest["call_order"]):
                self.assertEqual(payload, new.request_payload("offline", prompts[variant], by_id[case_id], 1200))
                self.assertNotIn("verdict_examples", payload["input"])
            self.assertFalse((output / "summary.json").exists())
            self.assertFalse((output / "human-review-template.json").exists())
            with self.assertRaises(FileExistsError):
                runner.run(ROOT, output, "offline", 16, 42, 1200, True, "v0.2")

    def test_default_v01_retains_requests_and_manifest_format(self):
        with tempfile.TemporaryDirectory() as directory, patch("receipts.runner.api_call") as api:
            output = Path(directory) / "legacy"
            runner.run(ROOT, output, "offline", 16, 42, 1200, True)
            api.assert_not_called()
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["format"], "receipts-eval-v0.1")
            self.assertNotIn("scoring_version", manifest)
            self.assertEqual(manifest["seed_for_order_only"], 42)
            cases, _ = old.load_suite(ROOT)
            by_id = {c["case_id"]: c for c in cases}
            prompts = json.loads((output / "prompts.json").read_text())
            requests = json.loads((output / "requests.json").read_text())
            self.assertEqual(requests, [old.request_payload("offline", prompts[v], by_id[c], 1200)
                                        for c, v in manifest["call_order"]])
            self.assertFalse((output / "suite.json").exists())

    def test_unknown_suite_fails_before_artifacts_or_transport(self):
        with tempfile.TemporaryDirectory() as directory, patch("receipts.runner.api_call") as api:
            output = Path(directory) / "bad"
            with self.assertRaisesRegex(ValueError, "Unknown suite"):
                runner.run(ROOT, output, "offline", 16, 42, 1200, True, "../v0.1")
            self.assertFalse(output.exists())
            api.assert_not_called()

    def test_mock_v02_run_preserves_invalid_output_and_writes_review_template(self):
        def reply(payload, key):
            packet = json.loads(payload["input"])
            return {"status": "completed", "text": json.dumps({
                "claim_id": "wrong-id", "verdict": "insufficient", "source_ids": [],
                "limitation_codes": [], "rationale": "Local stub only.", "next_evidence": ""}),
                "response_id": "mock-only", "returned_model": "mock", "usage": None,
                "response_sha256": canonical_hash(packet)}
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"OPENAI_API_KEY": "test-placeholder"}), patch("receipts.runner.api_call", side_effect=reply) as api:
            output = Path(directory) / "mock"
            self.assertEqual(runner.run(ROOT, output, "mock", 1, 42, 1200, False, "v0.2"), 1)
            self.assertEqual(api.call_count, 2)
            records = [json.loads(line) for line in (output / "results.jsonl").read_text().splitlines()]
            self.assertTrue(all(r["status"] == "invalid_output" for r in records))
            self.assertEqual(json.loads((output / "human-review-template.json").read_text()), new.review_template(records))
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["receipts"]["invalid_outputs"], 1)
            self.assertIn("Unsupported contradiction", (output / "summary.md").read_text())
            self.assertIn("NOT ASSESSED", (output / "summary.md").read_text())

    def test_missing_credentials_and_transport_failure_still_stop_v02(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict("os.environ", {"OPENAI_API_KEY": ""}), patch("receipts.runner.api_call") as api:
                self.assertEqual(runner.run(ROOT, Path(directory) / "blocked", "mock", 16, 42, 1200, False, "v0.2"), 2)
                api.assert_not_called()
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-placeholder"}), patch("receipts.runner.api_call", side_effect=RuntimeError("http_401")) as api:
                output = Path(directory) / "failed"
                self.assertEqual(runner.run(ROOT, output, "mock", 16, 42, 1200, False, "v0.2"), 1)
                self.assertEqual(api.call_count, 1)
                manifest = json.loads((output / "manifest.json").read_text())
                self.assertEqual((manifest["attempted_calls"], manifest["completed_calls"]), (1, 0))

    def test_valid_mock_v02_run_reports_scores_without_inventing_human_review(self):
        cases, gold = new.load_suite(ROOT)
        def reply(payload, key):
            case_id = json.loads(payload["input"])["case_id"]
            rubric = gold[case_id]
            answer = {"claim_id": case_id, "verdict": rubric["verdict"],
                      "source_ids": rubric["required_sources"],
                      "limitation_codes": rubric["required_limitations"],
                      "rationale": "Synthetic scorer fixture; not a model result.", "next_evidence": ""}
            return {"status": "completed", "text": json.dumps(answer), "response_id": "mock-only",
                    "returned_model": "mock", "usage": None, "response_sha256": "0" * 64}
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"OPENAI_API_KEY": "test-placeholder"}), patch("receipts.runner.api_call", side_effect=reply):
            output = Path(directory) / "mock-valid"
            self.assertEqual(runner.run(ROOT, output, "mock", 16, 42, 1200, False, "v0.2"), 0)
            summary = json.loads((output / "summary.json").read_text())
            for row in summary.values():
                self.assertEqual((row["verdict_correct"], row["valid_outputs"]), (len(cases), len(cases)))
                self.assertEqual(row["unsupported_contradiction"], 0)
                self.assertEqual(set(row["human_review"].values()), {"not_assessed"})
            review = json.loads((output / "human-review-template.json").read_text())
            self.assertEqual(len(review["rows"]), 32)
            self.assertTrue(all(r["reviewer"] is None for r in review["rows"]))

    def test_all_historical_requests_scores_and_summaries_replay_with_v01(self):
        current_cases, current_gold = old.load_suite(ROOT)
        paths = ["2026-10-30-gpt-5.4-mini", "2026-10-30-gpt4-comparison/gpt-4o",
                 "2026-10-30-gpt4-comparison/gpt-4.1", "2026-10-30-gpt-5.3-codex"]
        count = 0
        for path in paths:
            folder = ROOT / "experiments" / path
            manifest, gold, prompts = [json.loads((folder / (name + ".json")).read_text())
                                        for name in ("manifest", "gold", "prompts")]
            cases = {c["case_id"]: c for c in json.loads((folder / "cases.json").read_text())}
            self.assertEqual({c["case_id"]: c for c in current_cases}, cases)
            self.assertEqual(current_gold, gold)
            self.assertEqual(prompts, {"baseline": (ROOT / "prompts/baseline.txt").read_text(),
                                       "receipts": (ROOT / "prompts/auditor.txt").read_text()})
            records = [json.loads(line) for line in (folder / "results.jsonl").read_text().splitlines()]
            for record in records:
                case = cases[record["case_id"]]
                self.assertEqual(old.score(record["answer"], case, gold[case["case_id"]]), record["score"])
                payload = old.request_payload(manifest["model_requested"], prompts[record["variant"]],
                                               case, manifest["max_output_tokens_per_call"])
                self.assertEqual(canonical_hash(payload), record["request_sha256"])
                count += 1
            self.assertEqual(old.summarize(records), json.loads((folder / "summary.json").read_text()))
        self.assertEqual(count, 128)


if __name__ == "__main__":
    unittest.main()
