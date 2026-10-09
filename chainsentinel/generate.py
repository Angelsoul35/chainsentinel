"""Synthetic on-chain transactions with known money-laundering patterns.

Everything is synthetic. The graph has three layers, built so that detection is
*realistically hard* rather than trivially separable:

1. **Plain background** — ordinary payer -> merchant payments.
2. **Legitimate confounders** — normal accounts that *look* suspicious: payment
   intermediaries that forward most of what they receive (high pass-through),
   refund loops (A -> B -> A), payroll accounts paying many employees (fan-out),
   popular merchants collecting from many payers (fan-in), and vendors that
   invoice just under the reporting threshold. These are **not** laundering, and
   they are what force a detector to weigh several signals instead of latching
   onto one. They are the realistic false-positive pressure a real AML system
   fights.
3. **Injected laundering** — four classic FATF typologies, deliberately made
   *subtle* (varied amounts, one-off mules, slower layering) so a share of them
   sit close to legitimate behaviour:

   * **Structuring (smurfing):** many deposits around the reporting threshold,
     funnelled into one collector.
   * **Layering:** a lump of money moved through a chain of accounts.
   * **Round-tripping (cycle):** money that leaves and comes back (A -> B -> C -> A).
   * **Fan-out (distribution):** one account splitting money to many.

Only the laundering accounts are labelled suspicious; the confounders are not, so
the measured precision and recall reflect the genuine difficulty of telling them
apart — not a toy that scores 1.0.
"""

from __future__ import annotations

import numpy as np


