"""Read-only content audit of the original shipping pilot; no model calls."""

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile

from evidence_selection.analysis import compute as original_compute
from evidence_selection.core import check_plan, digest
from evidence_selection.parsing import parse
from evidence_selection.prompts import request_payload
from evidence_selection.provider import normalize
from evidence_selection.runner import messages_for, source_hash as original_source_hash
from evidence_selection.storage import returned_records, run_lock, write_json

POLICY = (
    "Separate content audit declared after the six-call smoke check. Remove at most "
    "one whole-response Markdown JSON fence; interpret nonnegative plain decimal "
    "strings as numbers; require exactly T1/T2/T3 with H1/H2 in each. Reject extra "
    "prose, duplicate keys, booleans, nonfinite values, and provider-invalid answers. "
    "Never change an original validity flag or replace an answer."
)


def reject_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def decode_content(text):
    stripped = text.strip()
    match = re.fullmatch(r"```(?:json)?\s*\n(.*?)\n```", stripped, re.S)
    fenced = match is not None
    if match:
        stripped = match.group(1)
    try:
        data = json.loads(stripped, object_pairs_hook=reject_duplicates)
        if not isinstance(data, dict) or set(data) != {"T1", "T2", "T3"}:
            raise ValueError("Unexpected test keys")
        strings = 0
        for row in data.values():
            if not isinstance(row, dict) or set(row) != {"H1", "H2"}:
                raise ValueError("Unexpected hypothesis keys")
            for hypothesis, value in row.items():
                if isinstance(value, str):
                    if not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value):
                        raise ValueError("Not a plain nonnegative decimal string")
                    value = float(value)
                    row[hypothesis] = value
                    strings += 1
                if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                    raise ValueError("Invalid numeric fee")
        return {"content_parseable": True, "predictions": data,
                "removed_fence": fenced, "numeric_strings_converted": strings}
    except (ValueError, TypeError, OverflowError):
        return {"content_parseable": False, "predictions": None,
                "removed_fence": fenced, "numeric_strings_converted": None}


def read_input(source):
    source = Path(source).resolve()
    if source.is_dir():
        names = ["plan.json", "runtime.json"] + [
            str(p.relative_to(source)) for p in sorted((source / "attempts").glob("*.json"))]
        files = {name: (source / name).read_bytes() for name in names}
        identity = digest({name: hashlib.sha256(value).hexdigest() for name, value in files.items()})
        identity_kind = "plan_runtime_attempts_manifest_sha256"
    else:
        with zipfile.ZipFile(source) as archive:
            names = archive.namelist()
            if len(set(names)) != len(names):
                raise ValueError("Duplicate archive paths")
            plans = [name for name in names if name.endswith("/plan.json") or name == "plan.json"]
            if len(plans) != 1:
                raise ValueError("Archive must contain exactly one run")
            prefix = plans[0][:-len("plan.json")]
            names = [prefix + "plan.json", prefix + "runtime.json"] + sorted(
                n for n in names if re.fullmatch(re.escape(prefix) + r"attempts/\d{6}\.json", n))
            files = {name[len(prefix):]: archive.read(name) for name in names}
        identity = hashlib.sha256(source.read_bytes()).hexdigest()
        identity_kind = "archive_sha256"
    return files, {"filename": source.name, identity_kind: identity}


