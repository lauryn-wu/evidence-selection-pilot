"""Prepare, resume, and bound a run without retrying unfavorable model answers."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import time

from .core import make_plan, digest
from .parsing import parse
from .prompts import request_payload
from . import provider
from .storage import load_attempts, read_plan, returned_records, run_lock, write_json


def now():
    return datetime.now(timezone.utc).isoformat()


def source_hash():
    return digest({
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(Path(__file__).parent.glob("*.py"))
    })


def prepare(config, output):
    plan = make_plan(config)
    with run_lock(output) as directory:
        if (directory / "plan.json").exists():
            if read_plan(directory) != plan:
                raise ValueError("Existing run has a different config or plan; choose a new directory")
        else:
            if (directory / "attempts").exists() or (directory / "runtime.json").exists():
                raise ValueError("Run contains records but no plan; refusing to overwrite")
            write_json(directory / "plan.json", plan)
            write_json(directory / "config.json", config)
            # Preview all frozen inputs without supplying any model answers.
            preview = [
                "# Frozen prompt preview",
                "",
                "Selection jobs insert the exact saved initial assistant response between",
                "their prefix and continuation. No oracle outcomes enter those requests.",
                "",
            ]
            for job in plan["jobs"]:
                preview += ["## " + job["id"], ""]
                for message in job.get("messages", job.get("prefix", [])):
                    preview += ["### " + message["role"], message["content"], ""]
                if job["kind"] == "select":
                    preview += ["### assistant", "[Saved initial response]", "",
                                "### user", job["continuation"], ""]
            (directory / "prompts.md").write_text("\n".join(preview))
    return {"protocol": config["protocol"], "model": config["model"],
            "cases": len(plan["worlds"]), "planned_calls": len(plan["jobs"]),
            "max_total_attempts": config["max_total_attempts"],
            "plan_hash": plan["plan_hash"], "api_calls": 0}


def messages_for(job, records):
    if job["kind"] != "select":
        return job["messages"]
    initial = records.get(job["depends_on"])
    if not initial or not initial["parsed"]["valid"]:
        return None
    return job["prefix"] + [
        {"role": "assistant", "content": initial["response"]["text"]},
        {"role": "user", "content": job["continuation"]},
    ]


def run(config, output, max_calls=None, mock=False, retry_uncertain=False,
        progress=print):
    if max_calls is not None and (type(max_calls) is not int or max_calls < 0):
        raise ValueError("max_calls must be a nonnegative integer")
    prepare(config, output)
    with run_lock(output) as directory:
        plan = read_plan(directory)
        runtime_path = directory / "runtime.json"
        runtime = {"mode": "mock" if mock else "live", "plan_hash": plan["plan_hash"],
                   "source_hash": source_hash()}
        if runtime_path.exists():
            saved = json.loads(runtime_path.read_text())
            if any(saved.get(k) != v for k, v in runtime.items()):
                raise ValueError("Run mode, plan, or source code changed; choose a new run directory")
        else:
            write_json(runtime_path, dict(runtime, created_at=now(),
                                          python_version=platform.python_version()))
        attempts = load_attempts(directory, plan)
        records = returned_records(attempts)
        worlds = {w["id"]: w for w in plan["worlds"]}
        calls = 0
        stop = "plan_exhausted"
        credential_checked = False
        for job in plan["jobs"]:
            if job["id"] in records:
                continue
            messages = messages_for(job, records)
            if messages is None:
                continue
            while job["id"] not in records:
                history = [a for a in attempts if a["job_id"] == job["id"]]
                if len(history) >= config["max_attempts_per_job"]:
                    break
                if max_calls is not None and calls >= max_calls:
                    stop = "call_limit"
                    break
                if len(attempts) >= config["max_total_attempts"]:
                    stop = "attempt_budget"
                    break
                if history and (history[-1]["status"] == "started"
                                or history[-1].get("uncertain")) and not retry_uncertain:
                    stop = "uncertain_attempt_requires_flag"
                    break
                if not mock and not credential_checked:
                    provider.credential(config)
                    credential_checked = True
                payload = request_payload(config, messages)
                attempt = {
                    "attempt": len(attempts) + 1, "job_id": job["id"],
                    "world_id": job["world_id"], "kind": job["kind"],
                    "condition": job["condition"], "plan_hash": plan["plan_hash"],
                    "source_hash": runtime["source_hash"], "is_simulated": mock,
                    "status": "started", "started_at": now(),
                    "payload": payload, "payload_hash": digest(payload),
                }
                path = directory / "attempts" / f"{attempt['attempt']:06d}.json"
                write_json(path, attempt)
                attempts.append(attempt)
                calls += 1
                try:
                    raw = (provider.mock_complete(config, job, worlds[job["world_id"]])
                           if mock else provider.complete(config, payload))
                except provider.ProviderError as exc:
                    attempt.update(status="error", finished_at=now(), error=str(exc),
                                   retryable=exc.retryable, uncertain=exc.uncertain)
                    write_json(path, attempt)
                    progress(job["id"] + ": transport error (" + str(exc) + ")")
                    if not exc.retryable:
                        stop = "uncertain_attempt_requires_flag" if exc.uncertain else "provider_error"
                        break
                    if len(history) + 1 < config["max_attempts_per_job"]:
                        time.sleep(min(2 ** (len(history) + 1), 8))
                    continue
                response = provider.normalize(raw, config["model"])
                parsed = parse(job["kind"], response["text"])
                parsed["format_valid"] = parsed["valid"]
                parsed["valid"] = parsed["valid"] and response["complete"]
                attempt.update(
                    status="complete" if parsed["valid"] else "invalid",
                    finished_at=now(), raw_response=raw, response=response, parsed=parsed,
                )
                write_json(path, attempt)
                records[job["id"]] = attempt
                progress(job["id"] + ": " + attempt["status"])
                if response["returned_model"] != config["model"]:
                    stop = "model_mismatch"
                    break
            if stop != "plan_exhausted":
                break
        blocked = [
            j["id"] for j in plan["jobs"] if j["kind"] == "select"
            and j["depends_on"] in records
            and not records[j["depends_on"]]["parsed"]["valid"]
        ]
        summary = {
            "stopped": stop, "calls_this_invocation": calls,
            "attempts_total": len(attempts), "api_calls": 0 if mock else len(attempts),
            "returned_answers": len(records),
            "valid_answers": sum(a["parsed"]["valid"] for a in records.values()),
            "invalid_answers_retained": sum(not a["parsed"]["valid"] for a in records.values()),
            "blocked_jobs": blocked, "planned_calls": len(plan["jobs"]),
            "max_total_attempts": config["max_total_attempts"],
            "is_simulated": mock,
            "collection_status": "complete" if len(records) == len(plan["jobs"]) else "incomplete",
        }
        write_json(directory / "status.json", summary)
        return summary
