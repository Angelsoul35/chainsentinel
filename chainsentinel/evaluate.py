"""Leakage-aware evaluation of the suspicion detector.

Each "example" in this problem is not a row but a *whole transaction graph*: the
per-account features (PageRank, clustering, cycle membership, pass-through) are
computed over the entire graph, so a node's features depend on its neighbours.
A plain row-wise train/test split would therefore leak — the test nodes' features
are shaped by the train nodes. The only trustworthy generalisation signal is
performance on graphs the model has **never seen**, so the protocol here is:

1. **Train** the detector on one graph (``train_seed``).
2. **Choose** the alert threshold on a separate **validation** graph
   (``val_seed``) — never on the test graphs.
3. **Report** precision / recall / F1 / ROC-AUC / PR-AUC on several independent
   **test** graphs (fresh seeds), as mean +/- std, next to the train-graph
   (resubstitution) score. The *gap* between them is the overfitting check: a
   detector that had memorised the training graph would collapse on the
   independent graphs; a small gap means it generalises.
4. **Error analysis** — break the false positives down by the kind of legitimate
   account they come from, so a reviewer can see that the misses are the
   genuinely hard confounders (money-services businesses that trip both the
   structuring and the layering signatures), not random noise.

Run it with ``python -m chainsentinel.evaluate``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    precision_recall_fscore_support,
    roc_auc_score,
)

from .features import build_features
from .generate import make_transactions
from .model import SuspicionModel
from .scoring import combined_score
from .typologies import detect_typologies

# Account-name prefixes -> the kind of (legitimate) account, for error analysis.
_CONFOUNDER_KINDS = {
    "acct_intermediary_": "payment intermediary",
    "acct_msb_": "money-services business",
    "acct_vendor_": "sub-threshold vendor",
    "acct_payroll_": "payroll",
    "acct_popular_": "popular merchant",
}


def _kind_of(address: str) -> str:
    for prefix, kind in _CONFOUNDER_KINDS.items():
        if address.startswith(prefix):
            return kind
    if address.startswith("acct_"):
        return "plain account"
    return "other"


@dataclass
class GraphMetrics:
    """Metrics for the detector on a single graph at a fixed threshold."""

    seed: int
    precision: float
    recall: float
    f1: float
    roc_auc: float
    pr_auc: float
    n_alerts: int
    true_positives: int
    false_positives: int
    false_negatives: int
    fp_by_kind: dict[str, int] = field(default_factory=dict)


@dataclass
class EvaluationReport:
    """The full evaluation: how it was trained, the chosen threshold, the gap."""

    train_seed: int
    val_seeds: tuple[int, ...]
    threshold: float
    train_graph: GraphMetrics
    test_graphs: list[GraphMetrics]

    def mean_std(self, attr: str) -> tuple[float, float]:
        vals = [getattr(g, attr) for g in self.test_graphs]
        return float(np.mean(vals)), float(np.std(vals))

    def generalisation_gap(self) -> float:
        """Train F1 minus the mean independent-test F1 (smaller is better)."""
        mean_test_f1, _ = self.mean_std("f1")
        return round(self.train_graph.f1 - mean_test_f1, 4)


def train_detector(train_seed: int = 42, params: dict | None = None) -> SuspicionModel:
    """Train the suspicion model on the graph generated with ``train_seed``."""
    txs, suspicious = make_transactions(seed=train_seed)
    feat = build_features(txs)
    labels = np.array([addr in suspicious for addr in feat.index], dtype=int)
    model = SuspicionModel(params or {"n_estimators": 200})
    model.train(feat, labels)
    return model


def fused_scores(model: SuspicionModel, feat) -> np.ndarray:
    """Noisy-OR fusion of the ML score and the typology rules, per account."""
    ml = model.score(feat)
    scores = [
        combined_score(float(ml[i]), detect_typologies(row))
        for i, (_addr, row) in enumerate(feat.iterrows())
    ]
    return np.asarray(scores, dtype=float)


def _graph_metrics(model: SuspicionModel, seed: int, threshold: float) -> GraphMetrics:
    txs, suspicious = make_transactions(seed=seed)
    feat = build_features(txs)
    y = np.array([addr in suspicious for addr in feat.index], dtype=int)
    scores = fused_scores(model, feat)
    pred = (scores >= threshold).astype(int)

    precision, recall, f1, _ = precision_recall_fscore_support(
        y, pred, average="binary", zero_division=0
    )
    roc = roc_auc_score(y, scores) if y.sum() and (y == 0).any() else float("nan")
    pr = average_precision_score(y, scores) if y.sum() else float("nan")

    fp_mask = (pred == 1) & (y == 0)
    fp_by_kind: dict[str, int] = {}
    for addr in feat.index[fp_mask]:
        kind = _kind_of(str(addr))
        fp_by_kind[kind] = fp_by_kind.get(kind, 0) + 1

    return GraphMetrics(
        seed=seed,
        precision=round(float(precision), 4),
        recall=round(float(recall), 4),
        f1=round(float(f1), 4),
        roc_auc=round(float(roc), 4),
        pr_auc=round(float(pr), 4),
        n_alerts=int(pred.sum()),
        true_positives=int(((pred == 1) & (y == 1)).sum()),
        false_positives=int(fp_mask.sum()),
        false_negatives=int(((pred == 0) & (y == 1)).sum()),
        fp_by_kind=dict(sorted(fp_by_kind.items(), key=lambda kv: -kv[1])),
    )


def choose_threshold(
    model: SuspicionModel,
    val_seeds: tuple[int, ...] = (123, 321, 456, 654),
    min_recall: float = 0.98,
) -> float:
    """Pick the threshold with the best precision while recall stays high.

    In AML a missed launderer is the expensive error, so recall is the binding
    constraint and precision is maximised underneath it. The threshold is chosen
    over *several* validation graphs (not one, which is noisy) and the recall
    floor is enforced on the **worst** validation graph, so the operating point
    is robust rather than lucky. The test graphs are never used here, so the
    reported test metrics stay honest.
    """
    val = []
    for seed in val_seeds:
        txs, suspicious = make_transactions(seed=seed)
        feat = build_features(txs)
        y = np.array([addr in suspicious for addr in feat.index], dtype=int)
        val.append((y, fused_scores(model, feat)))

    best_thr, best_precision = 0.5, -1.0
    for thr in np.round(np.arange(0.30, 0.96, 0.01), 2):
        precisions, recalls = [], []
        for y, scores in val:
            pred = (scores >= thr).astype(int)
            precision, recall, _, _ = precision_recall_fscore_support(
                y, pred, average="binary", zero_division=0
            )
            precisions.append(precision)
            recalls.append(recall)
        if min(recalls) >= min_recall and float(np.mean(precisions)) > best_precision:
            best_thr, best_precision = float(thr), float(np.mean(precisions))
    return best_thr


def evaluate(
    train_seed: int = 42,
    val_seeds: tuple[int, ...] = (123, 321, 456, 654),
    test_seeds: tuple[int, ...] = (777, 888, 999, 1234, 2024),
    threshold: float | None = None,
    params: dict | None = None,
) -> EvaluationReport:
    """Train, choose the threshold on validation, and score independent test graphs."""
    model = train_detector(train_seed, params)
    thr = threshold if threshold is not None else choose_threshold(model, val_seeds)
    train_metrics = _graph_metrics(model, train_seed, thr)
    test_metrics = [_graph_metrics(model, seed, thr) for seed in test_seeds]
    return EvaluationReport(
        train_seed=train_seed,
        val_seeds=val_seeds,
        threshold=thr,
        train_graph=train_metrics,
        test_graphs=test_metrics,
    )


def format_report(report: EvaluationReport) -> str:
    """A human-readable evaluation summary."""
    lines = [
        "ChainSentinel — generalisation evaluation",
        "=" * 48,
        f"train graph seed       : {report.train_seed}",
        f"validation graph seeds : {list(report.val_seeds)}  (threshold chosen here)",
        f"alert threshold        : {report.threshold:.2f}",
        "",
        "train graph (resubstitution — optimistic upper bound):",
        f"  P={report.train_graph.precision:.3f}  R={report.train_graph.recall:.3f}  "
        f"F1={report.train_graph.f1:.3f}  ROC-AUC={report.train_graph.roc_auc:.3f}  "
        f"PR-AUC={report.train_graph.pr_auc:.3f}",
        "",
        f"independent test graphs {[g.seed for g in report.test_graphs]} (never seen):",
    ]
    for metric in ("precision", "recall", "f1", "roc_auc", "pr_auc"):
        mean, std = report.mean_std(metric)
        lines.append(f"  {metric:<9}: {mean:.3f} +/- {std:.3f}")
    lines += [
        "",
        f"generalisation gap (train F1 - mean test F1): {report.generalisation_gap():.3f}",
        "  (small gap => the detector generalises, it did not memorise one graph)",
        "",
        "false positives by account kind (first test graph):",
    ]
    fp = report.test_graphs[0].fp_by_kind
    if fp:
        for kind, count in fp.items():
            lines.append(f"  {kind:<24}: {count}")
    else:
        lines.append("  (none)")
    return "\n".join(lines)


def main() -> None:  # pragma: no cover - CLI entry point
    print(format_report(evaluate()))


if __name__ == "__main__":  # pragma: no cover
    main()
