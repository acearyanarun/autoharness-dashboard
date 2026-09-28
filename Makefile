# Convenience targets. Nothing here is required: every command is also in README.md.
PY ?= python
.PHONY: help install test data verify web-install web-test web web-fixture build clean

help:
	@echo "make install      Python package + dev tools (use inside a virtualenv)"
	@echo "make test         Python tests, then frontend tests"
	@echo "make data         Rebuild and verify the dashboard dataset (web/public/data)"
	@echo "make web          Start the dashboard dev server (http://localhost:5173)"
	@echo "make build        Data + frontend production build (web/dist)"

install:
	$(PY) -m pip install -e ".[dev]"

test:
	$(PY) -m pytest -rs
	cd web && npm test

data:
	scripts/build-baseline-data.sh

verify:
	$(PY) -m autoharness_data verify --data web/public/data

web-install:
	cd web && npm install

web-test:
	cd web && npm test

web:
	cd web && npm run dev

# Regenerate the small dataset the frontend tests read.
web-fixture:
	rm -rf web/src/test/fixtures/data
	$(PY) -m autoharness_data build --listing tests/fixtures_small/all_variants.stdout.txt \
	  --run-meta tests/fixtures_small/run-meta.toml --out web/src/test/fixtures/data

build: data
	cd web && npm run build

clean:
	rm -rf web/dist build *.egg-info generator/*.egg-info .pytest_cache
