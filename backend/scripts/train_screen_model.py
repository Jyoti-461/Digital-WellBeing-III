"""Train the Random Forest behaviour arm from real pilot data.

Input CSV columns: social_media, entertainment, gaming, productivity, education, other (hours/day)
and `label` (0/1). YOU decide what label means and document it in the paper, e.g.
label = 1 when PHQ-9 >= 10 (or GAD-7 >= 10, or PSS-10 >= 27) in the same period.
Settings mirror the paper: 50 trees, random_state=42, 70/30 split.

Output: data/screen_rf.joblib  ({"model": ..., "features": [...]}) which the API loads automatically
(set SCREEN_MODEL_PATH to change the location).
"""
import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

FEATURES = ["social_media", "entertainment", "gaming", "productivity", "education", "other"]

ap = argparse.ArgumentParser()
ap.add_argument("csv")
ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "data" / "screen_rf.joblib"))
a = ap.parse_args()

df = pd.read_csv(a.csv)
missing = [c for c in FEATURES + ["label"] if c not in df.columns]
if missing:
    raise SystemExit(f"CSV is missing columns: {missing}")
if df["label"].nunique() < 2:
    raise SystemExit("label has only one class; need both 0 and 1 to train")

X, y = df[FEATURES], df["label"].astype(int)
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.30, random_state=42, stratify=y)
clf = RandomForestClassifier(n_estimators=50, random_state=42).fit(Xtr, ytr)
pred = clf.predict(Xte)
print(f"test rows: {len(yte)}")
print(f"accuracy : {accuracy_score(yte, pred):.3f}")
print(f"precision: {precision_score(yte, pred, zero_division=0):.3f}")
print(f"recall   : {recall_score(yte, pred, zero_division=0):.3f}")
joblib.dump({"model": clf, "features": FEATURES}, a.out)
print("saved", a.out)
