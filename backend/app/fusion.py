"""Late fusion of the text arm and the behaviour arm."""
from . import config


def fuse(text_risk: float, behavior_score: float,
         w_text: float | None = None, w_behavior: float | None = None) -> float:
    wt = config.W_TEXT if w_text is None else w_text
    wb = config.W_BEHAVIOR if w_behavior is None else w_behavior
    total = wt + wb
    if total <= 0:
        raise ValueError("fusion weights must sum to a positive number")
    wt, wb = wt / total, wb / total
    return max(0.0, min(1.0, wt * text_risk + wb * behavior_score))


def tier(score: float) -> str:
    if score >= config.TIER_HIGH:
        return "high"
    if score >= config.TIER_MODERATE:
        return "moderate"
    return "low"
