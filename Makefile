.PHONY: install dev lint test build clean publish

install:
	pip install .

dev:
	pip install -e ".[dev]"

lint:
	ruff check .
	mypy src/familiar

test:
	pytest tests/

coverage:
	pytest tests/ --cov=familiar --cov-report=term-missing --cov-report=html

build: clean
	python -m build

clean:
	rm -rf dist/ build/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

publish: build
	twine upload dist/*
