# Architecture

## Goal

Find money-laundering behaviour in a transaction graph, explain each alert, and keep a human
in the loop.

## Components

| Layer | Module | What it does |
|---|---|---|
| Data | `generate.py` | Synthetic transactions with injected typologies (+ labels) |
| Graph | `graph.py` | Build the transaction graph (NetworkX) |
| Features | `features.py` | Per-account graph and behavioral features |
| Rules | `typologies.py` | FATF-style typology rules |
| Model | `model.py` | Random forest suspicion score |
| Scoring | `scoring.py` | Blend the rule score and the ML score |
| Report | `report.py` | SAR narrative (template or LLM) |
| LLM | `llm/` | Provider-agnostic cascade |
| Flow | `service.py` | Ties the steps together |
| API | `main.py` | FastAPI endpoints |

## The graph

Each account is a node; each transfer is a directed edge with an amount and a time. We keep
a MultiDiGraph (parallel transfers are separate edges) for behavioural features, and a
collapsed weighted DiGraph for graph metrics like PageRank and cycle detection.

## Features

Per account: money in and out, net flow, pass-through ratio (money in ≈ money out), unique
senders and receivers, deposits just under the reporting threshold (in and out), how fast
money leaves after it arrives, PageRank, clustering, and whether the account sits in a short
cycle. These signals carry the typologies.

## Rules + model: explainable and learned

The system has two halves on purpose:

* **Typology rules** (`typologies.py`) are the explainable half. Each rule matches a known
  FATF pattern and says why, in words an analyst recognises.
* **The ML model** (`model.py`) is the learned half: a random forest trained on the features
  of known-suspicious and normal accounts.

The alert score blends them (`scoring.py`). The rules make every alert explainable; the
model catches combinations the rules miss. This is the standard shape of a real AML system.

## Why the background graph is a payment flow

The synthetic background is a payment flow (payers → merchants), which is acyclic. If the
background were random transfers, it would be full of short cycles, and the cycle signal
would flag everyone. Keeping the background acyclic makes a cycle a real signal, and varied
amounts keep a normal merchant from looking like a structuring collector.

## Human in the loop

ChainSentinel raises alerts and drafts a SAR; it does not file one. Every report ends with a
line that a human analyst must review. The LLM writes only the prose; the detection and the
score come from the rules and the model.

## Configuration

Settings use the `CS_` prefix (see `.env.example`): the model directory, the structuring
threshold, the alert threshold, the report mode (`template` or `llm`), and the provider order.
