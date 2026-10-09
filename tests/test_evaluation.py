"""Tests that prove the detector *generalises* and is not a toy that scores 1.0.

These are the regression guards for the overfitting fix. They train on one graph
and measure on graphs the model never saw, so they fail both ways: if someone
re-introduces trivially separable data the confounder checks break, and if
someone cripples the detector (over-conservative threshold, diluting fusion) the
recall/precision floors break.
"""

from __future__ import annotations

from chainsentinel.evaluate import evaluate
from chainsentinel.generate import make_transactions

_FAST = {"n_estimators": 120}


def test_detector_generalises_to_unseen_graphs():
    report = evaluate(test_seeds=(777, 888), params=_FAST)

    mean_recall, _ = report.mean_std("recall")
    mean_precision, _ = report.mean_std("precision")
    mean_roc, _ = report.mean_std("roc_auc")

    # Strong detection on graphs never used for training or threshold choice.
    assert mean_recall >= 0.9, f"recall collapsed on unseen graphs: {mean_recall}"
    assert mean_precision >= 0.8, f"too many false positives: {mean_precision}"
    assert mean_roc >= 0.9

    # The real overfitting check: performance must not fall off a cliff from the
    # training graph to the independent graphs. A memorising model would show a
    # large positive gap; a healthy one stays close to zero.
    assert abs(report.generalisation_gap()) < 0.15, report.generalisation_gap()


def test_confounders_exist_and_are_not_labelled_suspicious():
    """The legitimate-but-suspicious-looking accounts must be present and unlabelled.

    They are what make the problem non-trivial. If someone removed them (making
    the data trivially separable again) or mislabelled them as suspicious (making
    recall look free), this fails.
    """
    txs, suspicious = make_transactions(seed=42)
    addresses = {t["src"] for t in txs} | {t["dst"] for t in txs}

    for prefix in ("acct_msb_", "acct_intermediary_", "acct_vendor_"):
        present = {a for a in addresses if a.startswith(prefix)}
        assert present, f"missing confounder family {prefix}"
        assert present.isdisjoint(suspicious), f"{prefix} must be label 0, not suspicious"


def test_false_positives_concentrate_on_hard_confounders_not_plain_accounts():
    """Ordinary accounts are almost never flagged; errors fall on the hard cases.

    The false positives should be the genuinely ambiguous confounders (money-
    services businesses, intermediaries), not the plain background accounts. If
    the detector started firing indiscriminately, the plain-account false-positive
    rate would rise and this would fail.
    """
    report = evaluate(test_seeds=(777,), params=_FAST)
    fp_by_kind = report.test_graphs[0].fp_by_kind
    plain_fps = fp_by_kind.get("plain account", 0)
    assert plain_fps <= 1, f"detector fires on ordinary accounts: {fp_by_kind}"
