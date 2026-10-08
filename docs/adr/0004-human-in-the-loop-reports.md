# ADR-0004: Draft reports, but keep a human in the loop

* Status: accepted
* Date: 2026-03-03

## Context

Filing a suspicious-activity report (SAR) has legal weight. An automated system should prepare
the work, not file it, and the model should never be the one that "decides" in prose.

## Decision

For the top alerts, the system drafts a SAR narrative (template or LLM). Every draft ends with
a line that a human analyst must review. The LLM only writes the prose; the detection and the
score come from the rules and the model.

## Consequences

* **Good:** analysts get a ready draft and save time, but the decision stays with a person,
  and the alert is grounded in rules and a score, not in the LLM's words.
* **Cost:** a human step remains. For a legally weighty action, that is the right trade-off.
