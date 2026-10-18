# NLP-Augmented Personalized Digital Wellbeing — project

MCA Sem 3 capstone (TIMSCDR). A native Android app (Flutter) that reads the student's screen time from the
phone, takes a short free-text mood note, fuses the two signals on a FastAPI backend and returns a
personalised, tiered recommendation. PHQ-9 / GAD-7 / PSS-10 questionnaires are collected in-app to validate
the signals during the pilot.

```
Android app (Flutter + Kotlin bridge)                    FastAPI backend (Python)
 ├─ UsageStatsManager  → per-app minutes today            ├─ /auth, /checkin, /history, /assessments
 ├─ app → 6 categories (category_map.dart)    ──HTTP──▶   ├─ NLP arm: VADER  (+ optional fine-tuned transformer)
 ├─ mood note (typed)                                     ├─ Screen arm: Table-I thresholds (+ optional Random Forest)
 └─ dashboard, questionnaires                             ├─ Late fusion: 0.6·text + 0.4·behaviour (configurable)
                                                          ├─ Recommendations + crisis-language safety net
                                                          └─ SQLite + CSV export for analysis
```

## What is verified and what is not (read this first)

| Part | Status |
|---|---|
| Backend (auth, check-in, fusion, thresholds, recommendations, PHQ-9/GAD-7/PSS-10 scoring, CSV export) | **Tested**: 24 automated tests pass (`pytest`), and a live `uvicorn` server was exercised with curl. |
| Random Forest training script | **Run** on *synthetic* data only, to prove the pipeline works. The accuracy it prints on that data means nothing. |
| `setup.py` manifest patching | **Tested** on a sample manifest I wrote by hand (well-formed XML, idempotent). Not run against a real `flutter create` output. |
| Flutter/Dart app and Kotlin `MainActivity.kt` | **NOT compiled or run.** The build environment had no Flutter/Dart/Kotlin toolchain. I reviewed the code and fixed the type errors I found, but expect to fix some compile errors on first build. Please report them. |
| `scripts/finetune_text_model.py` | **NOT run** (needs Hugging Face downloads + GPU). Syntax-checked only. |
| Package ids in `category_map.dart` | **Unverified starter list**, written from general knowledge. Check each against its Play Store `id=`. |
| Accuracy of the on-device usage numbers | **Unvalidated.** Compare against the phone's own Digital Wellbeing screen on a pilot device. |

Facts I did check against sources: the Tele-MANAS helpline numbers (14416 / 1-800-891-4416), the Android
`UsageEvents.Event` constants used, the wording of PHQ-9 / GAD-7 / PSS-10 items and their score bands, and
that MentalBERT is a gated masked-language model (see below).

## Run the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest -q                                              # optional: should report 24 passed
ADMIN_TOKEN=choose-a-long-secret uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Interactive API docs: http://localhost:8000/docs. Data is stored in `backend/wellbeing.db` (SQLite).
Without any trained model the backend runs in a fully working fallback mode: VADER proxy for text and the
threshold rule for behaviour (the check-in response says which source was used).

## Build the Android app

Requires Flutter (run `flutter doctor`) and Python 3.
```bash
cd flutter_app
python setup.py          # creates ./app via `flutter create`, adds http + shared_preferences, applies overlay
cd app
flutter run              # emulator or USB phone
flutter build apk --release   # APK for the pilot (build/app/outputs/flutter-apk/)
```
`setup.py` replaces `MainActivity.kt` and adds `INTERNET`, `PACKAGE_USAGE_STATS` and cleartext-HTTP to the
manifest. On first launch the app sends the student to Settings → Usage access (Android shows no pop-up for
this permission). On the sign-in screen enter the server address: `http://10.0.2.2:8000` reaches the backend
from the Android emulator; from a real phone use your computer's LAN IP (same Wi-Fi), e.g. `http://192.168.1.10:8000`.

## From pilot data to research results

1. Collect data (`GET /admin/export/checkins.csv`, add `?include_text=true` for the mood text;
   `GET /admin/export/assessments.csv`; send header `X-Admin-Token`). Exports use pseudonymous `user_id`, not usernames.
