"""Atomic checkpoints, a per-run lock, and conservative attempt accounting."""

from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import tempfile

from .core import check_plan, digest


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def run_lock(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / "run.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another process is using this run directory") from None
        try:
            yield output
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def read_plan(output):
    plan = json.loads((Path(output) / "plan.json").read_text())
    check_plan(plan)
    return plan


def load_attempts(output, plan):
    attempts = []
    known = {job["id"] for job in plan["jobs"]}
    for path in sorted((Path(output) / "attempts").glob("*.json")):
        entry = json.loads(path.read_text())
        if (entry.get("attempt") != len(attempts) + 1 or
                entry.get("plan_hash") != plan["plan_hash"] or
                entry.get("job_id") not in known or
                path.name != f"{entry['attempt']:06d}.json" or
                digest(entry.get("payload")) != entry.get("payload_hash") or
                entry.get("status") not in ("started", "error", "complete", "invalid")):
            raise ValueError("Attempt journal integrity check failed: " + path.name)
        attempts.append(entry)
    return attempts


def returned_records(attempts):
    records = {}
    for entry in attempts:
        if entry["status"] in ("complete", "invalid"):
            if entry["job_id"] in records:
                raise ValueError("Multiple returned answers for one job; refusing to select one")
            records[entry["job_id"]] = entry
    return records
