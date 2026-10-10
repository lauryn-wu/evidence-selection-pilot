"""Deterministic instances, counterbalancing, exact oracle, and frozen plans."""

from __future__ import annotations

import hashlib
import itertools
import json
import random

PROTOCOL = "evidence-selection-shipping-v1"
CONDITIONS = ("direct", "facts", "deliberate", "explain")
DEFAULT_CONFIG = {
    "protocol": PROTOCOL,
    "n_worlds": 24,
    "seed": 202610101,
    "model": "gpt-4o-2024-08-06",
    "api_key_env": "OPENAI_API_KEY",
    "temperature": 0.0,
    "max_completion_tokens": 1024,
    "timeout_seconds": 120,
    "max_total_attempts": 168,
    "max_attempts_per_job": 2,
    "bootstrap_samples": 10000,
    "analysis_seed": 271828,
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def validate_config(config):
    if set(config) != set(DEFAULT_CONFIG):
        raise ValueError("Config keys must exactly match configs/pilot.json")
    if config["protocol"] != PROTOCOL:
        raise ValueError("Unsupported protocol")
    for key in ("n_worlds", "seed", "max_completion_tokens", "timeout_seconds",
                "max_total_attempts", "max_attempts_per_job", "bootstrap_samples",
                "analysis_seed"):
        if type(config[key]) is not int or config[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    if config["n_worlds"] % 24:
        raise ValueError("n_worlds must be a multiple of 24 for counterbalancing")
    if config["max_total_attempts"] < config["n_worlds"] * 6:
        raise ValueError("Attempt budget must cover the six planned jobs per case")
    if config["max_attempts_per_job"] > 3:
        raise ValueError("At most three transport attempts per job")
    if type(config["temperature"]) not in (int, float) or not 0 <= config["temperature"] <= 2:
        raise ValueError("temperature must be numeric, between 0 and 2")
    for key in ("model", "api_key_env"):
        if not isinstance(config[key], str) or not config[key].strip():
            raise ValueError(f"{key} must be a nonempty string")
    if not config["api_key_env"].isidentifier():
        raise ValueError("api_key_env must name an environment variable")


def outcome(world, hypothesis, order):
    kind = world["hypotheses"][hypothesis]
    free = (order["price"] >= world["price_threshold"] if kind == "price"
            else order["weight"] < world["weight_threshold"])
    return 0 if free else world["fee"]


def oracle(world):
    predictions = {
        test["id"]: {h: outcome(world, h, test) for h in ("H1", "H2")}
        for test in world["candidates"]
    }
    diagnostic = [t for t, p in predictions.items() if p["H1"] != p["H2"]]
    if len(diagnostic) != 1:
        raise ValueError("Each case must have exactly one diagnostic test")
    return {"predictions": predictions, "diagnostic_test": diagnostic[0],
            "information_bits": {
                t: float(p["H1"] != p["H2"]) for t, p in predictions.items()
            }}


def generate_worlds(config):
    """Full crossing: two label orders x two diagnostic directions x six permutations."""
    validate_config(config)
    rng = random.Random(config["seed"])
    worlds = []
    for block in range(config["n_worlds"] // 24):
        factors = list(itertools.product((False, True), (False, True),
                                         itertools.permutations(range(3))))
        rng.shuffle(factors)
        arm_orders = list(itertools.permutations(CONDITIONS))
        rng.shuffle(arm_orders)
        for local, (swap, low_light, permutation) in enumerate(factors):
            index = len(worlds)
            threshold = rng.randrange(40, 101, 5)
            weight_threshold = rng.choice((2, 3, 4, 5))
            fee = rng.choice((4, 5, 6, 8, 10))

            def order(high, light):
                return {
                    "price": threshold + rng.randint(1, 25) * (1 if high else -1),
                    "weight": round(weight_threshold +
                                    rng.choice((0.3, 0.5, 0.7, 0.9)) *
                                    (-1 if light else 1), 1),
                }

            observations = [dict(order(False, False), fee=fee),
                            dict(order(True, True), fee=0)]
            rng.shuffle(observations)
            used = {(o["price"], o["weight"]) for o in observations}
            candidates = []
            for high, light in ((False, False), (True, True),
                                (not low_light, low_light)):
                while True:
                    item = order(high, light)
                    pair = (item["price"], item["weight"])
                    if pair not in used:
                        used.add(pair)
                        candidates.append(item)
                        break
            hypotheses = ({"H1": "weight", "H2": "price"} if swap
                          else {"H1": "price", "H2": "weight"})
            world = {
                "id": f"shipping-{index:03d}",
                "block": block,
                "price_threshold": threshold,
                "weight_threshold": weight_threshold,
                "fee": fee,
                "hypotheses": hypotheses,
                "observations": observations,
                "candidates": [
                    dict(candidates[j], id=f"T{i + 1}")
                    for i, j in enumerate(permutation)
                ],
                "condition_order": list(arm_orders[local]),
            }
            for obs in observations:
                assert all(outcome(world, h, obs) == obs["fee"] for h in hypotheses)
            world["oracle"] = oracle(world)
            worlds.append(world)
    return worlds


def make_plan(config):
    from .prompts import competence_messages, initial_messages, selection_message
    worlds = generate_worlds(config)
    jobs = []
    for world in worlds:
        prefix = initial_messages(world)
        jobs.append({"id": world["id"] + "/initial", "world_id": world["id"],
                     "kind": "initial", "condition": None, "messages": prefix})
        for condition in world["condition_order"]:
            jobs.append({
                "id": world["id"] + "/select/" + condition,
                "world_id": world["id"], "kind": "select", "condition": condition,
                "prefix": prefix, "continuation": selection_message(world, condition),
                "depends_on": world["id"] + "/initial",
            })
        jobs.append({"id": world["id"] + "/competence", "world_id": world["id"],
                     "kind": "competence", "condition": None,
                     "messages": competence_messages(world)})
    plan = {"config": config, "worlds": worlds, "jobs": jobs}
    plan["plan_hash"] = digest(plan)
    return plan


def check_plan(plan):
    body = {k: v for k, v in plan.items() if k != "plan_hash"}
    if digest(body) != plan.get("plan_hash"):
        raise ValueError("Plan integrity check failed")
    if make_plan(plan["config"]) != plan:
        raise ValueError("Current generator/prompts differ from this frozen plan; use a new run directory")
