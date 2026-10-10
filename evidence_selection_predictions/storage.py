"""Study-specific plan validation plus shared atomic storage and locking."""

import json
from pathlib import Path

from evidence_selection.parsing import parse
from evidence_selection.provider import normalize
from evidence_selection.runner import messages_for
from evidence_selection.storage import (
    load_attempts as basic_load_attempts, returned_records, run_lock, write_json,
)
from .core import check_plan
from .prompts import request_payload


def read_plan(output):
    plan = json.loads((Path(output) / "plan.json").read_text())
    check_plan(plan)
    return plan


def load_attempts(output, plan):
    attempts = basic_load_attempts(output, plan)
    records = returned_records(attempts)
    jobs = {j["id"]: j for j in plan["jobs"]}
    runtime_path = Path(output) / "runtime.json"
    runtime = json.loads(runtime_path.read_text()) if runtime_path.exists() else {}
    if attempts and (runtime.get("mode") not in ("live", "mock")
                     or runtime.get("plan_hash") != plan["plan_hash"]):
        raise ValueError("Missing or inconsistent run identity")
    for attempt in attempts:
        job = jobs[attempt["job_id"]]
        expected_messages = messages_for(job, records)
        if (expected_messages is None
                or attempt["payload"] != request_payload(plan["config"], expected_messages)
                or attempt.get("source_hash") != runtime.get("source_hash")
                or attempt.get("is_simulated") != (runtime["mode"] == "mock")
                or any(attempt.get(k) != job[k] for k in ("world_id", "kind", "condition"))):
            raise ValueError("Attempt differs from the frozen request or run identity")
        if attempt["status"] in ("complete", "invalid"):
            response = normalize(attempt["raw_response"], plan["config"]["model"])
            parsed = parse(job["kind"], response["text"])
            parsed["format_valid"] = parsed["valid"]
            parsed["valid"] = parsed["valid"] and response["complete"]
            status = "complete" if parsed["valid"] else "invalid"
            if (response != attempt["response"] or parsed != attempt["parsed"]
                    or status != attempt["status"]):
                raise ValueError("Saved parsing or response differs from the raw response")
    return attempts
