"""Fine-tune a sequence-classification model for the text arm.   *** NOT TESTED in the build environment ***
(it needs a Hugging Face download, which was not available there; run it on Colab/GPU and check the output).

Why this is needed: a pretrained MentalBERT checkpoint is a masked language model (fill-mask). It has no
classification head, so it cannot output a risk probability until you fine-tune it on labelled text.
MentalBERT repos are gated on Hugging Face: request access and log in (`huggingface-cli login`) first.
Check each model's licence (the AIMH MentalBERT repos list cc-by-nc-4.0) before using it.

Input CSV: columns `text` and `label` (0 = not at risk, 1 = at risk). You must supply a labelled dataset
(your own annotated pilot text and/or a public dataset whose licence you have checked).

Usage:
  pip install transformers torch
  python scripts/finetune_text_model.py labelled.csv --base distilbert-base-uncased --out data/text_model
  export TRANSFORMER_MODEL_DIR=data/text_model     # backend now uses it (label index 1 = at risk)
"""
import argparse

import pandas as pd
import torch
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          Trainer, TrainingArguments)

ap = argparse.ArgumentParser()
ap.add_argument("csv")
ap.add_argument("--base", default="distilbert-base-uncased")
ap.add_argument("--out", default="data/text_model")
ap.add_argument("--epochs", type=int, default=3)
a = ap.parse_args()

df = pd.read_csv(a.csv).dropna(subset=["text", "label"])
tr, te = train_test_split(df, test_size=0.2, random_state=42, stratify=df["label"])
tok = AutoTokenizer.from_pretrained(a.base)
model = AutoModelForSequenceClassification.from_pretrained(a.base, num_labels=2)


class DS(torch.utils.data.Dataset):
    def __init__(self, frame):
        self.enc = tok(list(frame["text"]), truncation=True, padding=True, max_length=256)
        self.labels = list(frame["label"].astype(int))

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, i):
        item = {k: torch.tensor(v[i]) for k, v in self.enc.items()}
        item["labels"] = torch.tensor(self.labels[i])
        return item


trainer = Trainer(model=model,
                  args=TrainingArguments(output_dir=a.out + "_ckpt", num_train_epochs=a.epochs,
                                         per_device_train_batch_size=16, report_to=[]),
                  train_dataset=DS(tr))
trainer.train()
pred = trainer.predict(DS(te)).predictions.argmax(-1)
true = list(te["label"].astype(int))
print("held-out accuracy:", accuracy_score(true, pred), " F1:", f1_score(true, pred))
trainer.save_model(a.out)
tok.save_pretrained(a.out)
print("saved to", a.out)
