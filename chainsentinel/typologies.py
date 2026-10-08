"""FATF-style typology rules.

These are the explainable, rule-based signals a compliance analyst would
recognise. They run on the per-account features and return a list of typology
hits. The ML model adds a learned score on top; the rules make each alert
explainable.
"""

from __future__ import annotations

import pandas as pd

from .schema import TypologyHit


def detect_typologies(row: pd.Series) -> list[TypologyHit]:
    hits: list[TypologyHit] = []

    if row["pct_in_under_threshold"] >= 0.6 and row["in_count"] >= 5:
        hits.append(
            TypologyHit(
                name="structuring",
                detail=(
                    f"{row['pct_in_under_threshold']:.0%} of {int(row['in_count'])} deposits "
                    "sit just under the reporting threshold"
                ),
                severity=0.9,
            )
        )

    if row["pct_out_under_threshold"] >= 0.6 and row["out_count"] >= 3 and row["unique_out"] <= 2:
        hits.append(
            TypologyHit(
                name="structuring_source",
                detail=(
                    f"sends {row['pct_out_under_threshold']:.0%} of {int(row['out_count'])} "
                    "transfers just under the threshold to few accounts (likely a mule)"
                ),
                severity=0.7,
            )
        )

    if row["passthrough_ratio"] >= 0.8 and row["total_in"] > 10_000:
        hits.append(
            TypologyHit(
                name="layering",
                detail=f"pass-through ratio {row['passthrough_ratio']:.2f}; funds moved on quickly",
                severity=0.8,
            )
        )

    if int(row["in_cycle"]) == 1:
        hits.append(
            TypologyHit(
                name="round_tripping",
                detail="account takes part in a transaction cycle (money returns to its origin)",
                severity=0.7,
            )
        )

    if row["unique_out"] >= 10 and row["unique_in"] <= 2:
        hits.append(
            TypologyHit(
                name="fan_out",
                detail=f"distributes to {int(row['unique_out'])} accounts from "
                f"{int(row['unique_in'])} source(s)",
                severity=0.7,
            )
        )

    if row["unique_in"] >= 8 and row["unique_out"] <= 2 and row["total_out"] > 0:
        hits.append(
            TypologyHit(
                name="fan_in",
                detail=f"collects from {int(row['unique_in'])} accounts and forwards the funds",
                severity=0.6,
            )
        )

    return hits
