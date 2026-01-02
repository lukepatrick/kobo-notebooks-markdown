SHELL ?= /bin/bash

################################################################################
# Setup and Help                                                               #
################################################################################

.PHONY: help
help: ## This help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.DEFAULT_GOAL := help

################################################################################
# Development                                                                  #
################################################################################

.PHONY: install
install: ## Install development dependencies
	python -m pip install --upgrade pip
	pip install -e ".[dev]"

.PHONY: install-ai
install-ai: ## Install with AI features
	python -m pip install --upgrade pip
	pip install -e ".[dev,ai]"

.PHONY: lint
lint: ## Run ruff linter
	ruff check .

.PHONY: lint-fix
lint-fix: ## Run ruff linter with auto-fix
	ruff check --fix .

.PHONY: format
format: ## Run ruff formatter
	ruff format .

.PHONY: format-check
format-check: ## Check formatting without changes
	ruff format --check .

.PHONY: test
test: ## Run pytest
	pytest

.PHONY: test-verbose
test-verbose: ## Run pytest with verbose output
	pytest -v

.PHONY: test-coverage
test-coverage: ## Run pytest with coverage report
	pytest --cov=src/kobo_md --cov-report=term-missing

.PHONY: typecheck
typecheck: ## Run mypy type checker
	mypy src

################################################################################
# Build and Clean                                                              #
################################################################################

.PHONY: build
build: clean ## Build distribution packages
	python -m build

.PHONY: clean
clean: ## Remove build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true

################################################################################
# CI Pipeline                                                                  #
################################################################################

.PHONY: ci
ci: lint test ## Run CI pipeline (lint + test)

.PHONY: ci-full
ci-full: lint format-check typecheck test ## Run full CI pipeline

################################################################################
# Preflight Checks                                                             #
################################################################################

HAS_PYTHON := $(shell command -v python;)
HAS_PIP    := $(shell command -v pip;)
HAS_RUFF   := $(shell command -v ruff;)

.PHONY: check
check: ## Preflight checks for required tools
ifndef HAS_PYTHON
	$(error You must install python)
endif
ifndef HAS_PIP
	$(error You must install pip)
endif
	@echo "All required tools are installed"
