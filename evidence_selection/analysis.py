"""Paired descriptive analysis with explicit missingness and manipulation checks."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import random
import statistics

from .core import CONDITIONS
from .storage import load_attempts, read_plan, returned_records, run_lock, write_json

CONTRASTS = (
    ("deliberate", "facts"),
    ("deliberate", "direct"),
    ("explain", "facts"),
    ("explain", "deliberate"),
)


def paired_summary(pairs, bootstrap_samples=10000, seed=271828):
    """Each pair is (treatment success, control success), at the case level."""
    if not pairs:
        return {"n_pairs": 0, "difference_pp": None, "bootstrap_interval95_pp": None,
                "gains": 0, "losses": 0, "mcnemar_exact_p_unadjusted": None}
    differences = [int(a) - int(b) for a, b in pairs]
    n = len(differences)
    gains = differences.count(1)
    losses = differences.count(-1)
    discordant = gains + losses
    p = (min(1.0, 2 * sum(math.comb(discordant, j)
                         for j in range(min(gains, losses) + 1)) / 2 ** discordant)
         if discordant else 1.0)
    interval = None
    if len(set(differences)) > 1:
        rng = random.Random(seed)
        draws = sorted(sum(rng.choices(differences, k=n)) / n * 100
                       for _ in range(bootstrap_samples))
        interval = [draws[int(0.025 * (bootstrap_samples - 1))],
                    draws[int(0.975 * (bootstrap_samples - 1))]]
    return {
        "n_pairs": n, "difference_pp": 100 * statistics.mean(differences),
        "bootstrap_interval95_pp": interval,
        "interval_note": (
            "Descriptive case bootstrap; repeated cases share one task template."
            if interval is not None else
            "Not estimated: constant paired differences give a degenerate bootstrap. "
            "This is not evidence of equivalence or a zero-width population interval."
        ),
        "gains": gains, "losses": losses,
        "mcnemar_exact_p_unadjusted": p,
    }


def decision(summary):
    if summary["is_simulated"]:
        return "simulation_only_no_scientific_conclusion"
    if summary["returned_answers"] != summary["planned_calls"]:
        return "incomplete_no_go_decision"
    if summary["invalid_answers"]:
        return "measurement_issue_review_invalid_outputs"
    n = summary["cases"]
    stats = summary["conditions"]
    if (stats["direct"]["no_prefix_count"] / n < 22 / 24 or
            any(stats[c]["word_budget_met_count"] / n < 20 / 24
                for c in CONDITIONS if c != "direct")):
        return "measurement_issue_review_response_instructions"
    if summary["competence"]["all_six_correct"] / n < 22 / 24:
        return "insufficient_rule_prediction_competence"
    if all(stats[c]["diagnostic_count"] / n >= 23 / 24 for c in CONDITIONS):
        return "ceiling_stop_current_task"
    if any(stats[c]["diagnostic_count"] / n < 22 / 24 for c in ("direct", "facts")):
        return "weak_controls_inspect_before_expansion"
    neutral = stats["deliberate"]["diagnostic_count"]
    if all(stats[c]["diagnostic_count"] - neutral >= n / 6 for c in ("direct", "facts")):
        return "candidate_neutral_deliberation_harm_replicate_on_fresh_cases"
    if stats["facts"]["diagnostic_count"] - stats["explain"]["diagnostic_count"] >= n / 6:
        return "justification_specific_signal_deprioritize_broad_reasoning_claim"
    return "no_prespecified_large_harm_signal_do_not_expand_yet"


def compute(plan, attempts, simulated=None):
    records = returned_records(attempts)
    n = len(plan["worlds"])
    rows = []
    successes = {c: {} for c in CONDITIONS}
    competence_cases = set()
    initial_counts = {"H1": 0, "H2": 0}
    competence_valid = 0
    correct_cells = 0
    for world in plan["worlds"]:
        initial = records.get(world["id"] + "/initial")
        initial_valid = bool(initial and initial["parsed"]["valid"])
        hypothesis = initial["parsed"].get("hypothesis") if initial_valid else None
        if hypothesis:
            initial_counts[hypothesis] += 1
        check = records.get(world["id"] + "/competence")
        check_valid = bool(check and check["parsed"]["valid"])
        competent = False
        if check_valid:
            competence_valid += 1
            predictions = check["parsed"]["predictions"]
            correct_cells += sum(
                predictions[t][h] == fee
                for t, pair in world["oracle"]["predictions"].items()
                for h, fee in pair.items()
            )
            competent = predictions == world["oracle"]["predictions"]
            if competent:
                competence_cases.add(world["id"])
        for condition in CONDITIONS:
            item = records.get(world["id"] + "/select/" + condition)
            parsed = item["parsed"] if item else {}
            valid = bool(item and parsed["valid"])
            chosen = parsed.get("choice") if valid else None
            information = world["oracle"]["information_bits"].get(chosen)
            if valid:
                successes[condition][world["id"]] = int(information == 1)
            rows.append({
                "world_id": world["id"], "condition": condition,
                "initial_hypothesis": hypothesis,
                "initial_valid": initial_valid, "returned": item is not None,
                "valid": valid, "choice": chosen,
                "diagnostic_test": world["oracle"]["diagnostic_test"],
                "information_bits": information,
                "prefix_words": parsed.get("prefix_words"),
                "has_prefix": parsed.get("has_prefix"),
                "word_budget_met": parsed.get("word_budget_met"),
                "competence_valid": check_valid,
                "all_six_predictions_correct": competent if check_valid else None,
                "finish_reason": item["response"]["finish_reason"] if item else None,
                "text": item["response"]["text"] if item else "",
                "is_simulated": simulated,
            })
    conditions = {}
    for condition in CONDITIONS:
        selected = [r for r in rows if r["condition"] == condition]
        valid = [r for r in selected if r["valid"]]
        count = sum(r["information_bits"] == 1 for r in valid)
        lengths = [r["prefix_words"] for r in selected if r["returned"]
                   and r["prefix_words"] is not None]
        conditions[condition] = {
            "planned": n, "returned": sum(r["returned"] for r in selected),
            "valid": len(valid), "invalid": sum(r["returned"] and not r["valid"] for r in selected),
            "missing": sum(not r["returned"] for r in selected),
            "diagnostic_count": count,
            "diagnostic_rate_all_planned": count / n,
            "diagnostic_rate_valid_only": count / len(valid) if valid else None,
            "mean_information_bits_valid_only": count / len(valid) if valid else None,
            "has_prefix_count": sum(r["has_prefix"] is True for r in selected),
            "no_prefix_count": sum(r["has_prefix"] is False for r in selected),
            "word_budget_met_count": sum(r["word_budget_met"] is True for r in selected),
            "median_prefix_words": statistics.median(lengths) if lengths else None,
        }
    comparisons = {}
    for treatment, control in CONTRASTS:
        common = sorted(set(successes[treatment]) & set(successes[control]))
        pairs = [(successes[treatment][w], successes[control][w]) for w in common]
        result = paired_summary(pairs, plan["config"]["bootstrap_samples"],
                                plan["config"]["analysis_seed"])
        capable = [w for w in common if w in competence_cases]
        result["competence_correct_subset"] = {
            "n_pairs": len(capable),
            "difference_pp": (100 * statistics.mean(
                successes[treatment][w] - successes[control][w] for w in capable)
                if capable else None),
            "note": "Secondary descriptive subset; competence is measured in a separate call.",
        }
        comparisons[treatment + "_minus_" + control] = result
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for item in records.values():
        provider_usage = item["response"].get("usage")
        if isinstance(provider_usage, dict):
            for key in usage:
                value = provider_usage.get(key)
                if type(value) is int and value >= 0:
                    usage[key] += value
    result = {
        "protocol": plan["config"]["protocol"], "model": plan["config"]["model"],
        "plan_hash": plan["plan_hash"], "is_simulated": simulated,
        "cases": n, "task_families": 1, "planned_calls": len(plan["jobs"]),
        "attempts_total": len(attempts), "returned_answers": len(records),
        "invalid_answers": sum(not a["parsed"]["valid"] for a in records.values()),
        "unresolved_attempts": sum(a["status"] == "started" for a in attempts),
        "initial_hypotheses": initial_counts, "conditions": conditions,
        "competence": {"valid_cases": competence_valid,
                       "all_six_correct": len(competence_cases),
                       "correct_prediction_cells": correct_cells,
                       "planned_prediction_cells": n * 6},
        "primary_contrast": "deliberate_minus_facts",
        "comparisons": comparisons, "returned_response_token_usage": usage,
        "notes": [
            "The experimental unit is a paired generated case, not a response or prediction cell.",
            "All cases are numerical and order variants of one task; generalization is untested.",
            "Intervals are descriptive and p-values exploratory, unadjusted across contrasts.",
            "Equal observable prefixes do not establish equal latent beliefs or confidence.",
            "The intervention combines instructions with generated text; internal mechanism is untested.",
            "A competence call shows separate-task performance, not knowledge in a selection trace.",
            "This stage does not execute chosen tests or measure subsequent correction.",
            "Prefix length is an automatic format check, not a semantic audit of reasoning.",
            "Missing and invalid choices are failures to yield a diagnostic selection, not observed 0-bit actions.",
        ],
    }
    result["decision"] = decision(result)
    return result, rows


def report_text(summary):
    lines = ["# Evidence selection pilot", ""]
    if summary["is_simulated"]:
        lines += ["**SIMULATED SOFTWARE CHECK — NOT MODEL RESULTS.**", ""]
    lines += [
        f"Model: {summary['model']}",
        f"Returned jobs: {summary['returned_answers']}/{summary['planned_calls']}; "
        f"invalid outputs: {summary['invalid_answers']}.",
        f"Decision: **{summary['decision']}**", "",
        "| Condition | Diagnostic / planned | Valid | Missing | Text before choice | Median words |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for condition, values in summary["conditions"].items():
        lines.append(
            f"| {condition} | {values['diagnostic_count']}/{values['planned']} | "
            f"{values['valid']} | {values['missing']} | {values['has_prefix_count']} | "
            f"{values['median_prefix_words']} |"
        )
    lines += [
        "", "## Paired comparisons", "",
        "Negative differences mean fewer diagnostic choices in the first condition.",
        "The primary comparison is deliberate minus facts; the others are secondary.",
        "",
        "| Comparison | Pairs | Difference (pp) | Descriptive bootstrap interval | Gains / losses |",
        "| --- | ---: | ---: | --- | ---: |",
    ]
    for name, values in summary["comparisons"].items():
        difference = values["difference_pp"]
        displayed = "not available" if difference is None else f"{difference:.1f}"
        interval = values["bootstrap_interval95_pp"]
        ci = ("not estimated" if interval is None
              else f"[{interval[0]:.1f}, {interval[1]:.1f}]")
        lines.append(f"| {name} | {values['n_pairs']} | {displayed} | {ci} | "
                     f"{values['gains']} / {values['losses']} |")
    lines += [
        "", "Constant paired differences do not receive a zero-width interval. "
        "A null pilot does not establish equivalence.",
        "",
        f"Separate competence check: {summary['competence']['all_six_correct']}/"
        f"{summary['cases']} cases with all six predicted fees correct.",
        "", "## Interpretation limits", "",
    ]
    lines += ["- " + note for note in summary["notes"]]
    lines += [
        "", "Inspect audit.csv and attempts/*.json before interpreting the screen.",
        "The decision rule is a planning heuristic for a small pilot, not a publication or novelty verdict.",
        "The complete numerical output and exploratory exact paired p-values are in analysis.json.",
        "",
    ]
    return "\n".join(lines)


def analyze(output):
    with run_lock(output) as directory:
        plan = read_plan(directory)
        attempts = load_attempts(directory, plan)
        runtime_path = directory / "runtime.json"
        runtime = json.loads(runtime_path.read_text()) if runtime_path.exists() else {}
        simulated = runtime.get("mode") == "mock" if runtime else None
        summary, rows = compute(plan, attempts, simulated)
        write_json(directory / "analysis.json", summary)
        (directory / "report.md").write_text(report_text(summary))
        with (directory / "audit.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return summary
