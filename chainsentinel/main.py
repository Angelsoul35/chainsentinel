"""ChainSentinel HTTP API."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .schema import AnalysisResult, Transaction
from .service import AnalyzeService

app = FastAPI(
    title="ChainSentinel",
    version="1.0.0",
    summary="Anti-money-laundering detection on a transaction graph with alerts and reports.",
)

_service: AnalyzeService | None = None


def get_service() -> AnalyzeService:
    global _service
    if _service is None:
        _service = AnalyzeService()
    return _service


class AnalyzeRequest(BaseModel):
    transactions: list[Transaction]
    with_reports: bool = Field(default=False)


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/model", tags=["model"])
def model_info() -> dict:
    return get_service().model_info()


@app.post("/analyze", response_model=AnalysisResult, tags=["analyze"])
def analyze(request: AnalyzeRequest) -> AnalysisResult:
    transactions = [t.model_dump() for t in request.transactions]
    return get_service().analyze(transactions, with_reports=request.with_reports)


@app.post("/analyze/sample", response_model=AnalysisResult, tags=["analyze"])
def analyze_sample(with_reports: bool = False) -> AnalysisResult:
    result, _suspicious = get_service().analyze_sample(with_reports=with_reports)
    return result
