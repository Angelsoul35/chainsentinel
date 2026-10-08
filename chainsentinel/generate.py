"""Synthetic on-chain transactions with known money-laundering patterns.

Everything is synthetic. Most accounts just send money around at random (the
background). On top of that we inject four classic laundering typologies from the
FATF playbook, and we remember which accounts take part, so we can measure how
well detection works:

* **Structuring (smurfing):** many deposits just under the reporting threshold,
  funnelled into one collector.
* **Layering:** a lump of money moved fast through a chain of accounts to hide its
  origin.
* **Round-tripping (cycle):** money that leaves and comes back (A -> B -> C -> A).
* **Fan-out (distribution):** one account splitting money to many.
"""

from __future__ import annotations

import numpy as np


def make_transactions(
    n_normal: int = 120,
    seed: int = 42,
    structuring_threshold: float = 10_000.0,
) -> tuple[list[dict], set[str]]:
    """Return (transactions, suspicious_addresses)."""
    rng = np.random.default_rng(seed)
    txs: list[dict] = []
    suspicious: set[str] = set()
    counter = {"n": 0}

    def tx(src: str, dst: str, amount: float, t: int) -> None:
        counter["n"] += 1
        txs.append(
            {"tx_id": f"tx_{counter['n']:06d}", "src": src, "dst": dst,
             "amount": round(float(amount), 2), "timestamp": int(t)}
        )

    normal = [f"acct_{i:04d}" for i in range(n_normal)]

    # Background activity is a payment flow: payers pay merchants. Keeping it
    # (mostly) payer -> merchant makes the background acyclic, so a cycle is a
    # real signal and does not drown in random loops. Amounts are varied, so a
    # normal merchant is not confused with a structuring collector.
    half = n_normal // 2
    payers, merchants = normal[:half], normal[half:]
    for _ in range(n_normal * 5):
        a = str(rng.choice(payers))
        b = str(rng.choice(merchants))
        tx(a, b, float(rng.uniform(100, 25_000)), int(rng.integers(0, 2000)))

    # --- Structuring: many mules deposit just under the threshold to a collector.
    collector = "laund_collector"
    suspicious.add(collector)
    mules = [f"mule_{i:03d}" for i in range(12)]
    for mule in mules:
        suspicious.add(mule)
        for _ in range(int(rng.integers(3, 7))):
            amount = structuring_threshold * rng.uniform(0.85, 0.99)
            tx(mule, collector, amount, int(rng.integers(100, 300)))
    # The collector then forwards the pooled funds onward.
    tx(collector, "laund_exit_1", 400_000, 320)

    # --- Layering: a lump moved fast through a chain.
    chain = [f"layer_{i:02d}" for i in range(6)]
    for node in chain:
        suspicious.add(node)
    amount = 300_000.0
    t = 500
    tx("acct_0001", chain[0], amount, t)
    for i in range(len(chain) - 1):
        amount *= rng.uniform(0.95, 0.99)
        t += int(rng.integers(1, 3))  # moves fast
        tx(chain[i], chain[i + 1], amount, t)
    tx(chain[-1], "laund_exit_2", amount * 0.98, t + 2)

    # --- Round-tripping cycle: A -> B -> C -> A.
    cycle = ["cycle_a", "cycle_b", "cycle_c"]
    for node in cycle:
        suspicious.add(node)
    amount, t = 150_000.0, 800
    for i in range(len(cycle)):
        tx(cycle[i], cycle[(i + 1) % len(cycle)], amount * rng.uniform(0.97, 1.0), t + i)

    # --- Fan-out: a distributor splits money to many accounts.
    distributor = "laund_distributor"
    suspicious.add(distributor)
    tx("acct_0002", distributor, 500_000, 1000)
    for i in range(20):
        tx(distributor, f"fanout_{i:03d}", float(rng.uniform(15_000, 30_000)),
           int(rng.integers(1001, 1010)))

    rng.shuffle(txs)
    return txs, suspicious
