"""Paired selection scores, compliance, and a prospective planning screen."""

import csv
import json
from pathlib import Path

from evidence_selection.analysis import paired_summary
from .core import CONDITIONS
from .storage import load_attempts, read_plan, returned_records, run_lock, write_json


def decision(summary):
    if summary["is_simulated"]:
        return "simulation_only_no_scientific_conclusion"
    if summary["returned_answers"] != summary["planned_calls"]:
        return "incomplete_no_go_decision"
    if summary["invalid_answers"]:
        return "measurement_issue_review_invalid_outputs"
    n = summary["cases"]
    if any(s["no_prefix_count"] / n < 22 / 24 for s in summary["conditions"].values()):
        return "measurement_issue_review_answer_only_compliance"
    supplied = summary["conditions"]["predictions_supplied"]["diagnostic_count"]
    baseline = summary["conditions"]["rules_only"]["diagnostic_count"]
    if supplied / n >= 23 / 24:
        return ("both_conditions_near_ceiling_stop_shipping_task" if baseline / n >= 23 / 24
                else "supplied_predictions_near_ceiling_stop_shipping_task")
    if supplied / n <= 20 / 24:
        return "residual_errors_with_supplied_predictions_audit_before_any_expansion"
    return "small_residual_do_not_expand_automatically"


