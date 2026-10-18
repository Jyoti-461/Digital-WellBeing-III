"""Rule-based, tiered recommendations.

Content is general wellbeing guidance written for this project. It is NOT clinical advice
and has not been clinically validated; have it reviewed by your guide / a counsellor.
"""
from . import config

DISCLAIMER = (
    "This app is a self-awareness and screening aid for a research study. "
    "It is not a diagnosis and not a substitute for professional help."
)

_CATEGORY_TIPS = {
    "social_media": "Try turning off non-essential notifications for a few hours, or moving social apps off your home screen.",
    "entertainment": "Pick the one or two things you actually want to watch or listen to, and set a stopping point before you start.",
    "gaming": "Set a session timer before you start and plan something offline for right afterwards.",
    "productivity": "Long work blocks are easier to sustain with short breaks \u2014 stand up and look away from the screen for a few minutes each hour.",
    "education": "Studying matters, but give your eyes a break: every 20 minutes look at something about 20 feet away for 20 seconds (the 20-20-20 rule).",
    "other": "Check which apps are in this bucket \u2014 if it is mostly aimless scrolling, try replacing some of it with a short walk.",
}


def _numbers() -> str:
    return "; ".join(f"{h['name']}: {' or '.join(h['numbers'])}" for h in config.HELPLINES)


def build(hours: dict[str, float], exceeded: dict[str, float], total_over: bool,
          tier: str, crisis: bool) -> list[dict]:
    recs: list[dict] = []

    if crisis:
        recs.append({
            "kind": "support",
            "title": "You don't have to go through this alone",
            "body": "Some of what you wrote suggests you may be having thoughts of harming yourself. "
                    "Please consider reaching out to someone you trust, your college counselling cell, "
                    f"or a helpline right now. {_numbers()}.",
        })
    elif tier == "high":
        recs.append({
            "kind": "support",
            "title": "Today looks like a harder day",
            "body": "Your check-in points to a tougher stretch. Talking to a friend, a family member or your "
                    f"college counselling cell can help. If you would like to speak to someone: {_numbers()}.",
        })
    elif tier == "moderate":
        recs.append({
            "kind": "tip",
            "title": "Keep an eye on how you're feeling",
            "body": "Your check-in is in the middle range. A walk, some sleep, or a chat with someone you trust "
                    "are small things that often help.",
        })
    else:
        recs.append({
            "kind": "tip",
            "title": "Looking steady",
            "body": "Nothing stands out in today's check-in. Keep doing what is working for you.",
        })

    for cat, over in sorted(exceeded.items(), key=lambda kv: -kv[1]):
        label = config.CATEGORY_LABELS[cat]
        recs.append({
            "kind": "screen_time",
            "category": cat,
            "title": f"{label}: {hours[cat]:.1f} h (limit {config.THRESHOLDS_HOURS[cat]:.1f} h)",
            "body": _CATEGORY_TIPS[cat],
        })

    if total_over:
        recs.append({
            "kind": "screen_time",
            "category": "total",
            "title": f"Total screen time is above {config.TOTAL_DAILY_THRESHOLD_HOURS:.0f} h today",
            "body": "Consider a screen-free wind-down before bed; it is a simple place to start.",
        })
    return recs
