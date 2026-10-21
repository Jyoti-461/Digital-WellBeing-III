from conftest import ZERO


def good_checkin(day="2025-09-01", **over):
    hours = {**ZERO, "social_media": 3.0, "education": 1.0}
    hours.update(over)
    return {"day": day, "hours": hours, "mood_text": "I felt anxious and tired most of the day today"}


def test_health_and_config(client):
    assert client.get("/health").json()["status"] == "ok"
    cfg = client.get("/config").json()
    assert cfg["thresholds_hours"]["social_media"] == 2.0
    assert cfg["helplines"][0]["numbers"][0] == "14416"


def test_register_requires_consent_and_valid_username(client):
    r = client.post("/auth/register", json={"username": "nocon", "password": "longenough1", "consent": False})
    assert r.status_code == 422
    r = client.post("/auth/register", json={"username": "a b", "password": "longenough1", "consent": True})
    assert r.status_code == 422
    r = client.post("/auth/register", json={"username": "okname", "password": "short", "consent": True})
    assert r.status_code == 422


def test_register_login_duplicate(client):
    body = {"username": "dupuser", "password": "longenough1", "consent": True}
    assert client.post("/auth/register", json=body).status_code == 200
    assert client.post("/auth/register", json=body).status_code == 409
    assert client.post("/auth/login", json={"username": "dupuser", "password": "longenough1"}).status_code == 200
    assert client.post("/auth/login", json={"username": "dupuser", "password": "wrong-password"}).status_code == 401
    assert client.post("/auth/login", json={"username": "ghost", "password": "whatever123"}).status_code == 401


def test_checkin_requires_auth(client):
    assert client.post("/checkin", json=good_checkin()).status_code == 401
    assert client.post("/checkin", json=good_checkin(), headers={"Authorization": "Bearer nope"}).status_code == 401


def test_checkin_happy_path(client, auth):
    r = client.post("/checkin", json=good_checkin(), headers=auth)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["exceeded"] == {"social_media": 1.0}
    assert d["violation_ratio"] == round(1 / 6, 3)
    assert d["behavior_source"] == "threshold_rules"
    assert d["text_risk_source"] == "vader_proxy"
    assert 0 <= d["fused_score"] <= 1
    expected = round(0.6 * d["text_risk"] + 0.4 * d["behavior_score"], 2)
    assert abs(d["fused_score"] - expected) < 0.01
    assert d["crisis"] is False
    assert any(x["kind"] == "screen_time" and x["category"] == "social_media" for x in d["recommendations"])


def test_checkin_same_day_overwrites(client, auth):
    client.post("/checkin", json=good_checkin("2025-09-02"), headers=auth)
    client.post("/checkin", json=good_checkin("2025-09-02", gaming=4.0), headers=auth)
    entries = client.get("/history", headers=auth).json()["entries"]
    assert len(entries) == 1 and entries[0]["hours"]["gaming"] == 4.0


def test_checkin_validation(client, auth):
    bad_day = good_checkin(); bad_day["day"] = "01-09-2025"
    assert client.post("/checkin", json=bad_day, headers=auth).status_code == 422
    missing = good_checkin(); del missing["hours"]["gaming"]
    assert client.post("/checkin", json=missing, headers=auth).status_code == 422
    assert client.post("/checkin", json=good_checkin(social_media=-1), headers=auth).status_code == 422
    assert client.post("/checkin", json=good_checkin(social_media=25), headers=auth).status_code == 422
    over = good_checkin(social_media=10, entertainment=10, gaming=5)
    assert client.post("/checkin", json=over, headers=auth).status_code == 422     # total 25
    short = good_checkin(); short["mood_text"] = "ok fine"
    assert client.post("/checkin", json=short, headers=auth).status_code == 422
    empty = good_checkin(); empty["mood_text"] = "   "
    assert client.post("/checkin", json=empty, headers=auth).status_code == 422