def compute(plan, attempts, simulated=None):
    records = returned_records(attempts)
    rows = []
    n = len(plan["worlds"])
    labels = {"H1": 0, "H2": 0}
    rules = {"price": 0, "weight": 0}
    for world in plan["worlds"]:
        initial = records.get(world["id"] + "/initial")
        initial_valid = bool(initial and initial["parsed"]["valid"])
        hypothesis = initial["parsed"].get("hypothesis") if initial_valid else None
        semantic_rule = world["hypotheses"].get(hypothesis)
        if hypothesis:
            labels[hypothesis] += 1
            rules[semantic_rule] += 1
        for condition in CONDITIONS:
            item = records.get(world["id"] + "/select/" + condition)
            parsed = item["parsed"] if item else {}
            valid = bool(item and parsed["valid"])
            choice = parsed.get("choice") if valid else None
            fees = world["oracle"]["predictions"].get(choice, {})
            rows.append({
                "world_id": world["id"], "condition": condition,
                "initial_hypothesis": hypothesis, "initial_rule": semantic_rule,
                "initial_valid": initial_valid, "returned": item is not None,
                "valid": valid, "choice": choice,
                "diagnostic_test": world["oracle"]["diagnostic_test"],
                "diagnostic_direction": world["diagnostic_direction"],
                "information_bits": world["oracle"]["information_bits"].get(choice),
                "chosen_fee_H1": fees.get("H1"), "chosen_fee_H2": fees.get("H2"),
                "has_prefix": parsed.get("has_prefix"),
                "prefix_words": parsed.get("prefix_words"),
                "condition_call_position": world["condition_order"].index(condition) + 1,
                "finish_reason": item["response"]["finish_reason"] if item else None,
                "text": item["response"]["text"] if item else "",
                "is_simulated": simulated,
            })
    stats = {}
    for condition in CONDITIONS:
        selected = [r for r in rows if r["condition"] == condition]
        valid = [r for r in selected if r["valid"]]
        correct = sum(r["information_bits"] == 1 for r in valid)
        stats[condition] = {
            "planned": n, "returned": sum(r["returned"] for r in selected),
            "valid": len(valid), "invalid": sum(r["returned"] and not r["valid"] for r in selected),
            "missing": sum(not r["returned"] for r in selected),
            "diagnostic_count": correct, "diagnostic_rate_all_planned": correct / n,
            "diagnostic_rate_valid_only": correct / len(valid) if valid else None,
            "mean_information_bits_valid_only": correct / len(valid) if valid else None,
            "no_prefix_count": sum(r["has_prefix"] is False for r in selected),
            "has_prefix_count": sum(r["has_prefix"] is True for r in selected),
            "by_diagnostic_direction": {
                direction: {"correct": sum(r["information_bits"] == 1 for r in selected
                                           if r["diagnostic_direction"] == direction),
                            "planned": sum(r["diagnostic_direction"] == direction for r in selected)}
                for direction in ("high_heavy", "low_light")
            },
        }
    by = {(r["world_id"], r["condition"]): r for r in rows}
    pairs = []
    answer_only_pairs = []
    for world in plan["worlds"]:
        control = by[world["id"], "rules_only"]
        treatment = by[world["id"], "predictions_supplied"]
        if control["valid"] and treatment["valid"]:
            pair = (treatment["information_bits"] == 1, control["information_bits"] == 1)
            pairs.append(pair)
            if not control["has_prefix"] and not treatment["has_prefix"]:
                answer_only_pairs.append(pair)
    config = plan["config"]
    comparison = paired_summary(pairs, config["bootstrap_samples"], config["analysis_seed"])
    comparison["answer_only_subset"] = paired_summary(
        answer_only_pairs, config["bootstrap_samples"], config["analysis_seed"])
    usage = {k: sum(a["response"].get("usage", {}).get(k, 0) or 0 for a in records.values())
             for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
    result = {
        "protocol": config["protocol"], "model": config["model"], "plan_hash": plan["plan_hash"],
        "is_simulated": simulated, "cases": n, "task_families": 1,
        "planned_calls": len(plan["jobs"]), "attempts_total": len(attempts),
        "returned_answers": len(records),
        "invalid_answers": sum(not a["parsed"]["valid"] for a in records.values()),
        "unresolved_attempts": sum(a["status"] == "started" for a in attempts),
        "initial_hypotheses": {"labels": labels, "semantic_rules": rules},
        "conditions": stats, "primary_contrast": "predictions_supplied_minus_rules_only",
        "comparison": comparison, "returned_response_token_usage": usage,
        "supplied_prediction_failures": [
            {**r, "rules_only_choice": by[r["world_id"], "rules_only"]["choice"]}
            for r in rows if r["condition"] == "predictions_supplied"
            and r["valid"] and r["information_bits"] == 0
        ],
        "notes": [
            "Twenty-four paired numerical cases from one task family; broad generalization is untested.",
            "The initial response is shared verbatim, but latent beliefs and confidence are not measured.",
            "The table changes visibility, redundancy, and presentation; a benefit does not uniquely identify an internal bottleneck.",
            "A supplied correct table does not prove the model read, trusted, or represented it correctly.",
            "Answer-only output does not establish absence of internal reasoning.",
            "Invalid and missing choices are not observed zero-information actions.",
            "The primary comparison uses valid pairs; all-planned rates and missingness are also reported.",
            "The answer-only subset and direction slices are secondary descriptive checks.",
            "Bootstrap intervals are descriptive; the exact paired p-value is exploratory.",
            "This study does not execute a test, sample a hidden rule, or measure final rule identification.",
            "The decision labels are planning heuristics, not significance, mechanism, or novelty verdicts.",
        ],
    }
    result["decision"] = decision(result)
    return result, rows


def report_text(summary):
    lines = ["# Supplied predictions diagnostic", ""]
    if summary["is_simulated"]:
        lines += ["**SIMULATED SOFTWARE CHECK — NOT MODEL RESULTS.**", ""]
    lines += [f"Model: {summary['model']}",
              f"Returned jobs: {summary['returned_answers']}/{summary['planned_calls']}; "
              f"invalid outputs: {summary['invalid_answers']}.",
              f"Decision: **{summary['decision']}**", "",
              "| Condition | Diagnostic / planned | Valid | Missing | Extra text |",
              "| --- | ---: | ---: | ---: | ---: |"]
    for condition, s in summary["conditions"].items():
        lines.append(f"| {condition} | {s['diagnostic_count']}/{s['planned']} | "
                     f"{s['valid']} | {s['missing']} | {s['has_prefix_count']} |")
    comparison = summary["comparison"]
    diff = comparison["difference_pp"]
    interval = comparison["bootstrap_interval95_pp"]
    lines += ["", "Primary comparison: supplied predictions minus rules only.",
              f"Valid pairs: {comparison['n_pairs']}; difference (percentage points): {diff}; "
              f"gains/losses: {comparison['gains']}/{comparison['losses']}.",
              f"Descriptive 95% paired bootstrap interval: {interval}.",
              comparison.get("interval_note", "No pairs available."), "",
              "Initial hypotheses by rule: " + json.dumps(summary["initial_hypotheses"]["semantic_rules"]),
              "", "Inspect audit.csv and the supplied_prediction_failures entries in analysis.json.",
              "Read the raw requests and answers before interpreting any residual errors.", "",
              "## Interpretation limits", ""]
    lines += ["- " + note for note in summary["notes"]]
    return "\n".join(lines) + "\n"


def analyze(output):
    with run_lock(output) as directory:
        plan = read_plan(directory)
        attempts = load_attempts(directory, plan)
        runtime_path = Path(directory) / "runtime.json"
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
