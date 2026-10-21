from datetime import date, timedelta

from conftest import ZERO
from app import config, insights

TODAY = date(2025, 10, 20)


def entry(days_ago, fused=0.4, text=0.4, crisis=False, **hours):
    h = {**ZERO, **hours}
    return {"day": (TODAY - timedelta(days=days_ago)).isoformat(), "hours": h, "text_risk": text,
            "fused_score": fused, "tier": "low", "crisis_flag": crisis}


def assess(inst, total, band, days_ago=0, item9=False):
    return {"instrument": inst, "total": total, "band": band, "item9_positive": item9,
            "created_at": (TODAY - timedelta(days=days_ago)).isoformat() + "T10:00:00+00:00"}


def test_no_data_is_honest_and_gives_no_support_card():
    r = insights.build_insights([], [], TODAY)
    text = " ".join(r["checkin"]["observations"])
    assert "not yet enough check-ins" in text
    assert any("check in most days" in d for d in r["checkin"]["do"])
    assert r["questionnaire"]["observations"] == ["No questionnaires completed yet."]
    assert r["support"] is None


def test_weekly_trend_higher_lower_and_steady():
    up = [entry(i, fused=0.7) for i in (0, 1, 2, 3)] + [entry(i, fused=0.4) for i in (7, 8, 9, 10)]
    r = insights.build_insights(up, [], TODAY)
    assert any("higher than the week before" in o for o in r["checkin"]["observations"])
    assert any("small change" in d for d in r["checkin"]["do"])
    assert r["checkin"]["dont"]

    down = [entry(i, fused=0.3) for i in (0, 1, 2)] + [entry(i, fused=0.6) for i in (7, 8, 9)]
    r = insights.build_insights(down, [], TODAY)
    assert any("lower than the week before" in o for o in r["checkin"]["observations"])

    same = [entry(i, fused=0.40) for i in (0, 1, 2)] + [entry(i, fused=0.42) for i in (7, 8, 9)]
    r = insights.build_insights(same, [], TODAY)
    assert any("about the same" in o for o in r["checkin"]["observations"])


def test_needs_three_per_week_for_trend():
    few = [entry(0, fused=0.9), entry(1, fused=0.9), entry(7, fused=0.1), entry(8, fused=0.1)]
    r = insights.build_insights(few, [], TODAY)
    assert not any("higher than" in o or "lower than" in o for o in r["checkin"]["observations"])


def test_frequent_category_is_reported_with_counts_and_tip():
    rows = [entry(i, social_media=3.0) for i in range(5)]
    r = insights.build_insights(rows, [], TODAY)
    obs = " ".join(r["checkin"]["observations"])
    assert "Social Media was over its 2 h limit on 5 of your 5 check-ins" in obs
    assert any("notifications" in d for d in r["checkin"]["do"])


def test_category_not_reported_below_minimum_days():
    rows = [entry(0, social_media=3.0), entry(1, social_media=3.0)] + [entry(i) for i in (2, 3, 4)]
    r = insights.build_insights(rows, [], TODAY)
    assert "Social Media was over" not in " ".join(r["checkin"]["observations"])


def test_total_screen_time_pattern_adds_break_advice():
    rows = [entry(i, productivity=5.0, education=3.5) for i in range(4)]    # 8.5 h > 8 h
    r = insights.build_insights(rows, [], TODAY)
    assert any("total screen time was above 8 h" in o for o in r["checkin"]["observations"])
    assert any("long sessions" in d for d in r["checkin"]["dont"])


def test_heavy_days_read_more_negative_pattern():
    rows = []
    for i in range(8):
        if i % 2 == 0:
            rows.append(entry(i, text=0.8, entertainment=6.0))
        else:
            rows.append(entry(i, text=0.3, entertainment=1.0))
    r = insights.build_insights(rows, [], TODAY)
    assert any("more negative" in o and "not proof" in o for o in r["checkin"]["observations"])


def test_pattern_needs_enough_entries():
    r = insights.build_insights([entry(i) for i in range(5)], [], TODAY)
    assert any("needs at least 7" in o for o in r["checkin"]["observations"])


def test_recent_crisis_flag_shows_support_card():
    r = insights.build_insights([entry(2, crisis=True)], [], TODAY)
    assert r["support"] is not None
    assert r["support"]["helplines"][0]["numbers"][0] == "14416"
    old = insights.build_insights([entry(20, crisis=True)], [], TODAY)     # outside the 14-day window
    assert old["support"] is None


def test_questionnaire_change_and_concerning_band():
    rows = [assess("phq9", 12, "moderate", 0), assess("phq9", 6, "mild", 14),
            assess("gad7", 3, "minimal", 1)]
    r = insights.build_insights([], rows, TODAY)
    obs = " ".join(r["questionnaire"]["observations"])
    assert "PHQ-9: latest score 12 of 27 (moderate)" in obs and "up 6 points" in obs
    assert "GAD-7: latest score 3 of 21 (minimal)" in obs
    assert "worth talking over" in obs
    assert any("counselling cell" in d for d in r["questionnaire"]["do"])
    assert r["questionnaire"]["dont"]
    assert r["support"] is None


def test_item9_positive_triggers_support():
    r = insights.build_insights([], [assess("phq9", 3, "minimal", 0, item9=True)], TODAY)
    assert r["support"] is not None and "PHQ-9" in r["support"]["message"]


def test_non_concerning_questionnaires_get_gentle_guidance():
    r = insights.build_insights([], [assess("pss10", 10, "low")], TODAY)
    assert not any("worth talking over" in o for o in r["questionnaire"]["observations"])
    assert r["questionnaire"]["dont"] == []


def test_lists_are_capped_and_disclaimer_present():
    r = insights.build_insights([entry(i, social_media=3, gaming=3, productivity=7, education=2) for i in range(8)], [], TODAY)
    assert len(r["checkin"]["do"]) <= insights.MAX_ITEMS and len(r["checkin"]["dont"]) <= insights.MAX_ITEMS
    assert "not medical advice" in r["disclaimer"]
