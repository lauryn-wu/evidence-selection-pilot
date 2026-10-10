"""Reuse the original one-attempt transport; simulation is explicitly separate."""

from evidence_selection.provider import ProviderError, complete, credential, normalize


def mock_complete(config, job, world):
    content = ("HYPOTHESIS: H1" if job["kind"] == "initial" else
               "CHOICE: " + world["oracle"]["diagnostic_test"])
    return {"id": "SIMULATED-" + job["id"], "model": config["model"],
            "choices": [{"finish_reason": "stop",
                         "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}
