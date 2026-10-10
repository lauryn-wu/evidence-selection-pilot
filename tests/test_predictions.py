import copy
from collections import Counter, defaultdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from evidence_selection import core as original_core
from evidence_selection.parsing import parse
from evidence_selection.prompts import initial_messages, selection_message as original_selection
from evidence_selection_predictions import provider
from evidence_selection_predictions.__main__ import export_run
from evidence_selection_predictions.analysis import analyze, decision
from evidence_selection_predictions.core import (
    CONDITIONS, DEFAULT_CONFIG, check_plan, generate_worlds, make_plan,
)
from evidence_selection_predictions.legacy_audit import decode_content
from evidence_selection_predictions.prompts import prediction_table, selection_message
from evidence_selection_predictions.runner import messages_for, prepare, run
from evidence_selection_predictions.storage import load_attempts, read_plan, write_json


class PredictionsDesignTests(unittest.TestCase):
    def setUp(self):
        self.config = copy.deepcopy(DEFAULT_CONFIG)
        self.plan = make_plan(self.config)

    def test_only_treatment_change_is_the_exact_prediction_table(self):
        for world in self.plan["worlds"]:
            baseline = selection_message(world, "rules_only")
            treated = selection_message(world, "predictions_supplied")
            table = prediction_table(world)
            self.assertEqual(baseline, original_selection(world, "direct"))
            self.assertEqual(treated.replace("\n\n" + table, "", 1), baseline)
            table_rows = table.splitlines()[2:]
            self.assertEqual(len(table_rows), 3)
            for test, row in zip(world["candidates"], table_rows):
                expected = []
                for label in ("H1", "H2"):
                    free = (test["price"] >= world["price_threshold"]
                            if world["hypotheses"][label] == "price"
                            else test["weight"] < world["weight_threshold"])
                    expected.append(0 if free else world["fee"])
                self.assertEqual(row, f"{test['id']} | ${expected[0]} | ${expected[1]}")
            self.assertNotIn("diagnostic", table.lower())
            self.assertNotIn("choice", table.lower())

    def test_full_counterbalance_and_two_direction_smoke_check(self):
        worlds = self.plan["worlds"]
        self.assertEqual(Counter(w["oracle"]["diagnostic_test"] for w in worlds),
                         {"T1": 8, "T2": 8, "T3": 8})
        self.assertEqual(Counter(w["hypotheses"]["H1"] for w in worlds),
                         {"price": 12, "weight": 12})
        self.assertEqual(Counter(w["diagnostic_direction"] for w in worlds),
                         {"high_heavy": 12, "low_light": 12})
        self.assertEqual({w["diagnostic_direction"] for w in worlds[:2]},
                         {"high_heavy", "low_light"})
        groups = defaultdict(list)
        for w in worlds:
            groups[w["hypotheses"]["H1"], w["diagnostic_direction"],
                   w["oracle"]["diagnostic_test"]].append(tuple(w["condition_order"]))
        self.assertEqual(len(groups), 12)
        for orders in groups.values():
            self.assertEqual(set(orders), {CONDITIONS, tuple(reversed(CONDITIONS))})

    def test_shared_initial_and_no_cross_arm_response_leak(self):
        jobs = self.plan["jobs"][:3]
        self.assertEqual(jobs[0]["messages"], initial_messages(self.plan["worlds"][0]))
        records = {jobs[0]["id"]: {"parsed": {"valid": True},
                                   "response": {"text": "HYPOTHESIS: H2"}}}
        m1, m2 = [messages_for(j, records) for j in jobs[1:]]
        self.assertEqual(m1[:-1], m2[:-1])
        self.assertEqual(m1[-2]["content"], "HYPOTHESIS: H2")
        self.assertEqual(len(m1), 4)
        self.assertEqual(len(m2), 4)

    def test_fresh_cases_frozen_plan_and_budget(self):
        def identity(world):
            return original_core.digest({k: world[k] for k in
                                         ("price_threshold", "weight_threshold", "fee",
                                          "hypotheses", "observations", "candidates")})
        old = {identity(w) for w in original_core.generate_worlds(original_core.DEFAULT_CONFIG)}
        self.assertTrue(old.isdisjoint(identity(w) for w in self.plan["worlds"]))
        self.assertEqual(len(self.plan["jobs"]), 72)
        self.assertEqual(self.plan, make_plan(self.config))
        check_plan(self.plan)
        bad = copy.deepcopy(self.plan)
        bad["worlds"][0]["oracle"]["predictions"]["T1"]["H1"] = 123
        with self.assertRaises(ValueError):
            check_plan(bad)
        with self.assertRaises(ValueError):
            make_plan(dict(self.config, max_total_attempts=71))
        self.assertEqual(len(make_plan(dict(self.config, n_worlds=48,
                                            max_total_attempts=168))["jobs"]), 144)
        self.assertEqual(original_core.make_plan(original_core.DEFAULT_CONFIG)["plan_hash"],
                         "383bd6d3b8d6fb6154544469c07f9f7989745fb348fc58e03bcca347051e1b97")


class PredictionsRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name) / "run"
        self.config = dict(DEFAULT_CONFIG, bootstrap_samples=200)

    def tearDown(self):
        self.temp.cleanup()

    def run_mock(self, **kwargs):
        return run(self.config, self.output, mock=True, progress=lambda _: None, **kwargs)

    def test_resume_export_and_no_network(self):
        with patch.object(provider, "complete", side_effect=AssertionError("No API")):
            first = self.run_mock(max_calls=6)
            self.assertEqual(first["returned_answers"], 6)
            original = (self.output / "attempts/000001.json").read_bytes()
            second = self.run_mock()
            self.assertEqual(second["calls_this_invocation"], 66)
            self.assertEqual(second["returned_answers"], 72)
            self.assertEqual(self.run_mock()["calls_this_invocation"], 0)
            self.assertEqual((self.output / "attempts/000001.json").read_bytes(), original)
            summary = analyze(self.output)
            self.assertEqual(summary["decision"], "simulation_only_no_scientific_conclusion")
            self.assertTrue(all(s["diagnostic_count"] == 24 for s in summary["conditions"].values()))
            target = Path(self.temp.name) / "result.zip"
            export_run(self.output, target)
            with zipfile.ZipFile(target) as z:
                self.assertEqual(z.read("run/attempts/000001.json"), original)
                self.assertIsNone(z.testzip())
            with self.assertRaises(ValueError):
                export_run(self.output, target)
            with self.assertRaises(ValueError):
                export_run(self.output, self.output / "bad.zip")

    def test_source_config_and_mode_isolation(self):
        self.run_mock(max_calls=1)
        with self.assertRaises(ValueError):
            run(self.config, self.output, max_calls=1, mock=False)
        with self.assertRaises(ValueError):
            prepare(dict(self.config, seed=self.config["seed"] + 1), self.output)
        with patch("evidence_selection_predictions.runner.source_hash", return_value="changed"):
            with self.assertRaises(ValueError):
                self.run_mock()

    def test_original_run_directory_rejected(self):
        from evidence_selection.runner import prepare as original_prepare
        original_prepare(original_core.DEFAULT_CONFIG, self.output)
        with self.assertRaises(ValueError):
            self.run_mock()

    def test_invalid_initial_blocks_two_branches_without_replacement(self):
        original = provider.mock_complete
        def invalid(config, job, world):
            response = original(config, job, world)
            if job["id"] == "predictions-000/initial":
                response["choices"][0]["message"]["content"] = "I cannot choose."
            return response
        with patch.object(provider, "mock_complete", side_effect=invalid):
            result = self.run_mock()
        self.assertEqual(result["returned_answers"], 70)
        self.assertEqual(result["invalid_answers_retained"], 1)
        self.assertEqual(len(result["blocked_jobs"]), 2)
        self.assertEqual(self.run_mock()["calls_this_invocation"], 0)
        summary = analyze(self.output)
        self.assertTrue(all(s["missing"] == 1 for s in summary["conditions"].values()))

    def test_invalid_choice_and_extra_text_are_retained_not_retried(self):
        original = provider.mock_complete
        def changed(config, job, world):
            response = original(config, job, world)
            if job["kind"] == "select":
                text = ("CHOICE: T99" if job["condition"] == "rules_only" else
                        "Some extra text.\n" + response["choices"][0]["message"]["content"])
                response["choices"][0]["message"]["content"] = text
            return response
        with patch.object(provider, "mock_complete", side_effect=changed):
            result = self.run_mock()
        self.assertEqual(result["attempts_total"], 72)
        self.assertEqual(result["invalid_answers_retained"], 24)
        self.assertEqual(self.run_mock()["calls_this_invocation"], 0)
        summary = analyze(self.output)
        self.assertEqual(summary["conditions"]["rules_only"]["invalid"], 24)
        self.assertEqual(summary["conditions"]["predictions_supplied"]["has_prefix_count"], 24)
        self.assertEqual(summary["conditions"]["predictions_supplied"]["diagnostic_count"], 24)
        self.assertEqual(summary["comparison"]["n_pairs"], 0)

    def test_interrupted_attempt_is_counted_and_requires_explicit_retry(self):
        with patch.object(provider, "mock_complete", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_mock(max_calls=1)
        self.assertEqual(self.run_mock(max_calls=1)["stopped"], "uncertain_attempt_requires_flag")
        result = self.run_mock(max_calls=1, retry_uncertain=True)
        self.assertEqual(result["attempts_total"], 2)
        self.assertEqual(result["returned_answers"], 1)

    def test_transport_retries_obey_hard_attempt_cap(self):
        self.config["max_total_attempts"] = 72
        original = provider.mock_complete
        seen = set()
        def transient(config, job, world):
            if job["id"] not in seen:
                seen.add(job["id"])
                raise provider.ProviderError("HTTP 429", retryable=True)
            return original(config, job, world)
        with patch.object(provider, "mock_complete", side_effect=transient), \
                patch("evidence_selection_predictions.runner.time.sleep"):
            result = self.run_mock()
        self.assertEqual(result["attempts_total"], 72)
        self.assertEqual(result["returned_answers"], 36)
        self.assertEqual(result["stopped"], "attempt_budget")
        self.assertEqual(self.run_mock()["calls_this_invocation"], 0)

    def test_changed_saved_answer_is_rejected(self):
        self.run_mock(max_calls=3)
        path = self.output / "attempts/000002.json"
        item = json.loads(path.read_text())
        item["parsed"]["choice"] = "T99"
        write_json(path, item)
        with self.assertRaises(ValueError):
            load_attempts(self.output, read_plan(self.output))

    def test_known_paired_scores_and_residual_error_audit(self):
        original = provider.mock_complete
        def behavior(config, job, world):
            response = original(config, job, world)
            if job["kind"] == "select":
                index = int(world["id"].split('-')[-1])
                wrong = (job["condition"] == "rules_only" and index < 10 or
                         job["condition"] == "predictions_supplied" and index < 4)
                if wrong:
                    choice = next(t for t in ("T1", "T2", "T3") if t != world["oracle"]["diagnostic_test"])
                    response["choices"][0]["message"]["content"] = "CHOICE: " + choice
            return response
        with patch.object(provider, "mock_complete", side_effect=behavior):
            self.run_mock()
        summary = analyze(self.output)
        self.assertEqual(summary["conditions"]["rules_only"]["diagnostic_count"], 14)
        self.assertEqual(summary["conditions"]["predictions_supplied"]["diagnostic_count"], 20)
        self.assertEqual(summary["comparison"]["difference_pp"], 25)
        self.assertEqual(summary["comparison"]["gains"], 6)
        self.assertEqual(summary["comparison"]["losses"], 0)
        self.assertEqual(len(summary["supplied_prediction_failures"]), 4)


class PredictionsAnalysisTests(unittest.TestCase):
    def summary(self):
        return {"is_simulated": False, "returned_answers": 72, "planned_calls": 72,
                "invalid_answers": 0, "cases": 24,
                "conditions": {c: {"no_prefix_count": 24,
                                   "diagnostic_count": 24 if c == "predictions_supplied" else 8}
                               for c in CONDITIONS}}

    def test_prospective_stop_and_review_rules(self):
        s = self.summary()
        self.assertEqual(decision(s), "supplied_predictions_near_ceiling_stop_shipping_task")
        s["conditions"]["rules_only"]["diagnostic_count"] = 23
        self.assertEqual(decision(s), "both_conditions_near_ceiling_stop_shipping_task")
        s["conditions"]["predictions_supplied"]["diagnostic_count"] = 20
        self.assertEqual(decision(s), "residual_errors_with_supplied_predictions_audit_before_any_expansion")
        s["conditions"]["predictions_supplied"]["diagnostic_count"] = 22
        self.assertEqual(decision(s), "small_residual_do_not_expand_automatically")
        s["conditions"]["rules_only"]["no_prefix_count"] = 21
        self.assertEqual(decision(s), "measurement_issue_review_answer_only_compliance")
        s["invalid_answers"] = 1
        self.assertEqual(decision(s), "measurement_issue_review_invalid_outputs")
        s["returned_answers"] = 6
        self.assertEqual(decision(s), "incomplete_no_go_decision")
        s["is_simulated"] = True
        self.assertEqual(decision(s), "simulation_only_no_scientific_conclusion")

    def test_content_audit_normalization_is_explicit_and_strict(self):
        raw = '{"T1":{"H1":"0","H2":"5"},"T2":{"H1":"5","H2":"5"},"T3":{"H1":"0","H2":"0"}}'
        wrapped = "```json\n" + raw + "\n```"
        result = decode_content(wrapped)
        self.assertTrue(result["content_parseable"])
        self.assertTrue(result["removed_fence"])
        self.assertEqual(result["numeric_strings_converted"], 6)
        self.assertEqual(result["predictions"]["T1"], {"H1": 0, "H2": 5})
        self.assertFalse(parse("competence", wrapped)["valid"])
        for bad in ["Here is the answer:\n" + wrapped,
                    raw.replace('"H1":"0"', '"H1":true', 1),
                    raw.replace('"H1":"0"', '"H1":NaN', 1),
                    raw.replace('"H1":"0"', '"H1":"$0"', 1),
                    raw.replace('"H1":"0"', '"H1":"0","H1":"5"', 1),
                    raw.replace('"T1":', '"T4":', 1)]:
            self.assertFalse(decode_content(bad)["content_parseable"])


if __name__ == "__main__":
    unittest.main()
