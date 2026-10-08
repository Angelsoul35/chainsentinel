"""Combine the ML score and the typology rules into one alert score."""

from __future__ import annotations

from .schema import TypologyHit


def rule_score(hits: list[TypologyHit]) -> float:
    """A 0..1 score from the typology hits (more and stronger hits = higher)."""
    if not hits:
        return 0.0
    return min(1.0, sum(h.severity for h in hits) / 2.0)


def combined_score(ml_score: float, hits: list[TypologyHit], ml_weight: float = 0.5) -> float:
    """Blend the learned score with the rule score."""
    score = ml_weight * ml_score + (1 - ml_weight) * rule_score(hits)
    return round(float(min(1.0, max(0.0, score))), 4)