def test_crisis_text_triggers_support(client, auth):
    body = good_checkin("2025-09-03"); body["mood_text"] = "I feel like I want to die and nothing helps"
    d = client.post("/checkin", json=body, headers=auth).json()
    assert d["crisis"] is True
    assert d["recommendations"][0]["kind"] == "support"
    assert "14416" in d["recommendations"][0]["body"]


def test_history_isolated_per_user(client, auth):
    import uuid
    other = client.post("/auth/register", json={"username": "o" + uuid.uuid4().hex[:8],
                                                "password": "longenough1", "consent": True}).json()["token"]
    client.post("/checkin", json=good_checkin("2025-09-04"), headers=auth)
    other_hist = client.get("/history", headers={"Authorization": "Bearer " + other}).json()["entries"]
    assert other_hist == []


def test_assessment_flow(client, auth):
    lst = client.get("/assessments", headers=auth).json()["instruments"]
    assert {i["name"] for i in lst} == {"phq9", "gad7", "pss10"}
    inst = client.get("/assessments/phq9", headers=auth).json()
    assert len(inst["items"]) == 9 and inst["options"][0] == "Not at all"
    r = client.post("/assessments/phq9", json={"answers": [1, 1, 1, 1, 1, 1, 1, 1, 0]}, headers=auth).json()
    assert r["total"] == 8 and r["band"] == "mild" and "support" not in r
    r = client.post("/assessments/phq9", json={"answers": [0, 0, 0, 0, 0, 0, 0, 0, 1]}, headers=auth).json()
    assert r["item9_positive"] is True and r["support"]["helplines"][0]["numbers"][0] == "14416"
    assert client.post("/assessments/phq9", json={"answers": [0, 0]}, headers=auth).status_code == 422
    assert client.get("/assessments/nope", headers=auth).status_code == 404


def test_admin_export(client, auth):
    client.post("/checkin", json=good_checkin("2025-09-05"), headers=auth)
    assert client.get("/admin/export/checkins.csv").status_code == 403
    assert client.get("/admin/export/checkins.csv", headers={"X-Admin-Token": "bad"}).status_code == 403
    r = client.get("/admin/export/checkins.csv", headers={"X-Admin-Token": "test-admin-token"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    header = r.text.splitlines()[0]
    assert "fused_score" in header and "mood_text" not in header      # text excluded by default
    r2 = client.get("/admin/export/checkins.csv?include_text=true", headers={"X-Admin-Token": "test-admin-token"})
    assert "mood_text" in r2.text.splitlines()[0]
    assert client.get("/admin/export/assessments.csv", headers={"X-Admin-Token": "test-admin-token"}).status_code == 200


def test_assessment_history_endpoint(client, auth):
    client.post("/assessments/gad7", json={"answers": [1, 1, 1, 1, 1, 1, 1]}, headers=auth)
    client.post("/assessments/phq9", json={"answers": [0] * 9}, headers=auth)
    h = client.get("/history/assessments", headers=auth).json()["entries"]
    assert [e["instrument"] for e in h] == ["phq9", "gad7"]          # newest first
    assert h[1]["total"] == 7 and h[1]["max_total"] == 21 and h[1]["band"] == "mild"
    assert h[0]["title"].startswith("PHQ-9")
    assert client.get("/history/assessments").status_code == 401


def test_insights_endpoint(client, auth):
    for i in range(1, 5):
        client.post("/checkin", json=good_checkin(f"2025-10-{10 + i:02d}", social_media=3.0), headers=auth)
    r = client.get("/insights?today=2025-10-15", headers=auth)
    assert r.status_code == 200, r.text
    d = r.json()
    assert set(d) == {"as_of", "checkin", "questionnaire", "support", "disclaimer"}
    assert d["checkin"]["n_last7"] == 4
    assert any("Social Media was over" in o for o in d["checkin"]["observations"])
    assert client.get("/insights?today=15-10-2025", headers=auth).status_code == 422
    assert client.get("/insights").status_code == 401
    assert client.get("/insights", headers=auth).status_code == 200      # defaults to the server's date