def make_transactions(
    n_normal: int = 140,
    seed: int = 42,
    structuring_threshold: float = 10_000.0,
) -> tuple[list[dict], set[str]]:
    """Return ``(transactions, suspicious_addresses)``.

    ``suspicious_addresses`` are the injected laundering accounts only. The
    legitimate confounders are intentionally excluded from the label set: a
    detector that flags them is making a *false positive*, which is the point.
    """
    rng = np.random.default_rng(seed)
    txs: list[dict] = []
    suspicious: set[str] = set()
    counter = {"n": 0}

    def tx(src: str, dst: str, amount: float, t: int) -> None:
        counter["n"] += 1
        txs.append(
            {
                "tx_id": f"tx_{counter['n']:06d}",
                "src": src,
                "dst": dst,
                "amount": round(float(amount), 2),
                "timestamp": int(t),
            }
        )

    normal = [f"acct_{i:04d}" for i in range(n_normal)]
    half = n_normal // 2
    payers, merchants = normal[:half], normal[half:]

    # --- Layer 1: plain background (payer -> merchant), varied amounts/times.
    for _ in range(n_normal * 5):
        a = str(rng.choice(payers))
        b = str(rng.choice(merchants))
        tx(a, b, float(rng.uniform(100, 25_000)), int(rng.integers(0, 2000)))

    # --- Layer 2: legitimate confounders (label 0, but superficially suspicious).

    # 2a. Payment intermediaries / escrow: collect from a handful of payers and
    #     forward most of it to a few destinations -> high pass-through ratio,
    #     exactly like a layering hop, but legitimate and recurring.
    for k in range(6):
        inter = f"acct_intermediary_{k:02d}"
        received = 0.0
        for _ in range(int(rng.integers(4, 9))):
            amt = float(rng.uniform(2_000, 20_000))
            received += amt
            tx(str(rng.choice(payers)), inter, amt, int(rng.integers(0, 2000)))
        # forward ~70-95% onward to 1-3 merchants (the rest is its margin)
        forward = received * rng.uniform(0.70, 0.95)
        dests = [str(rng.choice(merchants)) for _ in range(int(rng.integers(1, 4)))]
        for d in dests:
            tx(inter, d, forward / len(dests), int(rng.integers(2000, 2100)))

    # 2b. Refund loops: a merchant refunds a customer, so money comes back
    #     (A -> B -> A). A real, benign two-node cycle.
    for _ in range(5):
        cust = str(rng.choice(payers))
        merch = str(rng.choice(merchants))
        amt = float(rng.uniform(500, 8_000))
        t0 = int(rng.integers(0, 1900))
        tx(cust, merch, amt, t0)
        tx(merch, cust, amt * rng.uniform(0.9, 1.0), t0 + int(rng.integers(1, 40)))  # refund

    # 2c. Payroll: an employer pays many employees -> large fan-out, legitimate.
    for k in range(2):
        payroll = f"acct_payroll_{k:02d}"
        tx(str(rng.choice(payers)), payroll, 300_000.0, 950)  # gets funded
        for _ in range(int(rng.integers(14, 22))):
            tx(payroll, str(rng.choice(normal)), float(rng.uniform(2_000, 6_000)), 960)

    # 2d. Popular merchant: collects from many distinct payers -> large fan-in.
    for k in range(2):
        shop = f"acct_popular_{k:02d}"
        for _ in range(int(rng.integers(12, 20))):
            tx(
                str(rng.choice(payers)),
                shop,
                float(rng.uniform(1_000, 9_000)),
                int(rng.integers(0, 2000)),
            )

    # 2e. Sub-threshold vendor: invoices repeatedly just under the threshold
    #     (e.g. a contractor) -> looks like structuring, but is a single honest biller.
    for k in range(4):
        vendor = f"acct_vendor_{k:02d}"
        for _ in range(int(rng.integers(3, 7))):
            amt = structuring_threshold * rng.uniform(0.80, 0.98)
            tx(str(rng.choice(payers)), vendor, amt, int(rng.integers(0, 2000)))

    # 2f. Money-services businesses (the genuinely hard false positives). A legit
    #     MSB takes many sub-threshold deposits from clients AND forwards most of
    #     it onward quickly to a couple of settlement accounts -> it trips BOTH the
    #     structuring and the layering signatures at once, exactly as a collector
    #     would. Real AML systems false-positive on MSBs; so does any honest model.
    for k in range(4):
        msb = f"acct_msb_{k:02d}"
        received = 0.0
        for _ in range(int(rng.integers(6, 10))):
            amt = structuring_threshold * rng.uniform(0.70, 0.98)  # sub-threshold inflows
            received += amt
            tx(str(rng.choice(payers)), msb, amt, int(rng.integers(100, 400)))
        for _ in range(int(rng.integers(1, 3))):  # forward ~90% to few settlements
            tx(
                msb,
                str(rng.choice(merchants)),
                received * 0.9 / 2,
                int(rng.integers(400, 450)),
            )

    # --- Layer 3: injected laundering (label 1), made subtle.

    # 3a. Structuring: mules deposit *just under* the reporting threshold into a
    #     collector (the textbook signature). Counts vary and a few mules deposit
    #     only once, so a single one-off mule (in_count < 5) is not individually
    #     obvious to the structuring rule and must be caught, if at all, by the
    #     model. The sub-threshold band is shared with the legitimate vendors and
    #     MSBs above, which is what makes telling them apart hard.
    collector = "laund_collector"
    suspicious.add(collector)
    for i in range(12):
        mule = f"mule_{i:03d}"
        suspicious.add(mule)
        n_dep = 1 if i % 5 == 0 else int(rng.integers(2, 6))  # some one-off mules
        for _ in range(n_dep):
            amount = structuring_threshold * rng.uniform(0.80, 0.99)
            tx(mule, collector, amount, int(rng.integers(100, 400)))
    tx(collector, "laund_exit_1", 380_000, 420)  # collector forwards the pool

    # 3b. Layering: a lump through a chain; speed varies (some hops slower).
    chain = [f"layer_{i:02d}" for i in range(6)]
    for node in chain:
        suspicious.add(node)
    amount, t = 300_000.0, 500
    tx(str(rng.choice(payers)), chain[0], amount, t)
    for i in range(len(chain) - 1):
        amount *= rng.uniform(0.90, 0.99)
        t += int(rng.integers(1, 8))  # not always fast
        tx(chain[i], chain[i + 1], amount, t)
    tx(chain[-1], "laund_exit_2", amount * 0.97, t + int(rng.integers(1, 6)))

    # 3c. Round-tripping: money returns to its origin through intermediaries.
    cycle = ["cycle_a", "cycle_b", "cycle_c", "cycle_d"]
    for node in cycle:
        suspicious.add(node)
    amount, t = 150_000.0, 800
    for i in range(len(cycle)):
        tx(cycle[i], cycle[(i + 1) % len(cycle)], amount * rng.uniform(0.95, 1.0), t + i)

    # 3d. Fan-out: a distributor splits money to many; a few recipients also take
    #     in legitimate funds, blurring the picture.
    distributor = "laund_distributor"
    suspicious.add(distributor)
    tx(str(rng.choice(payers)), distributor, 450_000, 1000)
    for i in range(18):
        tx(
            distributor,
            f"fanout_{i:03d}",
            float(rng.uniform(12_000, 30_000)),
            int(rng.integers(1001, 1015)),
        )

    rng.shuffle(txs)
    return txs, suspicious
