"""PHQ-9, GAD-7 and PSS-10 loading and scoring.

Score bands (cut-points as published with each instrument):
  PHQ-9  0-27 : 0-4 minimal, 5-9 mild, 10-14 moderate, 15-19 moderately severe, 20-27 severe
  GAD-7  0-21 : 0-4 minimal, 5-9 mild, 10-14 moderate, 15-21 severe
  PSS-10 0-40 : 0-13 low, 14-26 moderate, 27-40 high   (items 4, 5, 7, 8 reverse-scored)
These are screening bands, not diagnoses.
"""
import json
from pathlib import Path

_DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "instruments.json").read_text("utf-8"))
INSTRUMENTS = {k: v for k, v in _DATA.items() if not k.startswith("_")}


def _band(name: str, total: int) -> str:
    if name == "phq9":
        for upper, label in [(4, "minimal"), (9, "mild"), (14, "moderate"), (19, "moderately severe")]:
            if total <= upper:
                return label
        return "severe"
    if name == "gad7":
        for upper, label in [(4, "minimal"), (9, "mild"), (14, "moderate")]:
            if total <= upper:
                return label
        return "severe"
    if name == "pss10":
        if total <= 13:
            return "low"
        if total <= 26:
            return "moderate"
        return "high"
    raise KeyError(name)


def score(name: str, answers: list[int]) -> dict:
    inst = INSTRUMENTS[name]
    n_items = len(inst["items"])
    max_val = len(inst["options"]) - 1
    if len(answers) != n_items:
        raise ValueError(f"{name} needs {n_items} answers, got {len(answers)}")
    if any((not isinstance(a, int)) or a < 0 or a > max_val for a in answers):
        raise ValueError(f"each answer must be an integer from 0 to {max_val}")
    reverse = set(inst["reverse_items"])
    total = 0
    for i, a in enumerate(answers, start=1):
        total += (max_val - a) if i in reverse else a
    safety_idx = inst["safety_item_index"]
    item_positive = safety_idx is not None and answers[safety_idx] > 0
    return {"total": total, "band": _band(name, total), "item9_positive": bool(item_positive),
            "max_total": n_items * max_val}
