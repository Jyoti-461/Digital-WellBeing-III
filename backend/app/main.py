"""FastAPI service for the NLP-Augmented Personalized Digital Wellbeing app."""
from __future__ import annotations

import csv
import hmac
import io
import json
import re
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response
from pydantic import BaseModel, Field

from . import assessments, config, fusion, nlp_engine, recommend, safety, screen_engine, security
from .db import db, init_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Digital Wellbeing API", version="1.0.0", lifespan=lifespan)

USERNAME_RX = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


# ------------------------------------------------------------------ models
class RegisterIn(BaseModel):
    username: str
    password: str = Field(min_length=8, max_length=128)
    consent: bool
    age_group: Optional[str] = Field(default=None, max_length=32)
    gender: Optional[str] = Field(default=None, max_length=32)
    residence: Optional[str] = Field(default=None, max_length=32)


class LoginIn(BaseModel):
    username: str
    password: str


class CheckinIn(BaseModel):
    day: str                              # yyyy-MM-dd, the device's local date
    hours: dict[str, float]               # exactly the six category keys, hours 0..24
    mood_text: str


class AssessmentIn(BaseModel):
    answers: list[int]


# ------------------------------------------------------------------ auth
def current_user(authorization: Optional[str] = Header(default=None)) -> sqlite3.Row:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    raw = authorization.split(" ", 1)[1].strip()
    with db() as conn:
        row = conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token_hash = ? AND s.expires_at > ?",
            (security.token_hash(raw), security.iso(security.now_utc())),
        ).fetchone()
    if row is None:
        raise HTTPException(401, "invalid or expired token")
    return row


def _issue_token(conn: sqlite3.Connection, user_id: int) -> str:
    raw, hashed = security.new_token()
    conn.execute("INSERT INTO sessions(token_hash, user_id, expires_at) VALUES (?,?,?)",
                 (hashed, user_id, security.session_expiry()))
    return raw


def require_admin(x_admin_token: Optional[str] = Header(default=None)) -> None:
    if not config.ADMIN_TOKEN:
        raise HTTPException(404, "admin endpoints are disabled (ADMIN_TOKEN not set)")
    if not x_admin_token or not hmac.compare_digest(x_admin_token, config.ADMIN_TOKEN):
        raise HTTPException(403, "bad admin token")


# ------------------------------------------------------------------ public
@app.get("/health")
def health():
    return {"status": "ok", "transformer_loaded": nlp_engine._transformer is not None}


@app.get("/config")
def public_config():
    return {
        "categories": config.CATEGORIES,
        "labels": config.CATEGORY_LABELS,
        "thresholds_hours": config.THRESHOLDS_HOURS,
        "total_daily_threshold_hours": config.TOTAL_DAILY_THRESHOLD_HOURS,
        "min_words": config.MIN_WORDS,
        "helplines": config.HELPLINES,
        "disclaimer": recommend.DISCLAIMER,
    }


@app.post("/auth/register")
def register(body: RegisterIn):
    if not USERNAME_RX.match(body.username):
        raise HTTPException(422, "username must be 3-32 chars: letters, digits, _ . -")
    if not body.consent:
        raise HTTPException(422, "consent is required to join the study")
    salt, digest = security.hash_password(body.password)
    now = security.iso(security.now_utc())
    with db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users(username, pw_salt, pw_hash, age_group, gender, residence, consent_at, created_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (body.username, salt, digest, body.age_group, body.gender, body.residence, now, now),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "username already taken")
        token = _issue_token(conn, cur.lastrowid)
    return {"token": token}


@app.post("/auth/login")
def login(body: LoginIn):
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (body.username,)).fetchone()
        if row is None:
            # burn comparable time so unknown users are not distinguishable by latency
            security.hash_password(body.password)
            raise HTTPException(401, "wrong username or password")
        if not security.verify_password(body.password, row["pw_salt"], row["pw_hash"]):
            raise HTTPException(401, "wrong username or password")
        token = _issue_token(conn, row["id"])
    return {"token": token}


