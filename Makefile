# ==========================================
# LangChain Agent Framework Makefile
# ==========================================

VENV := .venv
PYTHON := $(VENV)/Scripts/python
PIP := $(VENV)/Scripts/pip
PYTEST := $(VENV)/Scripts/pytest
PFLAKE8 := $(VENV)/Scripts/pflake8

.PHONY: init run test fmt lint coverage clean install

init:
	@echo "========================================"
	@echo "Creating virtual environment..."
	@echo "========================================"
	python -m venv $(VENV)
	
	@echo "========================================"
	@echo "Installing dependencies..."
	@echo "========================================"
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install . '.[lint]' '.[test]' '.[package]' \
		-i https://pypi.tuna.tsinghua.edu.cn/simple/

install:
	$(PIP) install . '.[lint]' '.[test]' '.[package]' \
		-i https://pypi.tuna.tsinghua.edu.cn/simple/

run:
	$(PYTHON) -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

chat:
	$(PYTHON) -m src.chat

test:
	$(PYTEST) tests/ -v

fmt:
	$(PYTHON) -m black ./src ./tests
	$(PYTHON) -m isort --profile black ./src ./tests
	@$(MAKE) lint

lint:
	$(PFLAKE8) ./src ./tests

coverage:
	$(PYTEST) --cov=src tests/

clean:
	rm -rf $(VENV)
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
