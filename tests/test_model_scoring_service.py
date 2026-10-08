from __future__ import annotations

import numpy as np

from chainsentinel.features import build_features
from chainsentinel.model import SuspicionModel, latest_version
from chainsentinel.schema import TypologyHit
from chainsentinel.scoring import combined_score, rule_score


def test_model_trains_and_scores(sample, tmp_path):
    txs, suspicious = sample
    feat = build_features(txs)
    labels = np.array([a in suspicious for a in feat.index], dtype=int)
    model = SuspicionModel(params={"n_estimators": 120})
    report = model.train(feat, labels)
    assert report.metrics["roc_auc"] > 0.9
    scores = model.score(feat)
    assert ((scores >= 0) & (scores <= 1)).all()

    model.save(tmp_path)
    reloaded = SuspicionModel.load(tmp_path, model.version)
    assert reloaded.version == model.version
    assert latest_version(tmp_path) == model.version


def test_rule_and_combined_score():
    assert rule_score([]) == 0.0
    hits = [TypologyHit(name="structuring", detail="x", severity=0.9)]
    assert rule_score(hits) > 0
    assert combined_score(0.8, hits) <= 1.0
    assert combined_score(0.0, []) == 0.0


def test_service_detects_laundering(service):
    result, suspicious = service.analyze_sample()
    flagged = {a.address for a in result.alerts}
    true_positives = len(flagged & suspicious)
    precision = true_positives / len(flagged)
    recall = true_positives / len(suspicious)
    assert precision >= 0.9
    assert recall >= 0.6
    # alerts are sorted by score, highest first
    scores = [a.score for a in result.alerts]
    assert scores == sorted(scores, reverse=True)


def test_service_reports(service):
    result, _ = service.analyze_sample(with_reports=True)
    assert result.alerts[0].report
    assert "SUSPICIOUS ACTIVITY REPORT" in result.alerts[0].report
