"""Central configuration. Everything tunable lives here or in environment variables.

IMPORTANT: values marked PLACEHOLDER are starting points, not validated findings.
They must be calibrated against the PHQ-9 / GAD-7 / PSS data collected in the pilot.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.environ.get("WELLBEING_DB", str(BASE_DIR / "wellbeing.db"))

# --- Screen-time thresholds (hours/day) -- taken from Table I of the project paper ---
CATEGORIES = ["social_media", "entertainment", "gaming", "productivity", "education", "other"]
CATEGORY_LABELS = {
    "social_media": "Social Media",
    "entertainment": "Entertainment",
    "gaming": "Gaming",
    "productivity": "Productivity",
    "education": "Education",
    "other": "Other",
}
THRESHOLDS_HOURS = {
    "social_media": 2.0,
    "entertainment": 3.0,
    "gaming": 2.0,
    "productivity": 6.0,
    "education": 4.0,
    "other": 2.0,
}
TOTAL_DAILY_THRESHOLD_HOURS = 8.0

# --- Fusion --- initial weights from the paper (0.6 text / 0.4 behaviour); to be tuned.
W_TEXT = float(os.environ.get("W_TEXT", "0.6"))
W_BEHAVIOR = float(os.environ.get("W_BEHAVIOR", "0.4"))

# PLACEHOLDER tier cut-offs for the fused 0-1 score. Calibrate against PHQ-9/GAD-7/PSS.
TIER_MODERATE = float(os.environ.get("TIER_MODERATE", "0.35"))
TIER_HIGH = float(os.environ.get("TIER_HIGH", "0.60"))

# --- Text validation (paper: valid text is "> 3 words") ---
MIN_WORDS = 4
MAX_TEXT_CHARS = 2000

# --- Optional trained models (produced by the scripts/ folder; absent by default) ---
SCREEN_MODEL_PATH = os.environ.get("SCREEN_MODEL_PATH", str(BASE_DIR / "data" / "screen_rf.joblib"))
# Directory of a *fine-tuned sequence-classification* model. Leave unset to use VADER only.
TRANSFORMER_MODEL_DIR = os.environ.get("TRANSFORMER_MODEL_DIR", "")
# Index of the "at-risk" class in that model's output.
TRANSFORMER_RISK_LABEL_INDEX = int(os.environ.get("TRANSFORMER_RISK_LABEL_INDEX", "1"))

# --- Auth / admin ---
SESSION_DAYS = 30
PBKDF2_ITERATIONS = 200_000
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")  # empty => admin endpoints disabled

# --- Help resources shown when crisis language is detected (verify before deployment) ---
HELPLINES = [
    {
        "name": "Tele-MANAS (Govt. of India, 24x7, free)",
        "numbers": ["14416", "1-800-891-4416"],
    }
]
