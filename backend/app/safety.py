"""Keyword-based crisis-language check.

This is a deliberately conservative *safety net*, not a classifier. It will miss
indirect or non-English expressions and will flag negated sentences ("I would never
hurt myself"). It is meant to err on the side of showing support information.
"""
import re

_PATTERNS = [
    r"\bsuicid(e|al)\b",
    r"\bkill(ing)? myself\b",
    r"\bend(ing)? (my|this) life\b",
    r"\bwant(ed)? to die\b",
    r"\bbetter off dead\b",
    r"\bdon'?t want to (live|be alive)\b",
    r"\bno reason to live\b",
    r"\b(hurt|harm|cut)(ting)? myself\b",
    r"\bself[- ]?harm\b",
]
_RX = re.compile("|".join(_PATTERNS), re.IGNORECASE)


def has_crisis_language(text: str) -> bool:
    return bool(_RX.search(text))
