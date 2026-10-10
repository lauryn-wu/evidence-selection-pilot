"""The only treatment difference is a correct table of conditional predictions."""

from evidence_selection.prompts import candidate_text, selection_message as original_selection
from evidence_selection.prompts import request_payload


def prediction_table(world):
    lines = [
        "Predicted shipping fees calculated from the stated rules:",
        "Test | Fee if H1 | Fee if H2",
    ]
    for test in world["candidates"]:
        fees = world["oracle"]["predictions"][test["id"]]
        lines.append(f"{test['id']} | ${fees['H1']} | ${fees['H2']}")
    return "\n".join(lines)


def selection_message(world, condition):
    baseline = original_selection(world, "direct")
    if condition == "rules_only":
        return baseline
    if condition != "predictions_supplied":
        raise ValueError("Unknown condition")
    candidates = candidate_text(world)
    assert baseline.startswith(candidates)
    return candidates + "\n\n" + prediction_table(world) + baseline[len(candidates):]
