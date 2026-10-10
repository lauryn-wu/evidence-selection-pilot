"""Fresh paired cases and a frozen two-condition plan."""

from collections import defaultdict
import random

from evidence_selection.core import (
    PROTOCOL as ORIGINAL_PROTOCOL, digest, generate_worlds as original_worlds,
    validate_config as original_validate,
)

PROTOCOL = "evidence-selection-supplied-predictions-v1"
CONDITIONS = ("rules_only", "predictions_supplied")
DEFAULT_CONFIG = {
    "protocol": PROTOCOL,
    "n_worlds": 24,
    "seed": 202610102,
    "model": "gpt-4o-2024-08-06",
    "api_key_env": "OPENAI_API_KEY",
    "temperature": 0.0,
    "max_completion_tokens": 1024,
    "timeout_seconds": 120,
    "max_total_attempts": 84,
    "max_attempts_per_job": 2,
    "bootstrap_samples": 10000,
    "analysis_seed": 271828,
}


def original_config(config):
    # Reuse the original deterministic case generator, not its six-job schedule.
    return dict(config, protocol=ORIGINAL_PROTOCOL,
                max_total_attempts=max(config["max_total_attempts"], 6 * config["n_worlds"]))


def validate_config(config):
    if set(config) != set(DEFAULT_CONFIG) or config.get("protocol") != PROTOCOL:
        raise ValueError("Config must match configs/predictions.json and this protocol")
    # Validate the requested budget before adapting it for the case-only generator.
    for key in ("n_worlds", "max_total_attempts"):
        if type(config[key]) is not int or config[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    original_validate(original_config(config))
    if config["max_total_attempts"] < 3 * config["n_worlds"]:
        raise ValueError("Attempt budget must cover three jobs per case")


def generate_worlds(config):
    validate_config(config)
    worlds = original_worlds(original_config(config))
    rng = random.Random(config["seed"] + 104729)
    groups = defaultdict(list)
    for world in worlds:
        price_h = next(h for h, kind in world["hypotheses"].items() if kind == "price")
        diagnostic = world["oracle"]["diagnostic_test"]
        price_free = world["oracle"]["predictions"][diagnostic][price_h] == 0
        world["diagnostic_direction"] = "high_heavy" if price_free else "low_light"
        key = (world["block"], world["hypotheses"]["H1"], price_free, diagnostic)
        groups[key].append(world)
    # Each stratum has two candidate permutations: each arm is first once.
    for group in groups.values():
        assert len(group) == 2
        rng.shuffle(group)
        for index, world in enumerate(group):
            world["condition_order"] = list(CONDITIONS if index == 0 else reversed(CONDITIONS))
    # Interleave diagnostic directions so the six-call check covers both directions.
    high = [w for w in worlds if w["diagnostic_direction"] == "high_heavy"]
    low = [w for w in worlds if w["diagnostic_direction"] == "low_light"]
    worlds = [w for pair in zip(high, low) for w in pair]
    for index, world in enumerate(worlds):
        world["id"] = f"predictions-{index:03d}"
    return worlds


def make_plan(config):
    from evidence_selection.prompts import initial_messages
    from .prompts import selection_message
    worlds = generate_worlds(config)
    jobs = []
    for world in worlds:
        prefix = initial_messages(world)
        initial_id = world["id"] + "/initial"
        jobs.append({"id": initial_id, "world_id": world["id"], "kind": "initial",
                     "condition": None, "messages": prefix})
        for condition in world["condition_order"]:
            jobs.append({"id": world["id"] + "/select/" + condition,
                         "world_id": world["id"], "kind": "select", "condition": condition,
                         "prefix": prefix, "continuation": selection_message(world, condition),
                         "depends_on": initial_id})
    plan = {"config": config, "worlds": worlds, "jobs": jobs}
    plan["plan_hash"] = digest(plan)
    return plan


def check_plan(plan):
    if digest({k: v for k, v in plan.items() if k != "plan_hash"}) != plan.get("plan_hash"):
        raise ValueError("Plan integrity check failed")
    if make_plan(plan["config"]) != plan:
        raise ValueError("Generator or prompts changed; use a new run directory")
