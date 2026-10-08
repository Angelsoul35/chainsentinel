"""ChainSentinel command-line interface."""

from __future__ import annotations

import argparse

import numpy as np

from .config import get_settings
from .features import build_features
from .generate import make_transactions
from .model import SuspicionModel
from .service import AnalyzeService


def cmd_train(args) -> None:
    settings = get_settings()
    txs, suspicious = make_transactions(
        seed=42, structuring_threshold=settings.structuring_threshold
    )
    features = build_features(txs, settings.structuring_threshold)
    labels = np.array([a in suspicious for a in features.index], dtype=int)
    model = SuspicionModel()
    report = model.train(features, labels)
    path = model.save(settings.model_dir)
    print(f"version {report.version}  metrics {report.metrics}  -> {path}")


def cmd_demo(args) -> None:
    settings = get_settings()
    print("1) Training the suspicion model on a labelled synthetic graph ...")
    service = AnalyzeService(settings=settings, train_params={"n_estimators": 150})
    print(f"   model {service.model.version}  metrics {service.model.metadata['metrics']}")

    print("2) Analyzing a fresh transaction graph ...")
    result, suspicious = service.analyze_sample(with_reports=True)
    flagged = {a.address for a in result.alerts}
    tp = len(flagged & suspicious)
    precision = tp / len(flagged) if flagged else 0.0
    recall = tp / len(suspicious) if suspicious else 0.0
    print(f"   {result.n_transactions} transactions, {result.n_accounts} accounts, "
          f"{len(result.alerts)} alerts")
    print(f"   precision {precision:.2f}  recall {recall:.2f} (vs known labels)")

    print("\n3) Top alerts:")
    for alert in result.alerts[:6]:
        names = ", ".join(h.name for h in alert.typologies) or "model-only"
        print(f"   {alert.address:18s} score={alert.score:.2f}  typologies=[{names}]")

    top = result.alerts[0] if result.alerts else None
    if top and top.report:
        print("\n4) Example SAR narrative:")
        print(top.report)


def main() -> None:
    parser = argparse.ArgumentParser(description="ChainSentinel CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("train", help="train and save the model")
    p.set_defaults(func=cmd_train)
    p = sub.add_parser("demo", help="train, analyze, and show alerts")
    p.set_defaults(func=cmd_demo)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
