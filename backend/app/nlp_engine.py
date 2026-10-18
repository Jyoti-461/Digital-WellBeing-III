"""Text arm: VADER sentiment + optional fine-tuned transformer.

Honest scope notes
------------------
* VADER gives a sentiment polarity (compound, -1..+1). Turning that into a "risk" number
  with (1 - compound) / 2 is a PLACEHOLDER PROXY, not a validated depression/anxiety
  measure. It exists so the pipeline runs end-to-end before any model is trained.
* The transformer stage only runs if TRANSFORMER_MODEL_DIR points at a directory holding a
  *fine-tuned sequence-classification* model (see scripts/finetune_text_model.py).
  A raw pretrained MentalBERT checkpoint is a masked language model, not a classifier,
  so it cannot be used directly for risk scoring.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from . import config

log = logging.getLogger("nlp_engine")
_vader = SentimentIntensityAnalyzer()

_transformer = None          # (tokenizer, model, torch) once loaded
_transformer_tried = False
transformer_error: Optional[str] = None


def _load_transformer():
    global _transformer, _transformer_tried, transformer_error
    if _transformer_tried:
        return _transformer
    _transformer_tried = True
    path = config.TRANSFORMER_MODEL_DIR
    if not path:
        return None
    if not os.path.isdir(path):
        transformer_error = f"TRANSFORMER_MODEL_DIR '{path}' is not a directory"
        log.warning(transformer_error)
        return None
    try:
        import torch  # noqa: WPS433 (optional dependency)
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tok = AutoTokenizer.from_pretrained(path)
        model = AutoModelForSequenceClassification.from_pretrained(path)
        model.eval()
        _transformer = (tok, model, torch)
    except Exception as exc:  # pragma: no cover - depends on optional install
        transformer_error = f"could not load transformer: {exc}"
        log.warning(transformer_error)
    return _transformer


def vader_compound(text: str) -> float:
    return float(_vader.polarity_scores(text)["compound"])


def vader_risk_proxy(compound: float) -> float:
    """PLACEHOLDER mapping: strongly negative -> 1.0, neutral -> 0.5, strongly positive -> 0.0."""
    return max(0.0, min(1.0, (1.0 - compound) / 2.0))


def transformer_risk(text: str) -> Optional[float]:
    loaded = _load_transformer()
    if loaded is None:
        return None
    tok, model, torch = loaded
    inputs = tok(text, return_tensors="pt", truncation=True, max_length=256)
    with torch.no_grad():
        logits = model(**inputs).logits
    probs = torch.softmax(logits, dim=-1)[0]
    idx = config.TRANSFORMER_RISK_LABEL_INDEX
    if idx >= probs.shape[0]:
        raise ValueError("TRANSFORMER_RISK_LABEL_INDEX is out of range for this model")
    return float(probs[idx])


def score_text(text: str) -> dict:
    compound = vader_compound(text)
    t_risk = None
    try:
        t_risk = transformer_risk(text)
    except Exception as exc:  # pragma: no cover
        log.warning("transformer scoring failed, using VADER proxy: %s", exc)
    if t_risk is not None:
        return {
            "vader_compound": compound,
            "transformer_risk": t_risk,
            "text_risk": t_risk,
            "text_risk_source": "transformer",
        }
    return {
        "vader_compound": compound,
        "transformer_risk": None,
        "text_risk": vader_risk_proxy(compound),
        "text_risk_source": "vader_proxy",
    }
