"""Per-account features from the transaction graph.

Each account gets a row of features that describe how it moves money: how much
comes in and goes out, whether it is a pass-through, whether its deposits sit
just under the reporting threshold, how fast money leaves after it arrives, and
its place in the graph (PageRank, clustering, being in a short cycle). These are
the signals both the rules and the ML model use.
"""

from __future__ import annotations

import itertools

import networkx as nx
import numpy as np
import pandas as pd

from .graph import build_multigraph, collapse_weighted

FEATURE_COLUMNS = [
    "in_count",
    "out_count",
    "total_in",
    "total_out",
    "net_flow",
    "passthrough_ratio",
    "unique_in",
    "unique_out",
    "avg_in",
    "std_in",
    "pct_in_under_threshold",
    "pct_out_under_threshold",
    "turnover_gap",
    "pagerank",
    "clustering",
    "in_cycle",
]


def _cycle_nodes(weighted: nx.DiGraph, length_bound: int = 5, max_cycles: int = 3000) -> set[str]:
    nodes: set[str] = set()
    try:
        cycles = itertools.islice(nx.simple_cycles(weighted, length_bound=length_bound), max_cycles)
        for cycle in cycles:
            nodes.update(cycle)
    except Exception:  # pragma: no cover - defensive for odd graphs
        pass
    return nodes


def build_features(
    transactions: list[dict], structuring_threshold: float = 10_000.0
) -> pd.DataFrame:
    df = pd.DataFrame(transactions)
    accounts = sorted(set(df["src"]) | set(df["dst"]))

    in_grp = df.groupby("dst")["amount"]
    out_grp = df.groupby("src")["amount"]
    in_count = in_grp.count()
    in_sum = in_grp.sum()
    in_mean = in_grp.mean()
    in_std = in_grp.std().fillna(0.0)
    out_count = out_grp.count()
    out_sum = out_grp.sum()

    in_time = df.groupby("dst")["timestamp"].mean()
    out_time = df.groupby("src")["timestamp"].mean()
    unique_in = df.groupby("dst")["src"].nunique()
    unique_out = df.groupby("src")["dst"].nunique()

    lo, hi = 0.8 * structuring_threshold, structuring_threshold
    df_under = df.assign(_u=((df["amount"] >= lo) & (df["amount"] < hi)).astype(int))
    pct_under = df_under.groupby("dst")["_u"].mean()
    pct_out_under = df_under.groupby("src")["_u"].mean()

    weighted = collapse_weighted(build_multigraph(transactions))
    pagerank = nx.pagerank(weighted, weight="weight") if weighted.number_of_nodes() else {}
    clustering = nx.clustering(weighted.to_undirected())
    cycle_nodes = _cycle_nodes(weighted)

    rows = []
    for acc in accounts:
        tin, tout = float(in_sum.get(acc, 0.0)), float(out_sum.get(acc, 0.0))
        passthrough = min(tin, tout) / max(tin, tout) if max(tin, tout) > 0 else 0.0
        gap = (
            float(out_time.get(acc, 0.0) - in_time.get(acc, 0.0))
            if (acc in out_time.index and acc in in_time.index)
            else 0.0
        )
        rows.append(
            {
                "address": acc,
                "in_count": int(in_count.get(acc, 0)),
                "out_count": int(out_count.get(acc, 0)),
                "total_in": tin,
                "total_out": tout,
                "net_flow": tin - tout,
                "passthrough_ratio": passthrough,
                "unique_in": int(unique_in.get(acc, 0)),
                "unique_out": int(unique_out.get(acc, 0)),
                "avg_in": float(in_mean.get(acc, 0.0)),
                "std_in": float(in_std.get(acc, 0.0)),
                "pct_in_under_threshold": float(pct_under.get(acc, 0.0)),
                "pct_out_under_threshold": float(pct_out_under.get(acc, 0.0)),
                "turnover_gap": gap,
                "pagerank": float(pagerank.get(acc, 0.0)),
                "clustering": float(clustering.get(acc, 0.0)),
                "in_cycle": int(acc in cycle_nodes),
            }
        )
    return pd.DataFrame(rows).set_index("address")


def features_matrix(features: pd.DataFrame) -> np.ndarray:
    return features[FEATURE_COLUMNS].to_numpy(dtype=float)
