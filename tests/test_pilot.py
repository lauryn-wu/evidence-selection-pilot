import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evidence_selection.analysis import analyze, decision, paired_summary
from evidence_selection.core import (
    CONDITIONS, DEFAULT_CONFIG, check_plan, generate_worlds, make_plan, oracle, outcome,
)
from evidence_selection.parsing import parse
from evidence_selection.prompts import competence_messages
from evidence_selection.provider import mock_complete, normalize
from evidence_selection.runner import messages_for, prepare, run
from evidence_selection.storage import load_attempts, read_plan, returned_records, write_json


class DesignTests(unittest.TestCase):
    def setUp(self):
        self.config = copy.deepcopy(DEFAULT_CONFIG)
        self.plan = make_plan(self.config)

    def test_reproducible_and_seed_changes_cases(self):
        self.assertEqual(self.plan, make_plan(self.config))
        self.config["seed"] += 1
        self.assertNotEqual(self.plan["worlds"], generate_worlds(self.config))

    def test_counterbalanced_design(self):
        worlds = self.plan["worlds"]
        self.assertEqual(len(worlds), 24)
        for test in ("T1", "T2", "T3"):
            self.assertEqual(sum(w["oracle"]["diagnostic_test"] == test for w in worlds), 8)
        self.assertEqual(sum(w["hypotheses"]["H1"] == "price" for w in worlds), 12)
        self.assertEqual(len({tuple(w["condition_order"]) for w in worlds}), 24)
        for position in range(4):
            for condition in CONDITIONS:
                self.assertEqual(sum(w["condition_order"][position] == condition
                                     for w in worlds), 6)
        price_free = 0
        for w in worlds:
            diagnostic = next(t for t in w["candidates"]
                              if t["id"] == w["oracle"]["diagnostic_test"])
            price_h = next(h for h, kind in w["hypotheses"].items() if kind == "price")
            price_free += outcome(w, price_h, diagnostic) == 0
        self.assertEqual(price_free, 12)

    def test_observations_ambiguous_and_only_one_test_informative(self):
        for world in self.plan["worlds"]:
            for obs in world["observations"]:
                self.assertEqual(outcome(world, "H1", obs), obs["fee"])
                self.assertEqual(outcome(world, "H2", obs), obs["fee"])
            self.assertEqual(sum(oracle(world)["information_bits"].values()), 1)
            inputs = [(x["price"], x["weight"])
                      for x in world["observations"] + world["candidates"]]
            self.assertEqual(len(inputs), len(set(inputs)))

    def test_oracle_boundaries_and_known_example(self):
        w = {"price_threshold": 50, "weight_threshold": 2, "fee": 5,
             "hypotheses": {"H1": "price", "H2": "weight"}}
        self.assertEqual(outcome(w, "H1", {"price": 50, "weight": 2}), 0)
        self.assertEqual(outcome(w, "H2", {"price": 50, "weight": 2}), 5)
        self.assertEqual(outcome(w, "H2", {"price": 30, "weight": 1.9}), 0)
        w["candidates"] = [
            {"id": "T1", "price": 30, "weight": 4},
            {"id": "T2", "price": 70, "weight": 3},
            {"id": "T3", "price": 90, "weight": 0.5},
        ]
        self.assertEqual(oracle(w)["diagnostic_test"], "T2")
        self.assertEqual(oracle(w)["predictions"]["T2"], {"H1": 0, "H2": 5})

    def test_shared_prefix_and_isolated_competence(self):
        jobs = self.plan["jobs"][:6]
        initial = {"parsed": {"valid": True}, "response": {"text": "HYPOTHESIS: H2"}}
        records = {jobs[0]["id"]: initial}
        messages = [messages_for(j, records) for j in jobs if j["kind"] == "select"]
        self.assertTrue(all(m[:-1] == messages[0][:-1] for m in messages))
        self.assertEqual(messages[0][-2]["content"], "HYPOTHESIS: H2")
        self.assertEqual({m["role"] for m in competence_messages(self.plan["worlds"][0])},
                         {"system", "user"})
        self.assertNotIn("oracle", json.dumps(messages))
        self.assertNotIn("diagnostic_test", json.dumps(messages))

    def test_budget_and_frozen_plan(self):
        self.assertEqual(len(self.plan["jobs"]), 144)
        self.assertEqual(len({j["id"] for j in self.plan["jobs"]}), 144)
        check_plan(self.plan)
        damaged = copy.deepcopy(self.plan)
        damaged["worlds"][0]["fee"] = 99
        with self.assertRaises(ValueError):
            check_plan(damaged)
        self.config["n_worlds"] = 23
        with self.assertRaises(ValueError):
            make_plan(self.config)


