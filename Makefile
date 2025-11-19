# Makefile for RDBMS to Graph Migration System

.PHONY: help install install-dev test clean lint format docs run-example

help:
	@echo "Available commands:"
	@echo "  make install       - Install package dependencies"
	@echo "  make install-dev   - Install package with development dependencies"
	@echo "  make test          - Run tests"
	@echo "  make test-cov      - Run tests with coverage"
	@echo "  make clean         - Clean build artifacts"
	@echo "  make lint          - Run code linting"
	@echo "  make format        - Format code with black"
	@echo "  make run-example   - Run simple migration example"

install:
	pip install -r requirements.txt

install-dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/ examples/

run-example:
	python examples/simple_migration.py
