# ADR-0002: Combine explainable rules with a learned model

* Status: accepted
* Date: 2026-03-02

## Context

Pure rules are explainable but brittle: launderers change behaviour to dodge known rules. A
pure ML model catches more but cannot explain itself, and an unexplained AML alert is hard to
act on. We want both.

## Decision

Typology rules give explainable hits; a random-forest model gives a learned score. The alert
score blends the two. Every alert carries the typologies it matched, so it is explainable.

## Consequences

* **Good:** alerts are both strong and explainable. The rules catch known patterns and say
  why; the model catches combinations the rules miss.
* **Cost:** two systems to maintain and a blend weight to tune. That is the normal shape of a
  real AML system, so the cost buys realism.