class OutputTests(unittest.TestCase):
    def test_choice_parser_rejects_conflicting_or_trailing_answers(self):
        for text in ("CHOICE: T4", "CHOICE: T1\nCHOICE: T2",
                     "CHOICE: T2\nThat is my answer.", '{"choice":"T1"}'):
            self.assertFalse(parse("select", text)["valid"])
        answer = parse("select", "Some reasoning.\nCHOICE: T2")
        self.assertTrue(answer["valid"])
        self.assertEqual(answer["choice"], "T2")
        self.assertTrue(answer["has_prefix"])
        self.assertFalse(answer["word_budget_met"])

    def test_initial_must_be_answer_only(self):
        self.assertTrue(parse("initial", "HYPOTHESIS: H1")["valid"])
        self.assertFalse(parse("initial", "I think H1.\nHYPOTHESIS: H1")["valid"])

    def test_competence_rejects_boolean_and_duplicate_keys(self):
        valid = '{"T1":{"H1":0,"H2":5},"T2":{"H1":5,"H2":5},"T3":{"H1":0,"H2":0}}'
        self.assertTrue(parse("competence", valid)["valid"])
        self.assertFalse(parse("competence", valid.replace('"H1":0', '"H1":true', 1))["valid"])
        self.assertFalse(parse("competence", valid.replace('"H1":0', '"H1":0,"H1":5', 1))["valid"])
        self.assertFalse(parse("competence", valid.replace('"H1":0', '"H1":NaN', 1))["valid"])

    def test_truncation_refusal_and_model_mismatch_rejected(self):
        raw = mock_complete(DEFAULT_CONFIG, {"kind": "initial", "id": "x"}, {})
        self.assertTrue(normalize(raw, DEFAULT_CONFIG["model"])["complete"])
        for changed in ("length", "content_filter"):
            bad = copy.deepcopy(raw)
            bad["choices"][0]["finish_reason"] = changed
            self.assertFalse(normalize(bad, DEFAULT_CONFIG["model"])["complete"])
        bad = copy.deepcopy(raw)
        bad["choices"][0]["message"]["refusal"] = "No"
        self.assertFalse(normalize(bad, DEFAULT_CONFIG["model"])["complete"])
        self.assertFalse(normalize(raw, "different-model")["complete"])


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name) / "run"
        self.config = copy.deepcopy(DEFAULT_CONFIG)
        # Statistical uncertainty code is tested independently; keep I/O tests quick.
        self.config["bootstrap_samples"] = 200

    def tearDown(self):
        self.temp.cleanup()

    def do_run(self, **kwargs):
        return run(self.config, self.output, mock=True, progress=lambda _: None, **kwargs)

    def test_resume_without_duplicate_responses_or_network(self):
        with patch("evidence_selection.provider.complete",
                   side_effect=AssertionError("No API in a mock run")):
            first = self.do_run(max_calls=6)
            self.assertEqual(first["returned_answers"], 6)
            second = self.do_run()
            self.assertEqual(second["calls_this_invocation"], 138)
            self.assertEqual(second["returned_answers"], 144)
            third = self.do_run()
            self.assertEqual(third["calls_this_invocation"], 0)
        result = analyze(self.output)
        self.assertEqual(result["competence"]["all_six_correct"], 24)
        self.assertEqual(result["decision"], "simulation_only_no_scientific_conclusion")
        for values in result["conditions"].values():
            self.assertEqual(values["diagnostic_count"], 24)

    def test_mode_and_config_cannot_change_midrun(self):
        self.do_run(max_calls=1)
        with self.assertRaises(ValueError):
            run(self.config, self.output, max_calls=1, mock=False)
        different = dict(self.config, seed=self.config["seed"] + 1)
        with self.assertRaises(ValueError):
            prepare(different, self.output)

    def test_crash_accounted_and_explicit_uncertain_resume(self):
        with patch("evidence_selection.provider.mock_complete", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.do_run(max_calls=1)
        paused = self.do_run(max_calls=1)
        self.assertEqual(paused["stopped"], "uncertain_attempt_requires_flag")
        self.assertEqual(paused["calls_this_invocation"], 0)
        resumed = self.do_run(max_calls=1, retry_uncertain=True)
        self.assertEqual(resumed["attempts_total"], 2)
        self.assertEqual(resumed["returned_answers"], 1)

    def test_invalid_initial_retained_and_all_four_branches_blocked(self):
        original = mock_complete
        def invalid_initial(config, job, world):
            response = original(config, job, world)
            if job["id"] == "shipping-000/initial":
                response["choices"][0]["message"]["content"] = "I cannot decide."
            return response
        with patch("evidence_selection.provider.mock_complete", side_effect=invalid_initial):
            result = self.do_run()
        self.assertEqual(result["invalid_answers_retained"], 1)
        self.assertEqual(len(result["blocked_jobs"]), 4)
        self.assertEqual(result["returned_answers"], 140)
        self.assertEqual(self.do_run()["calls_this_invocation"], 0)
        summary = analyze(self.output)
        self.assertEqual(summary["conditions"]["direct"]["missing"], 1)

    def test_invalid_selection_is_not_retried(self):
        original = mock_complete
        def invalid_choice(config, job, world):
            response = original(config, job, world)
            if job["kind"] == "select" and job["condition"] == "deliberate":
                response["choices"][0]["message"]["content"] = "CHOICE: T99"
            return response
        with patch("evidence_selection.provider.mock_complete", side_effect=invalid_choice):
            result = self.do_run()
        self.assertEqual(result["attempts_total"], 144)
        self.assertEqual(result["invalid_answers_retained"], 24)
        self.assertEqual(self.do_run()["calls_this_invocation"], 0)
        summary = analyze(self.output)
        self.assertEqual(summary["conditions"]["deliberate"]["invalid"], 24)
        self.assertIsNone(summary["comparisons"]["deliberate_minus_facts"]["difference_pp"])

    def test_request_tampering_and_duplicate_records_rejected(self):
        self.do_run(max_calls=1)
        plan = read_plan(self.output)
        attempts = load_attempts(self.output, plan)
        with self.assertRaises(ValueError):
            returned_records(attempts + attempts)
        path = self.output / "attempts" / "000001.json"
        record = json.loads(path.read_text())
        record["payload"]["temperature"] = 1.0
        write_json(path, record)
        with self.assertRaises(ValueError):
            load_attempts(self.output, plan)

    def test_fixed_source_required_on_resume(self):
        self.do_run(max_calls=1)
        with patch("evidence_selection.runner.source_hash", return_value="changed"):
            with self.assertRaises(ValueError):
                self.do_run()


class AnalysisTests(unittest.TestCase):
    def test_known_paired_result_and_degenerate_case(self):
        result = paired_summary([(0, 1)] * 6 + [(1, 1)] * 18, 1000)
        self.assertEqual(result["difference_pp"], -25)
        self.assertEqual(result["losses"], 6)
        self.assertEqual(result["gains"], 0)
        self.assertEqual(result["mcnemar_exact_p_unadjusted"], 0.03125)
        self.assertIsNotNone(result["bootstrap_interval95_pp"])
        null = paired_summary([(1, 1)] * 24)
        self.assertIsNone(null["bootstrap_interval95_pp"])
        self.assertEqual(null["mcnemar_exact_p_unadjusted"], 1)
        self.assertIsNone(paired_summary([])["difference_pp"])

    def summary(self):
        return {
            "is_simulated": False, "returned_answers": 144, "planned_calls": 144,
            "invalid_answers": 0, "cases": 24,
            "competence": {"all_six_correct": 24},
            "conditions": {
                c: {"diagnostic_count": 24, "no_prefix_count": 24 if c == "direct" else 0,
                    "word_budget_met_count": 0 if c == "direct" else 24}
                for c in CONDITIONS
            },
        }

    def test_prespecified_screen_branches(self):
        summary = self.summary()
        self.assertEqual(decision(summary), "ceiling_stop_current_task")
        summary["conditions"]["deliberate"]["diagnostic_count"] = 18
        self.assertEqual(decision(summary),
                         "candidate_neutral_deliberation_harm_replicate_on_fresh_cases")
        summary = self.summary()
        summary["conditions"]["explain"]["diagnostic_count"] = 18
        self.assertEqual(decision(summary),
                         "justification_specific_signal_deprioritize_broad_reasoning_claim")
        summary["competence"]["all_six_correct"] = 18
        self.assertEqual(decision(summary), "insufficient_rule_prediction_competence")
        summary["is_simulated"] = True
        self.assertEqual(decision(summary), "simulation_only_no_scientific_conclusion")

    def test_incomplete_and_invalid_runs_cannot_pass_screen(self):
        summary = self.summary()
        summary["returned_answers"] = 6
        self.assertEqual(decision(summary), "incomplete_no_go_decision")
        summary = self.summary()
        summary["invalid_answers"] = 1
        self.assertEqual(decision(summary), "measurement_issue_review_invalid_outputs")


if __name__ == "__main__":
    unittest.main()
