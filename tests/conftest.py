from __future__ import annotations

import pytest

from chainsentinel.config import Settings
from chainsentinel.generate import make_transactions
from chainsentinel.service import AnalyzeService


@pytest.fixture(scope="session")
def sample():
    return make_transactions(seed=42)


@pytest.fixture(scope="session")
def service(tmp_path_factory):
    model_dir = tmp_path_factory.mktemp("artifacts")
    settings = Settings(model_dir=str(model_dir))
    return AnalyzeService(settings=settings, train_params={"n_estimators": 120})
