import pytest

from app import assessments, config, fusion, nlp_engine, safety, screen_engine


def test_thresholds_match_paper_table_1():
    assert config.THRESHOLDS_HOURS == {
        "social_media": 2.0, "entertainment": 3.0, "gaming": 2.0,
        "productivity": 6.0, "education": 4.0, "other": 2.0,
    }
    assert config.TOTAL_DAILY_THRESHOLD_HOURS == 8.0


def test_violation_ratio_counts_only_categories_over_threshold():
    h = {c: 0.0 for c in config.CATEGORIES}
    assert screen_engine.violation_ratio(h) == 0.0
    h["social_media"] = 2.0          # equal to threshold is NOT a violation
    assert screen_engine.violation_ratio(h) == 0.0
    h["social_media"] = 2.5
    h["gaming"] = 3.0
    assert screen_engine.violation_ratio(h) == 2 / 6
    assert screen_engine.exceeded_categories(h) == {"social_media": 0.5, "gaming": 1.0}


def test_total_exceeded():
    h = {c: 0.0 for c in config.CATEGORIES}
    h["productivity"] = 5.0
    h["education"] = 3.5
    assert screen_engine.total_exceeded(h) is True     # 8.5 > 8
    h["education"] = 3.0
    assert screen_engine.total_exceeded(h) is False    # exactly 8.0


def test_fusion_weights_and_clipping():
    assert fusion.fuse(1.0, 0.0, 0.6, 0.4) == 0.6
    assert fusion.fuse(0.0, 1.0, 0.6, 0.4) == 0.4
    assert fusion.fuse(0.5, 0.5, 3, 2) == 0.5          # weights are normalised
    assert fusion.fuse(1.0, 1.0) == 1.0


def test_tiers():
    assert fusion.tier(0.0) == "low"
    assert fusion.tier(config.TIER_MODERATE) == "moderate"
    assert fusion.tier(config.TIER_HIGH) == "high"


def test_vader_direction_and_proxy():
    pos = nlp_engine.score_text("I had a wonderful day and I feel great and happy")
    neg = nlp_engine.score_text("I feel terrible, hopeless and exhausted today")
    assert pos["vader_compound"] > 0 > neg["vader_compound"]
    assert pos["text_risk"] < neg["text_risk"]
    assert pos["text_risk_source"] == "vader_proxy"
    assert 0.0 <= pos["text_risk"] <= 1.0 and 0.0 <= neg["text_risk"] <= 1.0


def test_safety_keywords():
    assert safety.has_crisis_language("I just want to die")
    assert safety.has_crisis_language("thinking about suicide lately")
    assert safety.has_crisis_language("I keep wanting to hurt myself")
    assert not safety.has_crisis_language("The exam was killing me but I finished my homework")


def test_phq9_scoring_and_bands():
    r = assessments.score("phq9", [0] * 9)
    assert (r["total"], r["band"], r["item9_positive"]) == (0, "minimal", False)
    r = assessments.score("phq9", [1] * 9)
    assert (r["total"], r["band"], r["item9_positive"]) == (9, "mild", True)
    assert assessments.score("phq9", [3] * 9)["band"] == "severe"
    assert assessments.score("phq9", [3] * 9)["total"] == 27
    assert assessments.score("phq9", [2, 2, 2, 2, 2, 0, 0, 0, 0])["band"] == "moderate"  # 10


def test_gad7_bands():
    assert assessments.score("gad7", [0] * 7)["band"] == "minimal"
    assert assessments.score("gad7", [1] * 7)["band"] == "mild"           # 7
    assert assessments.score("gad7", [2] * 7)["band"] == "moderate"       # 14
    assert assessments.score("gad7", [3] * 7)["total"] == 21
    assert assessments.score("gad7", [3] * 7)["band"] == "severe"


def test_pss10_reverse_items():
    r = assessments.score("pss10", [0] * 10)            # items 4,5,7,8 reverse to 4 each => 16
    assert r["total"] == 16 and r["band"] == "moderate"
    assert assessments.score("pss10", [4] * 10)["total"] == 24
    r = assessments.score("pss10", [4, 4, 4, 0, 0, 4, 0, 0, 4, 4])   # 24 + 16
    assert r["total"] == 40 and r["band"] == "high"


def test_assessment_validation():
    with pytest.raises(ValueError):
        assessments.score("phq9", [0] * 8)
    with pytest.raises(ValueError):
        assessments.score("phq9", [4] + [0] * 8)
    with pytest.raises(ValueError):
        assessments.score("pss10", [5] + [0] * 9)


def test_instrument_item_counts():
    assert len(assessments.INSTRUMENTS["phq9"]["items"]) == 9
    assert len(assessments.INSTRUMENTS["gad7"]["items"]) == 7
    assert len(assessments.INSTRUMENTS["pss10"]["items"]) == 10


def test_random_forest_path_is_used_when_model_file_exists(tmp_path):
    """Trains a tiny RF on SYNTHETIC rows just to prove the loading/inference path works."""
    import joblib
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier

    rng = np.random.default_rng(0)
    X = rng.uniform(0, 8, size=(120, 6))
    y = (X[:, 0] + X[:, 1] > 6).astype(int)
    clf = RandomForestClassifier(n_estimators=10, random_state=42).fit(X, y)
    path = tmp_path / "rf.joblib"
    joblib.dump({"model": clf, "features": config.CATEGORIES}, path)

    old = config.SCREEN_MODEL_PATH
    try:
        config.SCREEN_MODEL_PATH = str(path)
        screen_engine.reset_model_cache()
        heavy = {c: 0.0 for c in config.CATEGORIES}
        heavy.update(social_media=5.0, entertainment=4.0)
        light = {c: 0.0 for c in config.CATEGORIES}
        s_heavy, src = screen_engine.behavior_score(heavy)
        s_light, _ = screen_engine.behavior_score(light)
        assert src == "random_forest"
        assert 0.0 <= s_light < s_heavy <= 1.0
    finally:
        config.SCREEN_MODEL_PATH = old
        screen_engine.reset_model_cache()
