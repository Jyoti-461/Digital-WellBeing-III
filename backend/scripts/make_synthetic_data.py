"""Generate SYNTHETIC screen-time data purely to test the training pipeline.

!!! Never report results from this data. It is random numbers with an arbitrary label rule. !!!
The real CSV comes from your pilot (GET /admin/export/checkins.csv joined with assessments).
"""
import argparse

import numpy as np
import pandas as pd

CATS = ["social_media", "entertainment", "gaming", "productivity", "education", "other"]

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=300)
ap.add_argument("--out", default="synthetic_screen_data.csv")
ap.add_argument("--seed", type=int, default=0)
a = ap.parse_args()

rng = np.random.default_rng(a.seed)
df = pd.DataFrame({c: np.clip(rng.gamma(2.0, s, a.n), 0, 12) for c, s in
                   zip(CATS, [1.2, 1.4, 0.8, 2.0, 1.5, 0.7])})
# arbitrary rule, only so the two classes exist: more recreational time => label 1
score = df.social_media + df.entertainment + df.gaming + rng.normal(0, 1.0, a.n)
df["label"] = (score > score.median()).astype(int)
df.to_csv(a.out, index=False)
print(f"wrote {a.n} SYNTHETIC rows to {a.out}")
