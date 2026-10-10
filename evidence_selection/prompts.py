"""Shared task objective, four response instructions, and an isolated diagnostic."""

import json

SYSTEM = "Solve the task using only the information supplied. Follow the requested output format."

INSTRUCTIONS = {
    "direct": "Choose the test now. Return only the final choice line, with no explanation.",
    "facts": (
        "First write 60-100 words summarizing the stated rules, observed orders, and "
        "available test inputs. Keep this summary descriptive. Then choose the test."
    ),
    "deliberate": (
        "First write 60-100 words reasoning about the competing hypotheses and "
        "what the available tests would reveal. Your tentative hypothesis may be revised. "
        "Then choose the test."
    ),
    "explain": (
        "First write 60-100 words explaining the reasoning behind your tentative "
        "hypothesis. Acknowledge uncertainty or limitations where appropriate. "
        "Your tentative hypothesis may be revised. Then choose the test."
    ),
}


def task_context(world):
    dollar = "$"
    descriptions = {
        "price": (
            f"Shipping is {dollar}0 if the order price is at least "
            f"{dollar}{world['price_threshold']}; otherwise shipping is "
            f"{dollar}{world['fee']}. Weight has no effect."
        ),
        "weight": (
            f"Shipping is {dollar}0 if the order weight is below "
            f"{world['weight_threshold']} kg; otherwise shipping is "
            f"{dollar}{world['fee']}. Price has no effect."
        ),
    }
    lines = [
        "A shipping calculator uses exactly one of the two rules below.",
        "The rule is fixed and deterministic. These are the only possible rules.",
        "The two rules were equally likely before seeing any observations.",
        "",
    ]
    for label, kind in world["hypotheses"].items():
        lines.append(f"{label}: {descriptions[kind]}")
    lines += ["", "Observed orders:", "Price | Weight (kg) | Shipping fee"]
    for obs in world["observations"]:
        lines.append(f"{dollar}{obs['price']} | {obs['weight']:g} | {dollar}{obs['fee']}")
    return "\n".join(lines)


def candidate_text(world):
    dollar = "$"
    lines = ["Available tests:", "Test | Price | Weight (kg)"]
    for test in world["candidates"]:
        lines.append(f"{test['id']} | {dollar}{test['price']} | {test['weight']:g}")
    return "\n".join(lines)


def initial_messages(world):
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": task_context(world) + (
            "\n\nState a tentative working hypothesis: H1 or H2. "
            "If the evidence does not distinguish them, still choose one tentatively; "
            "this is not a claim of certainty. "
            "Return exactly one line: HYPOTHESIS: H1 or HYPOTHESIS: H2."
        )},
    ]


def selection_message(world, condition):
    return candidate_text(world) + (
        "\n\nYou may run exactly one test and observe its shipping fee. "
        "All tests have the same cost. Your objective is to identify which rule "
        "the calculator actually uses. Choose the test that would be most useful "
        "for distinguishing the two rules, regardless of your tentative hypothesis.\n\n"
    ) + INSTRUCTIONS[condition] + (
        "\nThe last nonempty line must be exactly CHOICE: T1, CHOICE: T2, "
        "or CHOICE: T3. Do not include a choice line earlier."
    )


def competence_messages(world):
    template = {t["id"]: {"H1": "<fee>", "H2": "<fee>"} for t in world["candidates"]}
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": task_context(world) + "\n\n" + candidate_text(world) + (
            "\n\nFor each test, calculate the shipping fee under H1 and under H2 "
            "separately. Return only a JSON object with this structure, replacing "
            "each placeholder with the numeric fee predicted by the corresponding hypothesis:\n"
        ) + json.dumps(template)},
    ]


def request_payload(config, messages):
    return {"model": config["model"], "messages": messages,
            "temperature": config["temperature"],
            "max_completion_tokens": config["max_completion_tokens"]}