2. Decide what "at risk" means (e.g. PHQ-9 ≥ 10 in the same period), build a CSV with the six hour columns + `label`,
   then `python scripts/train_screen_model.py your.csv` → `data/screen_rf.joblib` (loaded automatically).
3. For the text arm, supply a labelled text dataset and run `scripts/finetune_text_model.py`
   (then set `TRANSFORMER_MODEL_DIR`). Until then the text arm is only the VADER proxy.
4. Calibrate `TIER_MODERATE`, `TIER_HIGH`, `W_TEXT`, `W_BEHAVIOR` (env vars / `app/config.py`) against PHQ-9/GAD-7/PSS.
5. Compare text-only vs screen-only vs fused against the questionnaires — that comparison is the paper's result.

## Decisions and deviations from the earlier plan (please read)

* **Firebase was replaced** by backend auth (PBKDF2 password hashes, hashed session tokens, SQLite). Reason: Firebase needs
  your own project credentials, so a zip could not run without them. You can swap it in later.
* **The "risk" from VADER is a placeholder**: `(1 − compound)/2`. It is a sentiment proxy, not a validated depression
  measure. Do not present it as a finding.
* **Correction to the earlier project report/paper code snippet:** it loaded `mental/mental-bert-base-uncased` into a
  `text-classification` pipeline. That checkpoint is a gated fill-mask model with no classification head, so that snippet
  would not produce a meaningful risk score. This build only uses a transformer if you fine-tune one first.
  Also check the licence of any MentalBERT checkpoint (the AIMH repos list cc-by-nc-4.0).
* **The report's `usage_fetcher.dart` snippet used a third-party plugin whose API I did not verify.** This build instead
  calls Android's `UsageStatsManager.queryEvents` directly from Kotlin.
* **Questionnaire cadence:** PHQ-9/GAD-7 ask about the last 2 weeks and PSS-10 about the last month, so weekly repeats
  overlap in what they measure. Choose the schedule deliberately and justify it in the paper.
* **Licences:** PHQ-9/GAD-7 sheets carry notices (Pfizer copyright on PHQ-9; GAD-7 sheets state no permission needed).
  The CMU PSS page directs permission requests to MAPI Research Trust. Confirm your position before deployment.
* **Ethics/consent:** the consent text in `auth_screen.dart` is a draft. Replace it with wording approved by your
  institution and get approval before recruiting students. Mood text is sensitive; restrict access to the database and exports.
* **Safety net:** a keyword check shows support information (Tele-MANAS) when crisis language is detected, and when PHQ-9
  item 9 is above 0. It is English-only, misses indirect wording and flags negations. It is not a substitute for a
  referral process — agree one with your guide / the college counselling cell before the pilot.
* **Transport security:** the app allows plain HTTP so a LAN pilot works. For anything else, put the backend behind HTTPS
  and remove `usesCleartextTraffic` from the manifest.
* **Android only**, as decided (Apple does not let a general app read other apps' usage). Some manufacturers' Android
  builds behave differently for usage access; test on the devices your participants use.
* **One check-in per day** is stored (submitting again the same day overwrites it).
* **Not implemented:** admin web UI, login rate-limiting, password reset, push reminders, iOS.

## API summary

| Method & path | Purpose |
|---|---|
| `GET /health`, `GET /config` | status; thresholds, labels, helplines (single source of truth for the app) |
| `POST /auth/register`, `POST /auth/login` | returns a bearer token (register requires `consent: true`) |
| `POST /checkin` | `{day, hours{6 categories}, mood_text}` → scores, tier, recommendations |
| `GET /history?days=30` | the user's past check-ins |
| `GET /assessments`, `GET/POST /assessments/{phq9\|gad7\|pss10}` | questionnaires and scoring |
| `GET /admin/export/checkins.csv`, `/assessments.csv` | research export (needs `X-Admin-Token`) |

## Layout
```
backend/app/        FastAPI app (config, db, security, nlp_engine, screen_engine, fusion, safety, recommend, assessments, main)
backend/data/       instruments.json (questionnaire items); trained models are written here
backend/scripts/    make_synthetic_data.py (pipeline testing only), train_screen_model.py, finetune_text_model.py
backend/tests/      24 pytest tests
flutter_app/        setup.py + overlay/ (Dart sources, MainActivity.kt.template)
```
