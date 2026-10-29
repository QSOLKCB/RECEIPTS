"""Offline action-review mechanics. Reviewer/model fixtures are synthetic. Apache-2.0."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from receipts import action_review as review, evaluation_v3 as suite, runner
from receipts.evidence import canonical_hash

ROOT = Path(__file__).resolve().parents[1]


def make_run(directory, *, proposal="Consult the relevant public filing and state its limits.", invalid_id=False, api_error=False, incomplete=False):
    """No provider request: fabricate clearly marked response fixtures in a temp dir."""
    cases, gold = suite.load_suite(ROOT)
    def respond(payload, key):
        if api_error:
            raise RuntimeError("http_401")
        case_id = json.loads(payload["input"])["case_id"]
        rubric = gold[case_id]
        answer = {"claim_id": "invalid-id" if invalid_id else case_id, "verdict": rubric["verdict"],
                  "source_ids": rubric["required_sources"], "limitation_codes": rubric["required_limitations"],
                  "rationale": "Synthetic test fixture; not a model response.", "next_evidence": proposal}
        return {"status": "incomplete" if incomplete else "completed", "text": json.dumps(answer),
                "response_id": "synthetic-test-only", "returned_model": "stub", "usage": None,
                "response_sha256": "0" * 64}
    with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-placeholder"}), patch("receipts.runner.api_call", side_effect=respond), contextlib.redirect_stdout(io.StringIO()):
        runner.run(ROOT, directory, "stub", 2, 42, 1200, False, "v0.3")
    return json.loads((directory / "action-review-template.json").read_text())


def attest(row, kind="pursue"):
    row.update(reviewer="Synthetic reviewer fixture, not an actual adjudication",
               reviewed_at_utc="2026-10-30T00:00:00Z", review_basis="human", recommendation_kind=kind)
    row["rubric_review"] = {"status": "accepted", "notes": "Synthetic rubric acceptance for validation tests only."}


def rate(row, dimension, status):
    row["assessments"][dimension] = {"status": status, "notes": "Synthetic dimension notes for validation tests only."}


class ActionSuiteTests(unittest.TestCase):
    def test_overflow_answer_is_preserved_as_invalid_in_a_reviewable_run(self):
        for literal in ("1e999", "-1e999", "1E+999", "1.7976931348623159e308"):
            text = '{"next_evidence":"Review the public filing","overflow":' + literal + '}'
            with self.subTest(literal=literal), tempfile.TemporaryDirectory() as directory, patch.dict(
                    "os.environ", {"OPENAI_API_KEY": "synthetic-placeholder"}), patch(
                    "receipts.runner.api_call", return_value={"status": "completed", "text": text}), contextlib.redirect_stdout(io.StringIO()):
                output = Path(directory) / "run"
                self.assertEqual(runner.run(ROOT, output, "stub", 1, 42, 1200, False, "v0.3"), 1)
                manifest, _, _, records, _ = review.load_run(output)
                self.assertEqual(manifest["status"], "completed_with_errors")
                self.assertEqual((manifest["attempted_calls"], manifest["completed_calls"]), (2, 2))
                for record in records:
                    self.assertEqual(record["response"]["text"], text)
                    self.assertIsNone(record["answer"])
                    self.assertEqual(record["status"], "invalid_output")
                    self.assertFalse(record["score"]["valid"])
                report = review.report(output, output / "action-review-template.json", Path(directory) / "report")
                self.assertEqual(sum(v["unavailable_proposals"] for v in report["action_assessments"].values()), 2)
                self.assertEqual(sum(v["structured_proposals"] for v in report["action_assessments"].values()), 0)

    def test_sixteen_cases_cover_access_routes_stopping_and_effect_limits(self):
        cases, gold = suite.load_suite(ROOT)
        self.assertEqual(len(cases), 16)
        self.assertEqual({v: sum(g["verdict"] == v for g in gold.values()) for v in ("supported", "contradicted", "insufficient")},
                         {"supported": 3, "contradicted": 2, "insufficient": 11})
        for case in cases:
            action = gold[case["case_id"]]["action_review"]
            self.assertEqual(set(action["criteria"]), set(review.DIMENSIONS))
            self.assertTrue(action["acceptable_examples"] and action["unacceptable_examples"])
            self.assertTrue(action["effect_limits"] and action["stop_conditions"])

    def test_rubric_and_action_examples_never_enter_requests(self):
        cases, gold = suite.load_suite(ROOT)
        for case in cases:
            payload = suite.request_payload("offline", "prompt", case, 1200)
            packet = json.loads(payload["input"])
            self.assertIn("next_evidence_contract", packet)
            for key in ("action_review", "acceptable_examples", "unacceptable_examples", "justification", "verdict_examples", "review_status"):
                self.assertNotIn(key, packet)
                with self.assertRaises(ValueError):
                    suite.model_input({**case, key: "DO_NOT_LEAK"})
            self.assertFalse(payload["store"])
            self.assertNotIn("tools", payload)

    def test_missing_criteria_and_false_independent_review_fail(self):
        cases, gold = suite.load_suite(ROOT)
        metadata = suite.load_metadata(ROOT)
        bad = copy.deepcopy(gold)
        del bad[cases[0]["case_id"]]["action_review"]["criteria"]["public_access"]
        with self.assertRaises(ValueError):
            suite.validate_suite(cases, bad, metadata)
        with self.assertRaises(ValueError):
            suite.validate_suite(cases, gold, {**metadata, "independent_human_review": "completed"})

    def test_v03_dry_run_does_not_create_fictional_reviews_or_scores(self):
        with tempfile.TemporaryDirectory() as directory, patch("receipts.runner.api_call") as api:
            output = Path(directory) / "prepared"
            runner.run(ROOT, output, "offline", 16, 42, 1200, True, "v0.3")
            api.assert_not_called()
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual((manifest["format"], manifest["scoring_version"]), ("receipts-eval-v0.3", "v0.2"))
            self.assertEqual((manifest["planned_calls"], manifest["attempted_calls"]), (32, 0))
            self.assertFalse((output / "summary.json").exists())
            self.assertFalse((output / "action-review-template.json").exists())

    def test_v02_fixture_hashes_remain_frozen(self):
        expected = {
            "cases": "7cc2ee8167788b78c42016ec93fe57dc6dfb0487c2e181995653b7f272018543",
            "gold": "eb2e9b20539ce82da9840fb54d9c36b9917690cd5d2e22a37a686769a8309da9",
            "suite": "db9babd6f99d8731c9dd0b29694bc1e8292f0ccadfa6f4316f608f6a47b71f36"}
        for name, digest in expected.items():
            self.assertEqual(canonical_hash(json.loads((ROOT / "evals/v0.2" / (name + ".json")).read_text())), digest)

    def test_runner_main_reports_offline_success_and_friendly_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as directory, patch("receipts.runner.api_call") as api:
            output = Path(directory) / "prepared"
            args = ["--root", str(ROOT), "--suite", "v0.3", "--dry-run", "--output", str(output)]
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(runner.main(args), 0)
            self.assertIn("No model calls", stdout.getvalue())
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(runner.main(args), 2)
            self.assertIn("choose a fresh", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})
            api.assert_not_called()


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="receipts action review ")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.run = self.work / "run"
        self.template = make_run(self.run)
        self.records = [json.loads(line) for line in (self.run / "results.jsonl").read_text().splitlines()]

    def save_review(self, data):
        path = self.work / "review.json"
        path.write_text(json.dumps(data, indent=2) + "\n")
        return path

    def test_unreviewed_run_has_zero_coverage_and_no_pass_rate(self):
        review.validate_review(self.template, self.template)
        data = review.aggregate(self.template, self.records)
        for row in data.values():
            self.assertEqual(row["proposals_with_any_dimension_reviewed"], 0)
            self.assertEqual(row["proposals_with_any_reported_failure"], 0)
            for counts in row["dimensions"].values():
                self.assertEqual(counts["pass"], 0)
                self.assertEqual(counts["not_reviewed"], 2)
                self.assertIsNone(counts["failure_fraction_among_judged"])

    def test_correct_verdict_can_have_a_separately_reported_action_failure(self):
        data = copy.deepcopy(self.template)
        row = data["rows"][0]
        attest(row)
        rate(row, "public_access", "fail")
        review.validate_review(data, self.template)
        summary = review.aggregate(data, self.records)[row["variant"]]
        self.assertEqual(summary["strict_correct_responses_with_reported_action_failure"], 1)
        self.assertEqual(summary["proposals_with_any_dimension_reviewed"], 1)
        self.assertEqual(summary["proposals_with_all_dimensions_reviewed"], 0)
        self.assertEqual(summary["dimensions"]["public_access"]["failure_fraction_among_judged"], 1)

    def test_partial_evidence_is_not_automatically_a_framing_failure(self):
        data = copy.deepcopy(self.template)
        row = data["rows"][0]
        attest(row)
        for dimension in review.DIMENSIONS[:-1]:
            rate(row, dimension, "pass")
        rate(row, "stopping", "not_applicable")
        row["evidence_effect"] = {"status": "partial_only", "notes": "Proposed evidence is explicitly limited to indirect context."}
        review.validate_review(data, self.template)
        summary = review.aggregate(data, self.records)[row["variant"]]
        self.assertEqual(summary["evidence_effect"]["partial_only"], 1)
        self.assertEqual(summary["proposals_with_any_reported_failure"], 0)
        self.assertEqual(summary["proposals_with_all_dimensions_reviewed"], 1)

    def test_stop_requires_a_substantive_stopping_judgment(self):
        data = copy.deepcopy(self.template)
        row = data["rows"][0]
        attest(row, "stop")
        for dimension in review.DIMENSIONS[:-1]:
            rate(row, dimension, "not_applicable")
        rate(row, "stopping", "pass")
        row["evidence_effect"] = {"status": "not_applicable", "notes": "No acquisition proposed in this reviewer fixture."}
        review.validate_review(data, self.template)
        summary = review.aggregate(data, self.records)[row["variant"]]
        self.assertEqual(summary["dimensions"]["stopping"]["pass"], 1)
        self.assertIsNone(summary["dimensions"]["public_access"]["failure_fraction_among_judged"])
        rate(row, "stopping", "not_applicable")
        with self.assertRaises(ValueError):
            review.validate_review(data, self.template)

    def test_unresolved_and_disputed_entries_are_visible_not_passes(self):
        data = copy.deepcopy(self.template)
        row = data["rows"][0]
        attest(row, "unclear")
        row["rubric_review"] = {"status": "disputed", "notes": "Synthetic reviewer disputes the sufficiency wording."}
        rate(row, "sufficiency_framing", "unresolved")
        review.validate_review(data, self.template)
        result = review.aggregate(data, self.records)[row["variant"]]
        self.assertEqual(result["rubric_review"]["disputed"], 1)
        self.assertEqual(result["dimensions"]["sufficiency_framing"]["unresolved"], 1)
        self.assertIsNone(result["dimensions"]["sufficiency_framing"]["failure_fraction_among_judged"])

    def test_no_human_judgments_are_inferred_from_the_proposal_text(self):
        directory = self.work / "dangerous-proposal"
        data = make_run(directory, proposal="Obtain staff-only KYC records and all private bank statements.")
        records = [json.loads(line) for line in (directory / "results.jsonl").read_text().splitlines()]
        for summary in review.aggregate(data, records).values():
            self.assertEqual(summary["proposals_with_any_dimension_reviewed"], 0)
            self.assertEqual(summary["dimensions"]["public_access"]["fail"], 0)
        # The text is intentionally bad, but software must not impersonate a reviewer.

    def test_api_only_and_incomplete_outputs_are_unavailable_not_approved(self):
        for name, options in (("api", {"api_error": True}), ("incomplete", {"incomplete": True})):
            directory = self.work / name
            data = make_run(directory, **options)
            _, _, _, records, _ = review.load_run(directory)
            review.validate_review(data, data)
            for summary in review.aggregate(data, records).values():
                self.assertEqual(summary["structured_proposals"], 0)
                self.assertEqual(summary["unavailable_proposals"], summary["attempted_responses"])
                self.assertIsNone(summary["dimensions"]["public_access"]["failure_fraction_among_judged"])
            bad = copy.deepcopy(data)
            attest(bad["rows"][0])
            with self.assertRaises(ValueError):
                review.validate_review(bad, data)

    def test_invalid_claim_id_does_not_hide_a_reviewable_proposal(self):
        directory = self.work / "invalid"
        data = make_run(directory, invalid_id=True)
        _, _, _, records, summary = review.load_run(directory)
        for row in review.aggregate(data, records).values():
            self.assertEqual(row["invalid_outputs_with_structured_proposals"], 2)
        self.assertEqual(summary["receipts"]["verdict_correct"], 0)
        self.assertTrue(all(r["case_id"].startswith("v03-") for r in data["rows"]))

    def test_empty_proposal_is_reviewable_but_not_automatically_justified_stopping(self):
        directory = self.work / "empty"
        data = make_run(directory, proposal="")
        self.assertTrue(all(r["proposal"] == "" and r["recommendation_kind"] == "not_reviewed" for r in data["rows"]))

    def test_ratings_require_human_attribution_notes_utc_and_rubric_review(self):
        base = copy.deepcopy(self.template)
        row = base["rows"][0]
        attest(row)
        rate(row, "public_access", "fail")
        for field, value in (("reviewer", None), ("review_basis", "model_judge"),
                             ("reviewed_at_utc", "2026-10-30T00:00:00"), ("recommendation_kind", "not_reviewed")):
            data = copy.deepcopy(base)
            data["rows"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                review.validate_review(data, self.template)
        for mutate in (lambda r: r["assessments"]["public_access"].update(notes=""),
                       lambda r: r.update(rubric_review={"status": "not_reviewed", "notes": ""}),
                       lambda r: r["assessments"]["public_access"].update(status="approved")):
            data = copy.deepcopy(base)
            mutate(data["rows"][0])
            with self.assertRaises(ValueError):
                review.validate_review(data, self.template)

    def test_missing_duplicate_reordered_and_edited_rows_are_rejected(self):
        mutations = [lambda d: d["rows"].pop(),
                     lambda d: d["rows"].append(copy.deepcopy(d["rows"][0])),
                     lambda d: d["rows"].reverse(),
                     lambda d: d["rows"].__setitem__(1, copy.deepcopy(d["rows"][0])),
                     lambda d: d["rows"][0].update(proposal="rewritten proposal"),
                     lambda d: d["rows"][0].update(record_sha256="0" * 64),
                     lambda d: d["binding"].update(gold_sha256="0" * 64)]
        for mutate in mutations:
            data = copy.deepcopy(self.template)
            mutate(data)
            with self.assertRaises(ValueError):
                review.validate_review(data, self.template)

    def test_report_keeps_originals_and_copies_exact_review_bytes(self):
        original = {p.name: p.read_bytes() for p in self.run.iterdir()}
        path = self.save_review(self.template)
        output = self.work / "report"
        result = review.report(self.run, path, output)
        self.assertEqual((output / "review.json").read_bytes(), path.read_bytes())
        self.assertEqual(result["verdict_performance"], json.loads((self.run / "summary.json").read_text()))
        self.assertEqual(original, {p.name: p.read_bytes() for p in self.run.iterdir()})
        self.assertIn("not passes", (output / "report.md").read_text())
        before = {p.name: p.read_bytes() for p in output.iterdir()}
        with self.assertRaises(FileExistsError):
            review.report(self.run, path, output)
        self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})
        with self.assertRaises(ValueError):
            review.report(self.run, path, self.run / "nested-report")

    def test_changed_case_score_summary_response_and_manifest_fail_before_output(self):
        original = {p.name: p.read_bytes() for p in self.run.iterdir()}
        for name in ("cases.json", "summary.json", "manifest.json", "results.jsonl"):
            with self.subTest(file=name):
                if name == "results.jsonl":
                    rows = copy.deepcopy(self.records)
                    rows[0]["response"]["text"] = "{}"
                    (self.run / name).write_text("\n".join(json.dumps(r) for r in rows) + "\n")
                else:
                    obj = json.loads(original[name])
                    if name == "cases.json": obj[0]["claim"] = "Changed claim"
                    if name == "summary.json": obj["receipts"]["verdict_correct"] = 99
                    if name == "manifest.json": obj["attempted_calls"] = 99
                    (self.run / name).write_text(json.dumps(obj))
                output = self.work / ("bad-" + name)
                with self.assertRaises(ValueError):
                    review.report(self.run, self.save_review(self.template), output)
                self.assertFalse(output.exists())
                (self.run / name).write_bytes(original[name])

    def test_truncated_results_and_duplicate_call_plans_fail(self):
        original = (self.run / "results.jsonl").read_bytes()
        (self.run / "results.jsonl").write_text(json.dumps(self.records[0]) + "\n")
        with self.assertRaises(ValueError): review.load_run(self.run)
        (self.run / "results.jsonl").write_bytes(original)
        manifest = json.loads((self.run / "manifest.json").read_text())
        manifest["call_order"][1] = manifest["call_order"][0]
        (self.run / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaises(ValueError): review.load_run(self.run)

    def test_json_duplicate_keys_and_nonfinite_values_are_rejected(self):
        for text in ('{"status":"pass","status":"fail"}', '{"value":NaN}', '{"value":Infinity}',
                     '{"value":-Infinity}', '1e999', '-1e999', '{"nested":[{"value":1E+999}]}'):
            with self.assertRaises(ValueError): review.strict_json(text)

    def test_finite_json_numbers_keep_standard_parsing(self):
        text = '[1.5,-2.5e1,1.7976931348623157e308,1e-999,-0.0,9007199254740993]'
        parsed = review.strict_json(text)
        self.assertEqual(parsed, json.loads(text))
        self.assertEqual(parsed[4].hex(), '-0x0.0p+0')
        self.assertIs(type(parsed[5]), int)

    def test_cli_reports_invalid_review_without_echoing_untrusted_text(self):
        path = self.work / "bad.json"
        path.write_text('{"arbitrary":"UNTRUSTED_SENTINEL"}')
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = review.main(["report", "--run", str(self.run), "--review", str(path), "--output", str(self.work / "no-output")])
        self.assertEqual(code, 2)
        self.assertNotIn("UNTRUSTED_SENTINEL", stderr.getvalue())
        self.assertFalse((self.work / "no-output").exists())


if __name__ == "__main__":
    unittest.main()
