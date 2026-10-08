from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from chainsentinel.generate import make_transactions
from chainsentinel.llm.base import LLMError
from chainsentinel.llm.cascade import CascadeLLM
from chainsentinel.llm.factory import build_llm
from chainsentinel.llm.fake import FailingLLM, FakeLLM
from chainsentinel.report import build_report
from chainsentinel.schema import Alert, TypologyHit


def test_cascade_fallback_and_failure():
    assert CascadeLLM([FailingLLM("a"), FakeLLM("ok")]).complete("s", "p").text == "ok"
    with pytest.raises(LLMError):
        CascadeLLM([FailingLLM("a"), FailingLLM("b")]).complete("s", "p")


def test_build_llm_cascade():
    multi = build_llm("anthropic,openai,ollama")
    assert isinstance(multi, CascadeLLM)
    assert [c.name for c in multi.clients] == ["anthropic", "openai", "ollama"]


def test_report_with_fake_llm():
    alert = Alert(
        address="x",
        score=0.9,
        ml_score=0.8,
        typologies=[TypologyHit(name="structuring", detail="d", severity=0.9)],
        features={"total_in": 1000},
    )
    assert build_report(alert, llm=FakeLLM("LLM report text.")) == "LLM report text."


def test_api(service):
    import chainsentinel.main as main

    main._service = service
    client = TestClient(main.app)

    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/model").json()["version"].startswith("m_")

    sample = client.post("/analyze/sample")
    assert sample.status_code == 200
    assert sample.json()["n_transactions"] > 0
    assert len(sample.json()["alerts"]) > 0

    txs, _ = make_transactions(seed=99)
    response = client.post("/analyze", json={"transactions": txs[:300], "with_reports": False})
    assert response.status_code == 200
    assert "alerts" in response.json()
