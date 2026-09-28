# Contributing

Thanks for helping. This file covers the rules. For setup and day-to-day commands, see
[docs/development.md](docs/development.md).

## Branches

- All work happens on `feature/autoharness-dynamic-dashboard` or on branches cut from it.
- Do not create, push to, or merge into `main` until the team decides where this project will live.
- Open pull requests against `feature/autoharness-dynamic-dashboard`.

## Ground rules

1. **Ingestion and presentation stay separate.** Anything that knows about Kani output lives in
   `generator/`. `web/` reads only the published JSON (`docs/data-contract.md`). Never parse Kani text in the UI.
2. **Fail closed.** Never add a catch-all category, soften a validation check, or add a flag that skips
   schema validation. Unknown data must fail the build with a message that says why.
3. **No numbers in UI code.** Counts, labels and issue links come from the data. The UI may compute
   percentages and hold explanatory copy keyed by category id.
4. **Don't fake anything.** No synthesized "real" fixtures, and no UI that implies live data or synced
   issues before they exist. Mark planned features "Coming next".
5. **Deterministic output.** Same input, byte-identical output. No wall-clock timestamps, and no unstable ordering.

## Changing things

| If you change… | Also do |
|---|---|
| Classification (`generator/autoharness_data/config/categories.toml`) | Update `docs/classification.md`; add a test in `tests/test_classify.py` with the exact Kani reason text; regenerate data |
| A schema (`generator/autoharness_data/schema/`) | Additive → bump the minor `SCHEMA_VERSION`; breaking → bump the major and update `web/src/data/contract.ts` and `SUPPORTED_SCHEMA_MAJOR`; update `docs/data-contract.md` |
| Generator output in any way | `scripts/build-baseline-data.sh` and `make web-fixture`, then commit `web/public/data` and `web/src/test/fixtures/data` (CI fails on drift) |
| The dashboard | `cd web && npm test && npm run build`; check light, dark and a narrow window |

## Before you push

```sh
pytest                      # all green; exactly 1 skipped (pending raw Sept. 17 listing)
cd web && npm test && npm run build
```

Write commit messages in the imperative, and explain *why* in the body when it isn't obvious.

## Data you may not own

`fixtures/baseline-2026-09-17-x86_64/golden/` and the dataset derived from it (`web/public/data`) come
from a teammate's project. Do not publish them (a public repository, or a public Pages site) until
publication is agreed. See `docs/provenance.md`.
