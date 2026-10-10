"""Strict answer extraction; invalid answers are retained, never repaired by retry."""

import json
import re


def parse(kind, text):
    stripped = text.strip()
    if kind == "initial":
        match = re.fullmatch(r"HYPOTHESIS: (H[12])", stripped)
        return {"valid": bool(match), "hypothesis": match.group(1) if match else None}
    if kind == "select":
        lines = [line.strip() for line in stripped.splitlines() if line.strip()]
        match = re.fullmatch(r"CHOICE: (T[123])", lines[-1]) if lines else None
        earlier = "\n".join(lines[:-1])
        valid = bool(match) and not re.search(r"\bCHOICE\s*:", earlier, re.I)
        return {"valid": valid, "choice": match.group(1) if valid else None,
                "prefix_words": len(earlier.split()), "has_prefix": bool(earlier),
                "word_budget_met": 60 <= len(earlier.split()) <= 100}
    if kind == "competence":
        try:
            def reject_duplicates(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("Duplicate key")
                    result[key] = value
                return result
            data = json.loads(stripped, object_pairs_hook=reject_duplicates)
            valid = isinstance(data, dict) and set(data) == {"T1", "T2", "T3"}
            valid = valid and all(
                isinstance(row, dict) and set(row) == {"H1", "H2"} and
                all(type(x) in (int, float) and x >= 0 and x < float("inf")
                    for x in row.values()) for row in data.values()
            )
            return {"valid": bool(valid), "predictions": data if valid else None}
        except (ValueError, TypeError):
            return {"valid": False, "predictions": None}
    raise ValueError(f"Unknown job kind: {kind}")
