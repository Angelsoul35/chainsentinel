"""The ML model: a random forest that scores how suspicious an account is.

It learns from the features of known-suspicious and normal accounts. It is the
learned half of the system; the typology rules are the explainable half. The
final alert score combines the two.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from .features import FEATURE_COLUMNS

_DEFAULT_PARAMS: dict[str, Any] = {
    "n_estimators": 200,
    "max_depth": None,
    "min_samples_leaf": 2,
    "class_weight": "balanced",
    "random_state": 42,
    "n_jobs": 1,
}


@dataclass
class TrainingReport:
    version: str
    trained_at: str
    n_accounts: int
    metrics: dict[str, float]


class SuspicionModel:
    def __init__(self, params: dict[str, Any] | None = None) -> None:
        self.params = {**_DEFAULT_PARAMS, **(params or {})}
        self.model: RandomForestClassifier | None = None
        self.version: str | None = None
        self.metadata: dict[str, Any] = {}

    def train(self, features: pd.DataFrame, labels: np.ndarray) -> TrainingReport:
        X = features[FEATURE_COLUMNS].to_numpy(dtype=float)
        y = np.asarray(labels).astype(int)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, stratify=y, random_state=42
        )
        self.model = RandomForestClassifier(**self.params)
        self.model.fit(X_train, y_train)

        proba = self.model.predict_proba(X_test)[:, 1]
        pred = (proba >= 0.5).astype(int)
        metrics = {
            "precision": round(float(precision_score(y_test, pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, pred, zero_division=0)), 4),
            "roc_auc": round(float(roc_auc_score(y_test, proba)), 4),
        }
        payload = json.dumps({"params": self.params, "features": FEATURE_COLUMNS}, sort_keys=True)
        self.version = "m_" + hashlib.sha256(payload.encode()).hexdigest()[:12]
        self.metadata = {
            "version": self.version,
            "trained_at": datetime.now(UTC).isoformat(),
            "n_accounts": int(len(features)),
            "metrics": metrics,
            "params": self.params,
        }
        return TrainingReport(self.version, self.metadata["trained_at"], len(features), metrics)

    def score(self, features: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("model is not trained or loaded")
        X = features[FEATURE_COLUMNS].to_numpy(dtype=float)
        return self.model.predict_proba(X)[:, 1]

    def save(self, model_dir: str | Path) -> Path:
        if self.model is None or self.version is None:
            raise RuntimeError("nothing to save; train first")
        target = Path(model_dir) / self.version
        target.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, target / "model.joblib")
        (target / "metadata.json").write_text(json.dumps(self.metadata, indent=2))
        return target

    @classmethod
    def load(cls, model_dir: str | Path, version: str | None = None) -> SuspicionModel:
        base = Path(model_dir)
        resolved = version or latest_version(base)
        if resolved is None:
            raise FileNotFoundError(f"no trained model under {base}")
        path = base / resolved
        obj = cls()
        obj.model = joblib.load(path / "model.joblib")
        obj.metadata = json.loads((path / "metadata.json").read_text())
        obj.version = obj.metadata["version"]
        obj.params = obj.metadata.get("params", obj.params)
        return obj


def latest_version(model_dir: str | Path) -> str | None:
    base = Path(model_dir)
    if not base.exists():
        return None
    candidates = [p for p in base.iterdir() if p.is_dir() and (p / "metadata.json").exists()]
    if not candidates:
        return None
    candidates.sort(key=lambda p: json.loads((p / "metadata.json").read_text())["trained_at"])
    return candidates[-1].name
