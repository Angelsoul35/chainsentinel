"""Combine the ML score and the typology rules into one alert score.

The learned model and the explicit typology rules are two *independent* sources
of evidence. They are fused with a **noisy-OR**, not a weighted average:

    combined = 1 - (1 - ml_score) * (1 - rule_score)

A weighted average silently *dilutes* a confident signal — a launderer the model
scores 0.9 but no rule happens to match would blend to 0.45 and fall under the
alert threshold, so the detector would miss real laundering just because the
explainable layer did not also fire. That is a loss of detection power, not a
feature. Noisy-OR instead reads as "the account is suspicious if *either* the
model or an explicit typology says so," so neither source can veto the other; the
combined score is always at least the max of the two. The model gives recall on
the subtle cases, the rules give explainability and catch textbook structures,
and the fusion keeps both.
"""

from __future__ import annotations

from .schema import TypologyHit


def rule_score(hits: list[TypologyHit]) -> float:
    """A 0..1 score from the typology hits (more and stronger hits = higher)."""
    if not hits:
        return 0.0
    return min(1.0, sum(h.severity for h in hits) / 2.0)


def combined_score(ml_score: float, hits: list[TypologyHit]) -> float:
    """Fuse the learned score and the rule score with a noisy-OR (see module docstring)."""
    ml = min(1.0, max(0.0, ml_score))
    rules = rule_score(hits)
    combined = 1.0 - (1.0 - ml) * (1.0 - rules)
    return round(float(combined), 4)
