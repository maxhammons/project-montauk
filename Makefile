# Project Montauk — canonical entry points.
#
# `make test` is the un-swallowable test runner: it uses the project venv's
# python directly (never a shell-hook-rewritten `pytest`), checks the venv
# exists before running, and propagates the real exit code. The certification
# net (golden regression, shadow comparator, ops contracts) is only trustworthy
# when invoked this way or via CI.

PY := .venv/bin/python

.PHONY: test
test:
	@test -x $(PY) || { echo "ERROR: $(PY) not found. Create it: python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt pytest"; exit 1; }
	$(PY) -m pytest tests/ -q
