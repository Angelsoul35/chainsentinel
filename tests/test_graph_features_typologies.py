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


def test_cycle_signal_flags_injected_cycle_but_is_not_a_giveaway(sample):
    txs, suspicious = sample
    feat = build_features(txs)
    for col in FEATURE_COLUMNS:
        assert col in feat.columns

    # The injected round-tripping cycle is detected.
    assert feat.loc["cycle_a"]["in_cycle"] == 1

    # But the benign refund loops (A -> B -> A) also create cycles, so being in a
    # cycle is an *ambiguous* signal, not a label: some legitimate background
    # accounts sit in cycles too. This is the false-positive pressure that stops
    # the round_tripping rule from being a free giveaway. If the refund-loop
    # confounders were removed, this list would be empty and the test would fail.
    benign_in_cycle = [
        a
        for a in feat.index
        if a.startswith("acct_") and a not in suspicious and feat.loc[a]["in_cycle"] == 1
    ]
    assert benign_in_cycle, "refund-loop confounders should put some benign accounts in cycles"

    # Yet cycles remain the exception in the plain background, not the rule.
    background = [a for a in feat.index if a.startswith("acct_")]
    assert feat.loc[background]["in_cycle"].mean() < 0.15


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
