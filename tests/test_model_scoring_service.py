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


def test_rule_score_grows_with_evidence():
    assert rule_score([]) == 0.0
    one = [TypologyHit(name="structuring", detail="x", severity=0.9)]
    two = one + [TypologyHit(name="layering", detail="y", severity=0.8)]
    assert 0.0 < rule_score(one) < rule_score(two) <= 1.0


def test_combined_score_is_noisy_or_not_a_diluting_average():
    """The fusion must never dilute a confident signal below either source.

    This is the regression guard for the fusion bug: a weighted average of a
    0.9 model score and a 0.0 rule score collapses to ~0.45 and the account
    falls under the alert threshold, so real laundering would be missed. A
    noisy-OR keeps it at 0.9. Mutating ``combined_score`` back to a weighted
    average makes the first assertion fail.
    """
    # A confident model score with no rule hit stays confident (not halved).
    assert combined_score(0.9, []) == 0.9
    # A strong rule with a silent model still raises the account.
    strong = [TypologyHit(name="structuring", detail="x", severity=0.9)]
    assert combined_score(0.0, strong) == rule_score(strong) > 0.0
    # Noisy-OR is always at least the max of the two sources, and bounded by 1.
    for ml in (0.0, 0.3, 0.7, 0.95):
        for hits in ([], strong):
            fused = combined_score(ml, hits)
            assert max(ml, rule_score(hits)) - 1e-9 <= fused <= 1.0
    assert combined_score(0.0, []) == 0.0


def test_service_detects_laundering(service):
    result, suspicious = service.analyze_sample()
    flagged = {a.address for a in result.alerts}
    true_positives = len(flagged & suspicious)
    precision = true_positives / len(flagged)
    recall = true_positives / len(suspicious)
    # Honest floors below the measured operating point (P~0.92, R~1.0 on this
    # graph): recall is the binding constraint for AML, precision stays high
    # despite the legitimate confounders designed to draw false positives.
    assert recall >= 0.95
    assert precision >= 0.85
    # alerts are sorted by score, highest first
    scores = [a.score for a in result.alerts]
    assert scores == sorted(scores, reverse=True)


def test_service_reports(service):
    result, _ = service.analyze_sample(with_reports=True)
    assert result.alerts[0].report
    assert "SUSPICIOUS ACTIVITY REPORT" in result.alerts[0].report
