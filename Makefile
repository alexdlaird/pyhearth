.PHONY: all install nopyc clean test check local validate-release upload

SHELL := /usr/bin/env bash
PYTHON_BIN ?= python
PROJECT_VENV ?= venv

all: local check test

venv:
	$(PYTHON_BIN) -m pip install virtualenv --user
	$(PYTHON_BIN) -m virtualenv $(PROJECT_VENV)

install: venv
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		python -m pip install .; \
	)

nopyc:
	find . -name '*.pyc' | xargs rm -f || true
	find . -name __pycache__ | xargs rm -rf || true

clean: nopyc
	rm -rf build dist *.egg-info $(PROJECT_VENV)

test: install
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		python -m pip install ".[dev]"; \
		coverage run -m unittest discover -v && coverage report && coverage xml && coverage html; \
	)

check: install
	@( \
		source $(PROJECT_VENV)/bin/activate; \
		python -m pip install ".[dev]"; \
		mypy pyhearth && flake8; \
	)

local:
	@rm -rf *.egg-info dist
	@( \
		$(PYTHON_BIN) -m pip install --upgrade pip && \
		$(PYTHON_BIN) -m pip install --upgrade build && \
		$(PYTHON_BIN) -m build && \
		$(PYTHON_BIN) -m pip install dist/*.tar.gz; \
	)

validate-release:
	@if [[ "${VERSION}" == "" ]]; then echo "VERSION is not set" & exit 1 ; fi

	@if [[ $$(grep "__version__ = \"${VERSION}\"" pyhearth/__init__.py) == "" ]] ; then echo "Version not bumped in pyhearth/__init__.py" & exit 1 ; fi

	@if [ -f SECURITY.md ]; then \
		MAJOR_MINOR=$$(echo "${VERSION}" | cut -d. -f1-2); \
		if [[ $$(grep "| $${MAJOR_MINOR}\.x" SECURITY.md) == "" ]] ; then echo "SECURITY.md missing supported-versions entry for $${MAJOR_MINOR}.x" & exit 1 ; fi; \
	fi

upload: local
	@( \
		$(PYTHON_BIN) -m pip install --upgrade twine && \
		$(PYTHON_BIN) -m build && \
		$(PYTHON_BIN) -m twine upload dist/*; \
	)
