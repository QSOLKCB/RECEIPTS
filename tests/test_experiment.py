"""Frozen-design and paired-report tests; all responses are synthetic. Apache-2.0."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from receipts import action_review, evaluation_v4 as suite, experiment, runner
from receipts.evidence import canonical_hash

ROOT = Path(__file__).resolve().parents[1]


def make_run(directory, slot, *, mode="correct", api_error_at=None, model="stub", tokens=1200, cases=16, seed=None):
    _, gold = suite.load_suite(ROOT)
    baseline = (ROOT / "prompts/baseline.txt").read_text()
    calls = 0
    def reply(payload, key):
        nonlocal calls
        calls += 1
        if calls == api_error_at:
            raise RuntimeError("http_429")
        case_id = json.loads(payload["input"])["case_id"]
        rubric = gold[case_id]
        verdict = rubric["verdict"]
        is_baseline = payload["instructions"] == baseline
        if (mode == "baseline_wrong" and is_baseline) or (mode == "receipts_wrong" and not is_baseline):
            verdict = "contradicted" if verdict != "contradicted" else "supported"
        answer = {"claim_id": "invalid-id" if mode == "invalid" else case_id, "verdict": verdict,
                  "source_ids": rubric["required_sources"], "limitation_codes": rubric["required_limitations"],
                  "rationale": "Synthetic fixture, not a model response.", "next_evidence": "Synthetic public-step fixture; not reviewed."}
        return {"status": "incomplete" if mode == "incomplete" else "completed", "text": json.dumps(answer),
                "response_id": f"synthetic-{slot['repeat']}-{calls}", "returned_model": "stub-returned",
                "usage": None, "response_sha256": "0" * 64}
    with patch.dict("os.environ", {"OPENAI_API_KEY": "synthetic-placeholder"}), patch("receipts.runner.api_call", side_effect=reply), contextlib.redirect_stdout(io.StringIO()):
        return runner.run(ROOT, directory, model, cases, slot["seed"] if seed is None else seed, tokens, False, "v0.4")


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="receipts repeat ")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.notes = self.work / "notes.md"
        self.notes.write_text("Synthetic design fixture. No independent review, real model call or spending authorization. Prior runs exist; cost not priced.")
        self.plan_dir = self.work / "plan"
        self.plan = experiment.prepare(ROOT, self.plan_dir, "stub", 2, 42, 1200, self.notes)
        self.plan_path = self.plan_dir / "plan.json"
        self.digest = canonical_hash(self.plan)
        self.index_path = self.work / "index.json"
        self.index = json.loads((self.plan_dir / "run-index-template.json").read_text())

    def submit(self, repeat, **kwargs):
        directory = self.work / f"run-{repeat}"
        make_run(directory, self.plan["slots"][repeat - 1], **kwargs)
        self.index["rows"][repeat - 1].update(run_directory=directory.name, unavailable_reason=None, notes="Synthetic run fixture.")
        return directory

    def report(self, output="report", digest=None):
        self.index_path.write_text(json.dumps(self.index))
        return experiment.report(self.plan_path, self.index_path, self.work / output, self.digest if digest is None else digest)

    def test_v04_controls_and_rubrics_are_complete_and_excluded_from_requests(self):
        cases, gold = suite.load_suite(ROOT)
        self.assertEqual({v: sum(g["verdict"] == v for g in gold.values()) for v in ("supported", "contradicted", "insufficient")},
                         {"supported": 5, "contradicted": 5, "insufficient": 6})
        for case in cases:
            request = suite.request_payload("stub", "instructions", case, 1200)
            packet = json.loads(request["input"])
            self.assertEqual(set(packet), {"case_id", "kind", "claim", "cutoff_utc", "sources", "limitation_code_definitions", "instruction", "claim_type", "scope", "claim_semantics", "next_evidence_contract"})
            self.assertNotIn("tools", request)
            self.assertFalse(request["store"])
            self.assertEqual(set(gold[case["case_id"]]["action_review"]["criteria"]), set(action_review.DIMENSIONS))
            with self.assertRaises(ValueError):
                suite.model_input({**case, "verdict": gold[case["case_id"]]["verdict"]})

    def test_prepare_freezes_all_cases_and_order_without_inference(self):
        with patch("receipts.runner.api_call") as api:
            plan = experiment.prepare(ROOT, self.work / "second-plan", "stub", 5, 10, 256, self.notes)
            api.assert_not_called()
        self.assertEqual((plan["planned_calls"], plan["maximum_output_tokens"]), (160, 40960))
        self.assertEqual(plan["policy"]["human_review"], "not_performed")
        self.assertFalse(plan["policy"]["held_out"])
        all_ids = {c["case_id"] for c in plan["inputs"]["cases"]}
        for index, slot in enumerate(plan["slots"]):
            self.assertEqual(set(slot["selected_case_ids"]), all_ids)
            self.assertEqual(len(slot["call_order"]), 32)
            self.assertEqual(slot["seed"], 10 + index)
        self.assertEqual((self.plan_dir / "plan-sha256.txt").read_text().strip(), self.digest)
        self.assertFalse((self.plan_dir / "summary.json").exists())

    def test_empty_index_exposes_unknowns_without_imputing_failure_or_success(self):
        result = self.report()
        self.assertEqual(result["status"], "incomplete_coverage")
        paired = result["metrics"]["paired"]
        self.assertEqual(paired["planned_pairs"], 32)
        self.assertEqual(paired["observed_pairs"], 0)
        self.assertIsNone(paired["mean_difference_all_planned_pairs"])
        self.assertIsNone(paired["mean_difference_observed_pairs_only"])
        self.assertEqual(paired["missing_outcome_bounds_all_planned_pairs"], [-1, 1])
        self.assertIsNone(result["metrics"]["repeat_dispersion"]["sample_standard_deviation"])
        for count in result["metrics"]["variants"].values():
            self.assertEqual((count["attempted"], count["unattempted"]), (0, 32))
            self.assertEqual(count["accuracy_bounds_for_planned_calls"], [0, 1])

    def test_complete_repeats_match_frozen_requests_and_show_zero_difference(self):
        requests = json.loads((self.plan_dir / "requests.json").read_text())
        for repeat in (1, 2):
            directory = self.submit(repeat)
            manifest, _, _, records, _ = action_review.load_run(directory)
            self.assertEqual(manifest["engine_sha256"], self.plan["engine_sha256"])
            self.assertEqual([r["request_sha256"] for r in records], [canonical_hash(p) for p in requests[repeat - 1]["requests"]])
            if repeat == 1:
                reviewed = action_review.report(directory, directory / "action-review-template.json", self.work / "action-report")
                self.assertEqual(reviewed["run_coverage"]["attempted_calls"], 32)
                self.assertTrue(all(r["proposals_with_any_dimension_reviewed"] == 0 for r in reviewed["action_assessments"].values()))
        result = self.report()
        self.assertEqual(result["status"], "all_planned_calls_observed")
        paired = result["metrics"]["paired"]
        self.assertEqual(paired["tied_strict_outcomes"], 32)
        self.assertEqual(paired["mean_difference_all_planned_pairs"], 0)
        self.assertEqual(paired["missing_outcome_bounds_all_planned_pairs"], [0, 0])
        self.assertEqual(result["metrics"]["repeat_dispersion"]["sample_standard_deviation"], 0)

    def test_opposite_repeat_effects_stay_visible_in_pairing_and_dispersion(self):
        self.submit(1, mode="baseline_wrong")
        self.submit(2, mode="receipts_wrong")
        metrics = self.report()["metrics"]
        self.assertEqual(metrics["paired"]["receipts_only_correct"], 16)
        self.assertEqual(metrics["paired"]["baseline_only_correct"], 16)
        self.assertEqual(metrics["paired"]["mean_difference_all_planned_pairs"], 0)
        self.assertEqual([r["mean_difference_if_all_pairs_observed"] for r in metrics["repeat_metrics"]], [1, -1])
        self.assertAlmostEqual(metrics["repeat_dispersion"]["sample_standard_deviation"], 2 ** 0.5)

    def test_missing_repeat_keeps_primary_mean_null_and_bounds_visible(self):
        self.submit(1, mode="baseline_wrong")
        result = self.report()
        paired = result["metrics"]["paired"]
        self.assertIsNone(paired["mean_difference_all_planned_pairs"])
        self.assertEqual(paired["mean_difference_observed_pairs_only"], 1)
        self.assertEqual(paired["missing_outcome_bounds_all_planned_pairs"], [0, 1])
        self.assertEqual(result["submitted_terminal_runs"], 1)

    def test_invalid_and_incomplete_outputs_are_observed_non_successes(self):
        self.submit(1, mode="invalid")
        self.submit(2, mode="incomplete")
        result = self.report()
        for count in result["metrics"]["variants"].values():
            self.assertEqual((count["attempted"], count["strict_correct"], count["invalid_outputs"]), (32, 0, 32))
            self.assertEqual(count["accuracy_bounds_for_planned_calls"], [0, 0])
        self.assertEqual(result["metrics"]["paired"]["tied_strict_outcomes"], 32)

    def test_api_stop_preserves_error_unattempted_calls_and_asymmetric_bounds(self):
        directory = self.submit(1, api_error_at=1)
        record = action_review.load_run(directory)[3][0]
        result = self.report()
        counts = result["metrics"]["variants"]
        self.assertEqual(sum(c["api_errors"] for c in counts.values()), 1)
        self.assertEqual(sum(c["unattempted"] for c in counts.values()), 63)
        bounds = result["metrics"]["paired"]["missing_outcome_bounds_all_planned_pairs"]
        self.assertEqual(bounds, [-31 / 32, 1] if record["variant"] == "baseline" else [-1, 31 / 32])

    def test_changed_plan_or_caller_digest_is_rejected_before_output(self):
        with self.assertRaises(ValueError): self.report(digest="0" * 64)
        changed = copy.deepcopy(self.plan)
        changed["model_requested"] = "other"
        experiment.write_json(self.plan_path, changed)
        with self.assertRaises(ValueError): self.report()
        self.assertFalse((self.work / "report").exists())

    def test_rehashed_plan_cannot_change_fixed_aggregation_or_runtime_contract(self):
        for mutate in (lambda p: p["policy"].update(held_out=True), lambda p: p["slots"].pop(),
                       lambda p: p.update(engine_sha256="0" * 64), lambda p: p.update(python_version="0.0")):
            changed = copy.deepcopy(self.plan)
            mutate(changed)
            experiment.write_json(self.plan_path, changed)
            with self.assertRaises(ValueError): self.report(digest=canonical_hash(changed))

    def test_returned_plan_cannot_mutate_global_policy(self):
        original = dict(experiment.POLICY)
        self.plan["policy"]["held_out"] = True
        self.assertEqual(experiment.POLICY, original)

    def test_missing_and_mixed_returned_model_ids_are_disclosed(self):
        directory = self.submit(1)
        path = directory / "results.jsonl"
        records = [json.loads(line) for line in path.read_text().splitlines()]
        records[0]["response"]["returned_model"] = "other-stub"
        records[1]["response"]["returned_model"] = None
        path.write_text(''.join(json.dumps(r) + '\n' for r in records))
        # Model fields do not affect verdict arithmetic, but identity changes stay visible.
        result = self.report()
        self.assertEqual(result["returned_model_ids"], ["other-stub", "stub-returned"])
        self.assertEqual(len(result["comparability_warnings"]), 3)
        self.assertIn('Multiple returned model IDs', (self.work / "report/report.md").read_text())

    def test_changed_model_tokens_seed_or_case_subset_do_not_match_plan(self):
        for i, kwargs in enumerate(({"model": "other"}, {"tokens": 256}, {"seed": 7}, {"cases": 1})):
            directory = self.work / f"changed-{i}"
            make_run(directory, self.plan["slots"][0], **kwargs)
            with self.assertRaises(ValueError): experiment.checked_run(directory, self.plan, self.plan["slots"][0])

    def test_changed_prompts_gold_and_cases_are_detected_against_plan(self):
        directory = self.submit(1)
        original = {p.name: p.read_bytes() for p in directory.iterdir()}
        for name in ("cases.json", "gold.json", "prompts.json"):
            (directory / name).write_text('{}')
            with self.assertRaises((ValueError, KeyError)): self.report()
            (directory / name).write_bytes(original[name])

    def test_run_before_plan_and_changed_execution_runtime_are_rejected(self):
        directory = self.submit(1)
        path = directory / "manifest.json"
        original = json.loads(path.read_text())
        for key, value in (("started_at_utc", "2000-01-01T00:00:00Z"), ("engine_sha256", "0" * 64), ("python_version", "0.0")):
            experiment.write_json(path, {**original, key: value})
            with self.assertRaises(ValueError): self.report()

    def test_dropped_reordered_or_duplicate_index_rows_are_rejected(self):
        original = copy.deepcopy(self.index)
        for rows in (original["rows"][:1], list(reversed(original["rows"])), [original["rows"][0]] * 2):
            self.index["rows"] = rows
            with self.assertRaises(ValueError): self.report()

    def test_duplicate_run_directory_is_rejected(self):
        self.submit(1)
        self.index["rows"][1].update(run_directory="./run-1", unavailable_reason=None)
        with self.assertRaises(ValueError): self.report()

    def test_blocked_and_interrupted_runs_are_explicit_unavailable_slots(self):
        self.index["rows"][0].update(unavailable_reason="blocked", notes="Synthetic missing-credentials event; original artifact retained separately.")
        self.index["rows"][1].update(unavailable_reason="interrupted", notes="Synthetic interruption; retain partial evidence separately.")
        result = self.report()
        self.assertEqual([r["reason"] for r in result["runs"]], ["blocked", "interrupted"])
        self.assertEqual(result["submitted_terminal_runs"], 0)

    def test_reports_preserve_original_bytes_and_refuse_protected_outputs(self):
        directory = self.submit(1)
        originals = {p: p.read_bytes() for root in (directory, self.plan_dir) for p in root.iterdir()}
        result = self.report()
        self.assertEqual(result["plan_sha256"], self.digest)
        self.assertEqual((self.work / "report/plan.json").read_bytes(), self.plan_path.read_bytes())
        self.assertEqual((self.work / "report/run-index.json").read_bytes(), self.index_path.read_bytes())
        for p, raw in originals.items(): self.assertEqual(p.read_bytes(), raw)
        with self.assertRaises(FileExistsError): self.report()
        for output in ("plan/nested", "run-1/nested"):
            with self.assertRaises(ValueError): self.report(output)

    def test_finite_controls_and_fixed_bounds_validate_without_assert_statements(self):
        for repeats, seed, tokens in ((True, 42, 1200), (1, 42, 1200), (6, 42, 1200), (2, 2**64 - 1, 1200), (2, 42, 2049)):
            with self.assertRaises(ValueError):
                experiment.build_plan(self.plan["inputs"], "stub", repeats, seed, tokens, "notes", self.plan["created_at_utc"], self.plan["engine_sha256"])
        with self.assertRaises(ValueError): experiment.timestamp('2026-01-01Z')

    def test_cli_rejection_does_not_echo_untrusted_notes_or_make_output(self):
        self.index_path.write_text('{"bad":"UNTRUSTED_SENTINEL"}')
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            status = experiment.main(["report", "--plan", str(self.plan_path), "--runs", str(self.index_path), "--expected-plan-sha256", self.digest, "--output", str(self.work / "bad")])
        self.assertEqual(status, 2)
        self.assertNotIn("UNTRUSTED_SENTINEL", stderr.getvalue())
        self.assertFalse((self.work / "bad").exists())


if __name__ == "__main__":
    unittest.main()
