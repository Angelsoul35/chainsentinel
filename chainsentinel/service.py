"""Orchestration: build graph features, score, apply rules, raise alerts."""

from __future__ import annotations

import numpy as np

from .config import Settings, get_settings
from .features import build_features
from .generate import make_transactions
from .llm import LLMClient
from .model import SuspicionModel, latest_version
from .report import build_report
from .schema import Alert, AnalysisResult
from .scoring import combined_score
from .typologies import detect_typologies

_ALERT_FEATURE_KEYS = [
    "total_in",
    "total_out",
    "in_count",
    "unique_in",
    "unique_out",
    "pct_in_under_threshold",
    "passthrough_ratio",
    "in_cycle",
]


class AnalyzeService:
    def __init__(
        self,
        settings: Settings | None = None,
        model: SuspicionModel | None = None,
        llm: LLMClient | None = None,
        train_params: dict | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm = llm
        self.model = model or self._load_or_train(train_params)

    def _load_or_train(self, params: dict | None) -> SuspicionModel:
        if latest_version(self.settings.model_dir) is not None:
            return SuspicionModel.load(self.settings.model_dir)
        txs, suspicious = make_transactions(
            seed=42, structuring_threshold=self.settings.structuring_threshold
        )
        features = build_features(txs, self.settings.structuring_threshold)
        labels = np.array([addr in suspicious for addr in features.index], dtype=int)
        model = SuspicionModel(params or {})
        model.train(features, labels)
        return model

    def model_info(self) -> dict:
        return {"version": self.model.version, "metadata": self.model.metadata}

    def analyze(
        self, transactions: list[dict], with_reports: bool = False, max_reports: int = 5
    ) -> AnalysisResult:
        features = build_features(transactions, self.settings.structuring_threshold)
        ml_scores = self.model.score(features)

        alerts: list[Alert] = []
        for i, (address, row) in enumerate(features.iterrows()):
            hits = detect_typologies(row)
            score = combined_score(float(ml_scores[i]), hits)
            if score >= self.settings.alert_threshold:
                alerts.append(
                    Alert(
                        address=str(address),
                        score=score,
                        ml_score=round(float(ml_scores[i]), 4),
                        typologies=hits,
                        features={k: round(float(row[k]), 4) for k in _ALERT_FEATURE_KEYS},
                    )
                )
        alerts.sort(key=lambda a: a.score, reverse=True)

        if with_reports:
            for alert in alerts[:max_reports]:
                alert.report = build_report(
                    alert,
                    mode=self.settings.report_mode,
                    llm=self.llm,
                    provider_spec=self.settings.llm_providers,
                )

        return AnalysisResult(
            n_accounts=len(features), n_transactions=len(transactions), alerts=alerts
        )

    def analyze_sample(self, with_reports: bool = False) -> tuple[AnalysisResult, set[str]]:
        """Analyze the built-in synthetic dataset; also return the true labels."""
        txs, suspicious = make_transactions(
            seed=7, structuring_threshold=self.settings.structuring_threshold
        )
        return self.analyze(txs, with_reports=with_reports), suspicious