# ------------------------------------------------------------------ check-in
def _validate_checkin(body: CheckinIn) -> tuple[dict[str, float], str]:
    try:
        datetime.strptime(body.day, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(422, "day must be yyyy-MM-dd")
    if set(body.hours) != set(config.CATEGORIES):
        raise HTTPException(422, f"hours must contain exactly: {', '.join(config.CATEGORIES)}")
    for cat, val in body.hours.items():
        if not (0.0 <= val <= 24.0):
            raise HTTPException(422, f"hours for {cat} must be between 0 and 24")
    if sum(body.hours.values()) > 24.01:
        raise HTTPException(422, "total hours cannot exceed 24")
    text = body.mood_text.strip()
    if len(text) > config.MAX_TEXT_CHARS:
        raise HTTPException(422, f"mood_text is limited to {config.MAX_TEXT_CHARS} characters")
    if len(text.split()) < config.MIN_WORDS:
        raise HTTPException(422, f"please write at least {config.MIN_WORDS} words about how your day felt")
    return {c: float(body.hours[c]) for c in config.CATEGORIES}, text


@app.post("/checkin")
def checkin(body: CheckinIn, user=Depends(current_user)):
    hours, text = _validate_checkin(body)

    nlp = nlp_engine.score_text(text)
    exceeded = screen_engine.exceeded_categories(hours)
    ratio = screen_engine.violation_ratio(hours)
    beh_score, beh_source = screen_engine.behavior_score(hours)
    fused = fusion.fuse(nlp["text_risk"], beh_score)
    tier = fusion.tier(fused)
    crisis = safety.has_crisis_language(text)
    recs = recommend.build(hours, exceeded, screen_engine.total_exceeded(hours), tier, crisis)

    with db() as conn:
        conn.execute(
            """INSERT INTO checkins(user_id, day, social_media, entertainment, gaming, productivity,
                   education, other, mood_text, vader_compound, transformer_risk, text_risk,
                   text_risk_source, violation_ratio, behavior_score, behavior_source,
                   fused_score, tier, crisis_flag, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(user_id, day) DO UPDATE SET
                   social_media=excluded.social_media, entertainment=excluded.entertainment,
                   gaming=excluded.gaming, productivity=excluded.productivity,
                   education=excluded.education, other=excluded.other,
                   mood_text=excluded.mood_text, vader_compound=excluded.vader_compound,
                   transformer_risk=excluded.transformer_risk, text_risk=excluded.text_risk,
                   text_risk_source=excluded.text_risk_source,
                   violation_ratio=excluded.violation_ratio, behavior_score=excluded.behavior_score,
                   behavior_source=excluded.behavior_source, fused_score=excluded.fused_score,
                   tier=excluded.tier, crisis_flag=excluded.crisis_flag, created_at=excluded.created_at""",
            (user["id"], body.day, *[hours[c] for c in config.CATEGORIES], text,
             nlp["vader_compound"], nlp["transformer_risk"], nlp["text_risk"], nlp["text_risk_source"],
             ratio, beh_score, beh_source, fused, tier, int(crisis),
             security.iso(security.now_utc())),
        )

    return {
        "day": body.day,
        "vader_compound": round(nlp["vader_compound"], 3),
        "text_risk": round(nlp["text_risk"], 3),
        "text_risk_source": nlp["text_risk_source"],
        "violation_ratio": round(ratio, 3),
        "behavior_score": round(beh_score, 3),
        "behavior_source": beh_source,
        "fused_score": round(fused, 3),
        "tier": tier,
        "exceeded": exceeded,
        "crisis": crisis,
        "recommendations": recs,
        "disclaimer": recommend.DISCLAIMER,
    }


@app.get("/history")
def history(days: int = Query(default=30, ge=1, le=366), user=Depends(current_user)):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM checkins WHERE user_id = ? ORDER BY day DESC LIMIT ?", (user["id"], days)
        ).fetchall()
    return {
        "entries": [
            {
                "day": r["day"],
                "hours": {c: r[c] for c in config.CATEGORIES},
                "vader_compound": round(r["vader_compound"], 3),
                "text_risk": round(r["text_risk"], 3),
                "behavior_score": round(r["behavior_score"], 3),
                "fused_score": round(r["fused_score"], 3),
                "tier": r["tier"],
            }
            for r in rows
        ]
    }


# ------------------------------------------------------------------ assessments
@app.get("/assessments")
def list_assessments(_=Depends(current_user)):
    return {"instruments": [{"name": k, "title": v["title"], "n_items": len(v["items"])}
                            for k, v in assessments.INSTRUMENTS.items()]}


@app.get("/assessments/{name}")
def get_assessment(name: str, _=Depends(current_user)):
    inst = assessments.INSTRUMENTS.get(name)
    if inst is None:
        raise HTTPException(404, "unknown instrument")
    return {"name": name, **inst}


@app.post("/assessments/{name}")
def submit_assessment(name: str, body: AssessmentIn, user=Depends(current_user)):
    if name not in assessments.INSTRUMENTS:
        raise HTTPException(404, "unknown instrument")
    try:
        result = assessments.score(name, body.answers)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    with db() as conn:
        conn.execute(
            "INSERT INTO assessments(user_id, instrument, answers_json, total, band, item9_positive, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (user["id"], name, json.dumps(body.answers), result["total"], result["band"],
             int(result["item9_positive"]), security.iso(security.now_utc())),
        )
    out = {"instrument": name, **result, "disclaimer": recommend.DISCLAIMER}
    if result["item9_positive"]:
        out["support"] = {
            "message": "You indicated thoughts of being better off dead or of hurting yourself. "
                       "Please consider talking to someone you trust, your college counselling cell, "
                       "or a helpline today.",
            "helplines": config.HELPLINES,
        }
    return out


# ------------------------------------------------------------------ admin export
def _csv_response(rows: list[sqlite3.Row], filename: str) -> Response:
    buf = io.StringIO()
    if rows:
        writer = csv.writer(buf)
        writer.writerow(rows[0].keys())
        for r in rows:
            writer.writerow([r[k] for k in r.keys()])
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/admin/export/checkins.csv")
def export_checkins(include_text: bool = False, _=Depends(require_admin)):
    cols = ("c.user_id, u.age_group, u.gender, u.residence, c.day, c.social_media, c.entertainment, "
            "c.gaming, c.productivity, c.education, c.other, c.vader_compound, c.transformer_risk, "
            "c.text_risk, c.text_risk_source, c.violation_ratio, c.behavior_score, c.behavior_source, "
            "c.fused_score, c.tier, c.crisis_flag")
    if include_text:
        cols += ", c.mood_text"
    with db() as conn:
        rows = conn.execute(
            f"SELECT {cols} FROM checkins c JOIN users u ON u.id = c.user_id ORDER BY c.user_id, c.day"
        ).fetchall()
    return _csv_response(rows, "checkins.csv")


@app.get("/admin/export/assessments.csv")
def export_assessments(_=Depends(require_admin)):
    with db() as conn:
        rows = conn.execute(
            "SELECT a.user_id, u.age_group, u.gender, u.residence, a.instrument, a.total, a.band, "
            "a.item9_positive, a.created_at FROM assessments a JOIN users u ON u.id = a.user_id "
            "ORDER BY a.user_id, a.created_at"
        ).fetchall()
    return _csv_response(rows, "assessments.csv")
