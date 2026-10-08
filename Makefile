.PHONY: install test lint train run demo clean

install:
	pip install -e ".[dev]"

test:
	pytest --cov=chainsentinel --cov-report=term-missing

lint:
	ruff check chainsentinel tests

train:
	python -m chainsentinel.cli train

run:
	uvicorn chainsentinel.main:app --reload --port 8000

demo:
	python -m chainsentinel.cli demo

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov artifacts/*
	touch artifacts/.gitkeep
