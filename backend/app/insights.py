"""Personal insights computed from a user's OWN check-ins and questionnaires.

Design rules (so this stays honest):
* Every observation is a simple calculation on the user's data and says how much data it used.
* Nothing here is a diagnosis or a clinical recommendation. The do / try-to-avoid lists are general
  wellbeing suggestions written for this project and have not been clinically validated; have them
  reviewed by your guide or a counsellor.
* The "combined score" comes from a research prototype (the text part is a placeholder proxy until a model
  is trained), so insights describe changes in that signal, not in the person's health.
* Thresholds below marked PLACEHOLDER are arbitrary starting values, not published cut-offs.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from statistics import mean, median

from . import assessments, config
from .recommend import _CATEGORY_TIPS

TREND_DELTA = 0.05          # PLACEHOLDER: change in mean combined score treated as "higher/lower"
MIN_PER_WEEK = 3            # check-ins needed in each of two weeks for a weekly comparison
CATEGORY_MIN_DAYS = 3       # a category must be over its limit on at least this many days ...
CATEGORY_MIN_SHARE = 0.5    # ... and on at least this share of the check-ins in the last two weeks
PATTERN_MIN_ENTRIES = 7     # check-ins (last 30 days) needed to compare heavier vs lighter screen days
PATTERN_MIN_EACH_SIDE = 3
PATTERN_DELTA = 0.10        # PLACEHOLDER: difference in mean text signal treated as a pattern
MAX_ITEMS = 5

DISCLAIMER = (
    "These insights are simple patterns calculated from your own entries. They are general wellbeing "
    "suggestions written for this study, not medical advice. A pattern is not proof that one thing causes "
    "another, and the combined score comes from a research prototype, not a measure of your health."
)

_NAMES = {"phq9": "PHQ-9", "gad7": "GAD-7", "pss10": "PSS-10"}
_CONCERNING = {
    "phq9": {"moderate", "moderately severe", "severe"},
    "gad7": {"moderate", "severe"},
    "pss10": {"high"},
}


def _d(day: str) -> date:
    return datetime.strptime(day, "%Y-%m-%d").date()


def _window(entries: list[dict], start: date, end: date) -> list[dict]:
    return [e for e in entries if start <= _d(e["day"]) <= end]


def _dedupe(items: list[str], cap: int = MAX_ITEMS) -> list[str]:
    seen, out = set(), []
    for i in items:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out[:cap]


def _checkin_section(checkins: list[dict], today: date) -> tuple[dict, bool]:
    obs: list[str] = []
    do: list[str] = []
    dont: list[str] = []
    crisis_recent = False

    recent = _window(checkins, today - timedelta(days=6), today)
    prev = _window(checkins, today - timedelta(days=13), today - timedelta(days=7))
    last14 = _window(checkins, today - timedelta(days=13), today)
    last30 = _window(checkins, today - timedelta(days=29), today)

    # --- weekly trend
    if len(recent) >= MIN_PER_WEEK and len(prev) >= MIN_PER_WEEK:
        diff = mean(e["fused_score"] for e in recent) - mean(e["fused_score"] for e in prev)
        if diff >= TREND_DELTA:
            obs.append(f"Your combined score over the last 7 days is higher than the week before ({diff:+.2f}).")
            do.append("Pick one small change this week, such as a fixed bedtime, a short walk or a chat with a "
                      "friend, and see whether the pattern shifts.")
            dont.append("Try not to ignore a rising pattern on your own; tell someone you trust how you have been feeling.")
        elif diff <= -TREND_DELTA:
            obs.append(f"Your combined score over the last 7 days is lower than the week before ({diff:+.2f}).")
            do.append("Notice what has been different this week and keep doing it.")
        else:
            obs.append(f"Your combined score is about the same as the week before (change {diff:+.2f}).")
    else:
        obs.append("There are not yet enough check-ins to compare this week with last week "
                   f"(at least {MIN_PER_WEEK} in each week are needed).")

    # --- which categories are repeatedly over their limit
    if last14:
        n = len(last14)
        counts = {c: sum(1 for e in last14 if e["hours"][c] > config.THRESHOLDS_HOURS[c]) for c in config.CATEGORIES}
        frequent = sorted(
            [(c, k) for c, k in counts.items() if k >= CATEGORY_MIN_DAYS and k / n >= CATEGORY_MIN_SHARE],
            key=lambda ck: -ck[1],
        )[:2]
        for cat, k in frequent:
            obs.append(f"{config.CATEGORY_LABELS[cat]} was over its {config.THRESHOLDS_HOURS[cat]:g} h limit on "
                       f"{k} of your {n} check-ins in the last two weeks.")
            do.append(_CATEGORY_TIPS[cat])
        total_days = sum(1 for e in last14 if sum(e["hours"].values()) > config.TOTAL_DAILY_THRESHOLD_HOURS)
        if total_days >= CATEGORY_MIN_DAYS and total_days / n >= CATEGORY_MIN_SHARE:
            obs.append(f"Your total screen time was above {config.TOTAL_DAILY_THRESHOLD_HOURS:g} h on "
                       f"{total_days} of your {n} check-ins.")
            dont.append("Try not to let long sessions run without a break; a few minutes away from the screen "
                        "each hour is a simple start.")

    # --- heavier vs lighter screen-time days (within the user's own data)
    if len(last30) >= PATTERN_MIN_ENTRIES:
        totals = [sum(e["hours"].values()) for e in last30]
        med = median(totals)
        high = [e for e, t in zip(last30, totals) if t > med]
        low = [e for e, t in zip(last30, totals) if t <= med]
        if len(high) >= PATTERN_MIN_EACH_SIDE and len(low) >= PATTERN_MIN_EACH_SIDE:
            d = mean(e["text_risk"] for e in high) - mean(e["text_risk"] for e in low)
            if d >= PATTERN_DELTA:
                obs.append("On your heavier screen-time days, your mood notes tended to read more negative than on "
                           "your lighter days. This is a pattern in your own data, not proof that screen time is the cause.")
                do.append("On days you expect a lot of screen time, plan one offline thing you enjoy.")
            elif d <= -PATTERN_DELTA:
                obs.append("Your heavier screen-time days did not read more negative than your lighter days; "
                           "if anything your notes were more positive on them.")
            else:
                obs.append("There is no clear difference in how your notes read on heavier versus lighter "
                           "screen-time days.")
    else:
        obs.append(f"A comparison of heavier and lighter screen-time days needs at least {PATTERN_MIN_ENTRIES} "
                   "check-ins in the last 30 days.")

    # --- consistency
    if len(recent) >= 5:
        do.append("Keep up your daily check-ins; more entries make these insights more reliable.")
    elif len(recent) < MIN_PER_WEEK:
        do.append("Try to check in most days this week; the insights need a few entries to be useful.")

    # --- recent crisis wording (shown as a support card, not as an observation)
    crisis_recent = any(e.get("crisis_flag") for e in last14)

    return {
        "n_last7": len(recent),
        "n_total": len(checkins),
        "observations": _dedupe(obs, cap=8),
        "do": _dedupe(do),
        "dont": _dedupe(dont),
    }, crisis_recent


def _questionnaire_section(rows: list[dict]) -> tuple[dict, bool]:
    obs: list[str] = []
    do: list[str] = []
    dont: list[str] = []
    item9 = False
    concerning: list[str] = []

    for inst in ("phq9", "gad7", "pss10"):
        items = [r for r in rows if r["instrument"] == inst]
        if not items:
            continue
        latest = items[0]
        name = _NAMES[inst]
        maxv = assessments.max_total(inst)
        text = f"{name}: latest score {latest['total']} of {maxv} ({latest['band']}) on {latest['created_at'][:10]}"
        if len(items) > 1:
            prev = items[1]
            delta = latest["total"] - prev["total"]
            if delta > 0:
                text += f", up {delta} point{'s' if delta != 1 else ''} since {prev['created_at'][:10]}"
            elif delta < 0:
                text += f", down {-delta} point{'s' if delta != -1 else ''} since {prev['created_at'][:10]}"
            else:
                text += f", unchanged since {prev['created_at'][:10]}"
        obs.append(text + ".")
        if latest["band"] in _CONCERNING[inst]:
            concerning.append(name)
        if inst == "phq9" and latest.get("item9_positive"):
            item9 = True

    if not obs:
        obs.append("No questionnaires completed yet.")
        do.append("Complete a questionnaire when your researcher asks you to; they let the study compare the "
                  "app's signals with established scales.")
    else:
        if any(len([r for r in rows if r["instrument"] == i]) > 1 for i in _NAMES):
            obs.append("Small differences between two readings can be ordinary day-to-day variation.")
        if concerning:
            obs.append(f"Your latest {' and '.join(concerning)} score is in a range that is worth talking over with someone.")
            do.append("Consider booking a chat with your college counselling cell or a doctor. A screening score "
                      "cannot diagnose anything, but a professional can help you make sense of it.")
            dont.append("Try not to wait it out alone if low mood, worry or stress has lasted for weeks.")
        else:
            do.append("Keep an eye on how you feel, and repeat the questionnaires when your researcher asks; "
                      "that shows how things change over time.")

    return {"observations": obs, "do": _dedupe(do), "dont": _dedupe(dont)}, item9


def build_insights(checkins: list[dict], assessment_rows: list[dict], today: date) -> dict:
    """checkins: newest-first dicts {day, hours{cat: h}, text_risk, fused_score, tier, crisis_flag}
    assessment_rows: newest-first dicts {instrument, total, band, item9_positive, created_at}"""
    ci, crisis_recent = _checkin_section(checkins, today)
    qu, item9 = _questionnaire_section(assessment_rows)

    support = None
    if crisis_recent or item9:
        reason = ("Some of your recent notes included very heavy wording." if crisis_recent
                  else "You indicated thoughts of being better off dead or of hurting yourself on a recent PHQ-9.")
        support = {
            "message": reason + " You do not have to handle this alone. Please consider talking to someone you "
                                "trust, your college counselling cell, or a helpline.",
            "helplines": config.HELPLINES,
        }
    return {"as_of": today.isoformat(), "checkin": ci, "questionnaire": qu, "support": support,
            "disclaimer": DISCLAIMER}
