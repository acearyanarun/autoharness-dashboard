# Development

## Prerequisites

- Python 3.11 or newer
- Node 20.19+ or 22.12+ (the dashboard only)
- Bash for `scripts/build-baseline-data.sh` (or run its two commands by hand)

## Setup

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"            # installs jsonschema (runtime), pytest and setuptools (dev)
cd web && npm install && cd ..
```

## Everyday commands

| Task | Command |
|---|---|
| Python tests | `pytest` (add `-rs` to see why the one test is skipped) |
| Frontend tests | `cd web && npm test` (watch mode: `npm run test:watch`) |
| Typecheck frontend | `cd web && npm run typecheck` |
| Dashboard dev server | `cd web && npm run dev` → http://localhost:5173 |
| Production build | `cd web && npm run build` → `web/dist/` |
| Preview the build | `cd web && npm run preview` |
| Rebuild the bundled dataset | `scripts/build-baseline-data.sh` |
| Rebuild the frontend test dataset | `make web-fixture` |
| Verify any data directory | `python -m autoharness_data verify --data <dir>` |

## Producing a dataset from a real Kani run

1. Run Kani and keep **stdout unmodified**:
   ```sh
   kani autoharness -Z autoharness -Z unstable-options --list --std ./library \
     -Z function-contracts -Z mem-predicates -Z float-lib -Z c-ffi -Z loop-contracts \
     > autoharness-list.stdout.txt
   ```
   Don't pass `--quiet` (it suppresses the tables) or include/exclude patterns (a filtered run fails validation).
2. Write `run-meta.toml`:
   ```toml
   run_id = "my-run-2026-10-01"
   provenance = "manual"                 # "ci" when produced by a workflow
   finished_at = "2026-10-01T18:05:00Z"  # ISO-8601 date, or datetime with timezone
   target = "x86_64-unknown-linux-gnu"
   duration_seconds = 4380
   command = "kani autoharness ..."

   [kani]
   repo = "model-checking/kani"
   commit = "<full 40-char sha>"
   [library]
   repo = "model-checking/verify-rust-std"
   ref = "main"
   commit = "<full 40-char sha>"
   [toolchain]
   channel = "nightly-2026-08-21"
   [flags]
   bounded_arguments = false
   [host]
   os = "linux"
   arch = "x86_64"
   cpus = 16
   memory_gb = 64
   ```
3. Build, verify, and view:
   ```sh
   python -m autoharness_data build --listing autoharness-list.stdout.txt \
     --run-meta run-meta.toml --kani-list kani-list.json --out /tmp/mydata
   python -m autoharness_data verify --data /tmp/mydata
   ```
   Then serve it next to a dashboard build, or open the dev server with `?data=` pointing at it.

## Tests

| Suite | What it covers |
|---|---|
| `tests/test_adapter_stdout.py` | Parser on Kani's real test-suite output and on edge cases (pipes in names, wide Unicode, CRLF/ANSI, truncation, garbage, duplicate sections) |
| `tests/test_synthetic_listings.py` | The test renderer reproduces Kani's tables byte for byte; checked-in synthetic fixtures are current |
| `tests/test_classify.py` | Every known Kani reason form, fail-closed behaviour, argument splitting |
| `tests/test_golden_baseline.py` | Reproduces every Sept. 17 figure and the classification of all 41,233 functions |
| `tests/test_raw_baseline_reproduction.py` | **Pending**: the same, from the original raw stdout (skipped until it is found) |
| `tests/test_schema_required.py` | Schema validation can't be skipped; missing validator → exit 2, nothing written |
| `tests/test_install.py` | Wheel install into isolated venvs; bundled resources found; refuses without jsonschema |
| `tests/test_committed_datasets.py` | `web/public/data` and the frontend fixture equal a fresh build |
| `web/src/test/load.test.ts` | Loader: valid data, failed manifest, unreachable/malformed/tampered data, schema major, lazy loading |
| `web/src/test/views.test.tsx` | Overview numbers and error states, Coverage counts/percentages/detail panel, Functions lazy loading and filtering |

## Deployment

`ci.yml` always runs the tests and the production build. It deploys `web/dist` to GitHub Pages only
when the repository variable **`ENABLE_PAGES`** is `true`, on pushes to
`feature/autoharness-dynamic-dashboard`. Otherwise the deploy job is skipped and CI stays green.
One-time setup, when you decide to publish:

1. *Settings → Pages → Build and deployment → Source: **GitHub Actions***.
2. *Settings → Secrets and variables → Actions → Variables → New repository variable*:
   `ENABLE_PAGES` = `true`.
3. If the deploy job reports that the branch is not allowed to deploy: *Settings → Environments →
   github-pages → Deployment branches*, and add `feature/autoharness-dynamic-dashboard`.

**Visibility.** Pages for a private repository requires GitHub Pro, Team or Enterprise, and the site is
**public** unless the organization has Enterprise Cloud private Pages. The bundled dataset is derived from a
teammate's data (see `provenance.md`), so choose one of these:

| Option | Exposure |
|---|---|
| Don't enable Pages; teammates run `cd web && npm install && npm run dev` | None beyond repository collaborators |
| Download the `github-pages` artifact from a CI run and serve it locally (`python -m http.server` in the unzipped folder) | Repository collaborators |
| Enable Pages after the data owner agrees, or after replacing the dataset with a run you produced | Public |
| Host in an organization with Enterprise Cloud private Pages | Organization members |

The build is portable: it works at any URL prefix, so moving it to another organization or repository
needs no code change.
