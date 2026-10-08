"""Build a transaction graph from a list of transactions.

Each account is a node; each transaction is a directed edge from sender to
receiver. We keep a MultiDiGraph (several transfers between the same pair are
separate edges) for behavioural features, and a collapsed weighted DiGraph for
graph metrics like PageRank.
"""

from __future__ import annotations

import networkx as nx


def build_multigraph(transactions: list[dict]) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    for tx in transactions:
        graph.add_edge(
            tx["src"],
            tx["dst"],
            key=tx["tx_id"],
            amount=float(tx["amount"]),
            timestamp=int(tx["timestamp"]),
        )
    return graph


def collapse_weighted(multigraph: nx.MultiDiGraph) -> nx.DiGraph:
    """Collapse parallel edges into a single weighted edge (sum of amounts)."""
    weighted = nx.DiGraph()
    for src, dst, data in multigraph.edges(data=True):
        amount = data["amount"]
        if weighted.has_edge(src, dst):
            weighted[src][dst]["weight"] += amount
        else:
            weighted.add_edge(src, dst, weight=amount)
    return weighted
