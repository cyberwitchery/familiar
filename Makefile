.PHONY: install dev format lint test coverage ci build clean publish

install:
	pip install .

dev:
	pip install -e ".[dev]"

format:
	ruff format .

lint:
	ruff format --check .
	ruff check .
	mypy .
	bandit -r src/ -s B404,B603,B607

test:
	pytest -q

coverage:
	pytest --cov-report=term-missing --cov-report=html

ci:
	pytest --cov-report=term-missing --cov-report=xml

build: clean
	python -m build

clean:
	rm -rf dist/ build/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

publish: build
	twine upload dist/*