def compute_audit(source):
    files, identity = read_input(source)
    plan = json.loads(files["plan.json"])
    runtime = json.loads(files["runtime.json"])
    check_plan(plan)
    if (runtime.get("plan_hash") != plan["plan_hash"]
            or runtime.get("source_hash") != original_source_hash()
            or runtime.get("mode") not in ("mock", "live")):
        raise ValueError("Original source, plan, or runtime identity does not match")
    attempts = [json.loads(value) for name, value in sorted(files.items()) if name.startswith("attempts/")]
    records = returned_records(attempts)
    jobs = {j["id"]: j for j in plan["jobs"]}
    for index, attempt in enumerate(attempts, 1):
        job = jobs.get(attempt.get("job_id"))
        if (job is None or attempt.get("attempt") != index
                or attempt.get("plan_hash") != plan["plan_hash"]
                or attempt.get("source_hash") != runtime["source_hash"]
                or attempt.get("is_simulated") != (runtime["mode"] == "mock")
                or digest(attempt.get("payload")) != attempt.get("payload_hash")
                or attempt["payload"] != request_payload(plan["config"], messages_for(job, records))):
            raise ValueError("Original attempt integrity check failed")
        if attempt["status"] in ("complete", "invalid"):
            response = normalize(attempt["raw_response"], plan["config"]["model"])
            parsed = parse(job["kind"], response["text"])
            parsed["format_valid"] = parsed["valid"]
            parsed["valid"] = parsed["valid"] and response["complete"]
            expected_status = "complete" if parsed["valid"] else "invalid"
            if (response != attempt["response"] or parsed != attempt["parsed"]
                    or attempt["status"] != expected_status):
                raise ValueError("Original raw response or saved parse is inconsistent")
    strict, _ = original_compute(plan, attempts, runtime["mode"] == "mock")
    cases = []
    initial_rules = Counter()
    for world in plan["worlds"]:
        initial = records.get(world["id"] + "/initial")
        if initial and initial["parsed"]["valid"]:
            initial_rules[world["hypotheses"][initial["parsed"]["hypothesis"]]] += 1
        item = records.get(world["id"] + "/competence")
        text = item["response"]["text"] if item else ""
        decoded = decode_content(text)
        valid = bool(item and item["response"]["complete"] and decoded["content_parseable"])
        # Independently recompute the fees, then verify the saved oracle.
        expected = {t["id"]: {
            h: (0 if (t["price"] >= world["price_threshold"] if kind == "price"
                      else t["weight"] < world["weight_threshold"]) else world["fee"])
            for h, kind in world["hypotheses"].items()} for t in world["candidates"]}
        if expected != world["oracle"]["predictions"]:
            raise ValueError("Original oracle mismatch")
        predicted = decoded["predictions"]
        cases.append({"world_id": world["id"], "strict_valid": bool(item and item["parsed"]["valid"]),
                      **decoded, "content_valid": valid, "expected": expected,
                      "all_six_correct": predicted == expected if valid else None,
                      "correct_cells": sum(predicted[t][h] == v for t, row in expected.items()
                                           for h, v in row.items()) if valid else None,
                      "text": text})
    return {
        "audit_policy": POLICY, "input": identity, "plan_hash": plan["plan_hash"],
        "source_hash": runtime["source_hash"], "is_simulated": runtime["mode"] == "mock",
        "returned_answers": len(records), "planned_calls": len(plan["jobs"]),
        "strict_original_decision": strict["decision"],
        "strict_competence": strict["competence"],
        "content_competence": {
            "planned_cases": len(cases), "content_valid_cases": sum(c["content_valid"] for c in cases),
            "all_six_correct": sum(c["all_six_correct"] is True for c in cases),
            "correct_prediction_cells": sum(c["correct_cells"] or 0 for c in cases),
            "planned_prediction_cells": 6 * len(cases),
        },
        "initial_semantic_rules": dict(initial_rules),
        "original_selection_conditions": strict["conditions"],
        "original_paired_comparisons": strict["comparisons"],
        "competence_cases": cases,
        "note": "Supplementary content audit only. Original records, strict flags, and decision are unchanged. "
                "Original comparison fields retain their original strict competence subset.",
    }


def audit_original(source, output):
    source, target = Path(source).resolve(), Path(output).resolve()
    if source.is_dir() and (target == source or source in target.parents):
        raise ValueError("Audit output must be outside the original run directory")
    result = compute_audit(source)
    with run_lock(target) as directory:
        if any(p.name != "run.lock" for p in directory.iterdir()):
            raise ValueError("Audit output is not empty; choose a new directory")
        write_json(directory / "content_audit.json", result)
        c = result["content_competence"]
        marker = "SIMULATED SOFTWARE CHECK; NO SCIENTIFIC CONCLUSION.\n\n" if result["is_simulated"] else ""
        text = ("# Original shipping pilot: separate content audit\n\n" + marker + POLICY + "\n\n"
                + f"Strict original competence: {result['strict_competence']['all_six_correct']}/"
                + f"{c['planned_cases']} fully correct cases under the original parser.\n\n"
                + f"Audited fee content: {c['all_six_correct']}/{c['planned_cases']} fully correct cases; "
                + f"{c['correct_prediction_cells']}/{c['planned_prediction_cells']} correct fee cells.\n\n"
                + "See content_audit.json for every original competence response, both scores, and expected fees.\n"
                + "No source response or original analysis file was overwritten. No API calls were made.\n")
        (directory / "report.md").write_text(text)
    return {"output": str(target), "content_competence": result["content_competence"],
            "strict_original_decision": result["strict_original_decision"], "api_calls": 0}
