# Architecture

## Goal

Measure how Kani's AutoHarness applies to the Rust standard library, explain every skip in terms of the
Kani issue that owns it, and do it with a pipeline that could run in any repository: this one, a
`model-checking/autoharness-dashboard`, or `tools/autoharness-dashboard/` inside verify-rust-std.

## The pieces

```
 ┌──────────────────────── ingestion (Python, generator/) ────────────────────────┐
 │                                                                                 │
 │  input ──► adapter ──► classify ──► build docs ──► validate ──► emit (hashes)   │
 │            │            │                           │                           │
 │   kani-list-stdout-v1   config/categories.toml      schema/*.schema.json        │
 │   per-function-json-v1  (prefix rules; unknown     + count/consistency checks   │
 │                          → hard failure)                                        │
 └───────────────────────────────────┬─────────────────────────────────────────────┘
                                     │  data/  (JSON contract v1, sha256 manifest)
 ┌───────────────────────────────────▼─────────────────────────────────────────────┐
 │  presentation (React, web/)                                                     │
 │  loader: fetch manifest → refuse unless status "pass" → verify hashes → views   │
 └─────────────────────────────────────────────────────────────────────────────────┘
```

### Ingestion: `generator/autoharness_data/`

| Module | Responsibility |
|---|---|
| `adapters/kani_list_stdout.py` | Parses the two ASCII tables Kani prints for `kani autoharness` (selected / skipped), plus Kani's own "for N function(s)" totals. Strict inside a table; ignores everything outside. Checked byte for byte against Kani's test-suite output. |
| `adapters/functions_json.py` | Reads per-function JSON (`crate`, `function`, `status`, verbatim `detail`). Used to rebuild the Sept. 17 baseline while its raw stdout is missing. Has no Kani totals, so header checks report "not applicable". |
| `classify.py` | Maps each Kani reason to exactly one category by prefix (`config/categories.toml`); splits argument lists into `(name, type)` pairs when unambiguous. |
| `build.py` | Builds the contract documents: pure, no I/O. |
| `validate.py` | Header counts, partition sums, uniqueness, classification completeness, optional golden expectations, and **mandatory** JSON Schema validation. |
| `emit.py` | Deterministic serialization, the sha256 manifest, and self-checks of `validation.json` and `manifest.json` before anything is written. |
| `runmeta.py` | Run metadata (Kani / library revisions, target, flags, host, ISO-8601 timestamps) and the `comparability_key`. |
| `resources.py` | Finds bundled config and schemas through `importlib.resources`, so the package works after `pip install`. |

### The contract: `data/`

Seven kinds of files, each with a JSON Schema. The dashboard reads `manifest.json` first and refuses the
dataset unless `status` is `"pass"`. See [data-contract.md](data-contract.md).

### Presentation: `web/`

| Path | Responsibility |
|---|---|
| `src/data/load.ts` | The only code that fetches. Checks schema major version, manifest status, per-file sha256, `run_id` consistency and totals; lazily loads crate files and caches them. |
| `src/data/derive.ts` | Percentages, labels, and category color slots. Pure and tested. |
| `src/data/explanations.ts` | Explanatory copy keyed by category id, with a fallback for unknown ids. |
| `src/views/*` | Overview, Coverage (decision tree + detail panel), Functions (filters, pagination), About. |
| `src/router.ts` | Hash routing, so the site needs no server rewrites and works under any base path. |

Build: Vite with `base: "./"`, so every asset path is relative. The dataset is copied from
`web/public/data` into `dist/data`. `?data=<url>` points the same build at another dataset.

## Design decisions

| Decision | Why |
|---|---|
| Parse Kani's printed tables rather than internal metadata files | They are the output Kani prints for users; the metadata files are internal and unversioned. A future machine-readable Kani output becomes a new adapter, and nothing downstream changes. |
| Categories in config, not code | Changing classification is a reviewed data change with a test, not a code change. |
| Fail closed on unknown reasons | A Kani wording change must never be silently counted under the wrong issue. |
| `jsonschema` is a required dependency | Validation that can silently disappear is not validation. A second, hand-written validator could drift from the schemas. |
| Committed dataset + drift check in CI | `npm run dev` works without Python, and CI proves the committed data is exactly what the generator produces. |
| Hash routing + relative paths | Portable to any GitHub Pages path or organization with no configuration. |
| Hashes verified in the browser | A dataset edited by hand, or mixed from two runs, is refused rather than displayed. |

## What runs where

| Where | What |
|---|---|
| Developer machine | Everything: generator, tests, dashboard dev server |
| GitHub Actions (`ci.yml`) | Python tests (3.11–3.13), installed-package smoke test, dataset rebuild + drift check, frontend tests + build, Pages deploy on the feature branch |
| Not yet (Phase 2) | Building Kani and running AutoHarness in CI; issue sync; history |
