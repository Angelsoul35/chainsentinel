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
  (refunds, exchanges), so the cycle rule there needs more care; the README is honest about it.
