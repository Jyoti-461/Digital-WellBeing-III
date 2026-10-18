"""Behaviour arm: category thresholds (Table I) and an optional trained Random Forest."""
from __future__ import annotations

import logging
import os

from . import config

log = logging.getLogger("screen_engine")
_rf = None
_rf_tried = False


def exceeded_categories(hours: dict[str, float]) -> dict[str, float]:
    """Return {category: hours_over_threshold} for categories above their threshold."""
    out = {}
    for cat in config.CATEGORIES:
        over = hours.get(cat, 0.0) - config.THRESHOLDS_HOURS[cat]
        if over > 0:
            out[cat] = round(over, 2)
    return out


def violation_ratio(hours: dict[str, float]) -> float:
    """Share of the six categories that are over their own threshold (0..1)."""
    return len(exceeded_categories(hours)) / len(config.CATEGORIES)


def total_exceeded(hours: dict[str, float]) -> bool:
    return sum(hours.get(c, 0.0) for c in config.CATEGORIES) > config.TOTAL_DAILY_THRESHOLD_HOURS


def _load_rf():
    global _rf, _rf_tried
    if _rf_tried:
        return _rf
    _rf_tried = True
    path = config.SCREEN_MODEL_PATH
    if os.path.isfile(path):
        try:
            import joblib

            _rf = joblib.load(path)  # dict: {"model": clf, "features": [...]}
        except Exception as exc:  # pragma: no cover
            log.warning("could not load Random Forest model: %s", exc)
    return _rf


def reset_model_cache() -> None:
    """Used by tests."""
    global _rf, _rf_tried
    _rf, _rf_tried = None, False


def behavior_score(hours: dict[str, float]) -> tuple[float, str]:
    """Return (score 0..1, source). Uses the trained Random Forest if one is present,
    otherwise the deterministic threshold rule."""
    rf = _load_rf()
    if rf is not None:
        feats = [[hours.get(f, 0.0) for f in rf["features"]]]
        proba = rf["model"].predict_proba(feats)[0]
        classes = list(rf["model"].classes_)
        if 1 in classes:
            return float(proba[classes.index(1)]), "random_forest"
    return violation_ratio(hours), "threshold_rules"
