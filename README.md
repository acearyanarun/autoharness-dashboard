# autoharness-dashboard

Turns Kani AutoHarness output for the Rust standard library into **validated, versioned JSON**
that any dashboard can read. This repository is the data pipeline. A frontend comes later and
will consume only the published JSON.

```
Kani autoharness listing (stdout)
  → adapter (parse Kani's tables)
  → classify (bundled config/categories.toml)
  → validate (fail closed)
  → data/ (JSON, bundled schema/ v1)  →  any compatible UI
```

**Status: Phase 1.** Ingestion, classification, validation and the JSON contract are done and
tested. Not built yet: the Kani measurement workflow (Phase 2), GitHub issue sync (Phase 3) and
the dashboard (Phase 4).

## Quick start

Requires Python 3.11 or newer. The only runtime dependency is `jsonschema`: every `build`
and `verify` checks its output against the bundled schemas. If `jsonschema` can't be
imported, both commands exit `2` and write nothing. Schema validation is never skipped.

```sh
python -m pip install .               # or: python -m pip install -e '.[dev]' to run the tests
python -m pytest -rs

# Build data/ from a Kani listing
python -m autoharness_data build \
  --listing path/to/autoharness-list.stdout.txt[.gz] \
  --run-meta path/to/run-meta.toml \
  [--kani-list path/to/kani-list.json] [--expect expected.toml] \
  --out data/

# Check a published data/ directory (hashes, schemas, status)
python -m autoharness_data verify --data data/
```

Exit codes: `0` means the data was written and validation passed. `1` means validation failed; the data is still
written for inspection and `manifest.json` has `"status": "fail"`, so don't publish it. `2` means an input or usage
error, or that the schema validator is unavailable; nothing is written.

The category config and schemas ship inside the package (loaded with `importlib.resources`), so the
CLI works the same from a checkout and after `pip install`.

The listing is the stdout of `kani autoharness -Z autoharness --list --std ./library ...`, or of any
`kani autoharness` run that prints the selection tables (anything without `--quiet`).

## Layout

| Path | What |
|---|---|
| `generator/autoharness_data/` | The pipeline: `adapters/`, `classify`, `build`, `validate`, `emit`, `runmeta`, CLI |
| `generator/autoharness_data/config/categories.toml` | The five skip categories, their Kani reason prefixes and umbrella issues (#4887–#4891). Override with `--config DIR`. |
| `generator/autoharness_data/schema/` | JSON Schema (2020-12) for every published file. This is the contract. Override with `--schema-dir DIR`. |
| `fixtures/` | Golden baseline (2026-09-17) and tables copied from Kani's own test suite |
| `tests/` | Parser, classifier, pipeline, golden and pending raw-reproduction tests |
| `docs/` | [Data contract](docs/data-contract.md), [classification](docs/classification.md), [provenance](docs/provenance.md) |

## What has been proven so far

- The parser reads Kani's real output (tables from Kani's own test suite), and the test renderer
  reproduces those tables **byte for byte**.
- From the 2026-09-17 baseline's per-function rows, the pipeline reproduces **41,233 / 26,975 /
  14,258** and all five category totals, and matches the baseline's classification of every one of
  the 41,233 functions.
- **Still pending:** reproducing that baseline from the **original raw stdout**. See
  `fixtures/baseline-2026-09-17-x86_64/raw/README.md`. That test is skipped until the original files
  are found; they are never synthesized.

## License

MIT OR Apache-2.0. Fixture provenance and licensing: `fixtures/*/README.md` and `PROVENANCE.md`.
