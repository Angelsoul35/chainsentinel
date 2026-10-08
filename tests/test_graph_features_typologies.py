from __future__ import annotations

import pandas as pd

from chainsentinel.features import FEATURE_COLUMNS, build_features
from chainsentinel.generate import make_transactions
from chainsentinel.typologies import detect_typologies


def test_generate_has_suspicious_accounts():
    txs, suspicious = make_transactions(seed=42)
    assert len(txs) > 500
    assert "laund_collector" in suspicious
    assert {"cycle_a", "cycle_b", "cycle_c"} <= suspicious


def test_features_columns_and_cycle_signal(sample):
    txs, _ = sample
    feat = build_features(txs)
    for col in FEATURE_COLUMNS:
        assert col in feat.columns
    # the injected cycle is flagged; the (acyclic) background is not
    assert feat.loc["cycle_a"]["in_cycle"] == 1
    normal = [a for a in feat.index if a.startswith("acct_")]
    assert feat.loc[normal]["in_cycle"].mean() < 0.05


def test_collector_has_structuring_signal(sample):
    txs, _ = sample
    feat = build_features(txs)
    assert feat.loc["laund_collector"]["pct_in_under_threshold"] >= 0.9


def test_detect_typologies_rules():
    structuring = pd.Series(
        {
            "pct_in_under_threshold": 0.9,
            "in_count": 10,
            "pct_out_under_threshold": 0.0,
            "out_count": 1,
            "unique_out": 1,
            "passthrough_ratio": 0.2,
            "total_in": 50000,
            "in_cycle": 0,
            "unique_in": 10,
            "total_out": 0,
        }
    )
    names = {h.name for h in detect_typologies(structuring)}
    assert "structuring" in names

    cycle = pd.Series(
        {
            "pct_in_under_threshold": 0.0,
            "in_count": 2,
            "pct_out_under_threshold": 0.0,
            "out_count": 2,
            "unique_out": 1,
            "passthrough_ratio": 0.95,
            "total_in": 100000,
            "in_cycle": 1,
            "unique_in": 1,
            "total_out": 95000,
        }
    )
    names = {h.name for h in detect_typologies(cycle)}
    assert "round_tripping" in names and "layering" in names
