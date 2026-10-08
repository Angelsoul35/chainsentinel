"""Models for transactions, typology hits, and alerts."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    tx_id: str
    src: str
    dst: str
    amount: float
    timestamp: int  # hour index in this demo


class TypologyHit(BaseModel):
    name: str
    detail: str
    severity: float  # 0..1


class Alert(BaseModel):
    address: str
    score: float  # combined 0..1
    ml_score: float
    typologies: list[TypologyHit] = Field(default_factory=list)
    features: dict = Field(default_factory=dict)
    report: str | None = None


class AnalysisResult(BaseModel):
    n_accounts: int
    n_transactions: int
    alerts: list[Alert] = Field(default_factory=list)
