# ADR-0003: Use graph features, and keep the background acyclic

* Status: accepted
* Date: 2026-03-03

## Context

Laundering shows up in the shape of the money flow, so we need graph features (cycles,
fan-in/out, PageRank). But a random background graph is full of short cycles, which would make
the cycle signal flag everyone.

## Decision

We compute graph features on a transaction graph, and we build the synthetic background as a
payment flow (payers → merchants), which is acyclic. Amounts are varied so a normal merchant
is not confused with a structuring collector.

## Consequences

* **Good:** the cycle signal is clean (a cycle is a real signal), and the typologies separate
  well. The features reflect the real structure of laundering.
* **Cost:** the background is simpler than real traffic. Real data has legitimate cycles
  (refunds, exchanges), so the cycle rule there needs more care; the README documents it.

## Update (2026-10-09): realistic confounders added

The original "clean, acyclic background" made the typologies separate *too* well — the
detector scored a perfect 1.0, which is a symptom of a toy dataset, not a good model. The
background is now deliberately **realistically hard**: alongside the mostly-acyclic payment
flow it contains legitimate accounts that trip the same signatures as laundering — payment
intermediaries and money-services businesses (pass-through, like layering), **refund loops**
(A → B → A, benign cycles, like round-tripping), payroll runs (fan-out), popular merchants
(fan-in), and sub-threshold vendors (like structuring). These are label 0, so they apply
genuine false-positive pressure. As a result `in_cycle` is now an *ambiguous* signal rather
than a giveaway, and the measured precision/recall are realistic (~0.95 / ~0.99 on unseen
graphs, not 1.0). See `chainsentinel/evaluate.py` for the leakage-aware, multi-graph protocol
that proves the detector generalises rather than memorising one graph.
