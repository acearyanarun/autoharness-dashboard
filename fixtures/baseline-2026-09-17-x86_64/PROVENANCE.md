# Provenance: 2026-09-17 x86_64 controlled baseline

## What this run was

A `kani autoharness --list --std` listing over verify-rust-std's library, without
`--bounded-arguments`, on x86_64 Linux (47 GB RAM), taking 73 minutes. An otherwise
identical run with `--bounded-arguments` took 88 minutes and generated 28,077 / skipped 13,156.

| Item | Value | Source |
|---|---|---|
| Kani | `02abb5b0d` (short), reported version 0.67.0 | R1 baseline report; practicum `autoharness-dashboard.json` `meta` |
| Kani lineage | `b07abe8a7` + 2 compatibility commits + kani#4799, kani#4801, local workaround for kani#4794 | practicum dashboard notes |
| verify-rust-std | `9b38cdc4d84` on `sync-2026-08-21`, with local workarounds | R1 baseline report; practicum notes |
| Toolchain | `nightly-2026-08-21` | R1 baseline report |
| Target | `x86_64-unknown-linux-gnu` | practicum `meta.target` |
| Totals and categories | see `expected.toml` | R1 baseline report (authoritative) |
| Per-crate counts for core/alloc/std and the other-crates rollup | see `expected.toml` | practicum `autoharness-dashboard.json` `crates` |

Still unknown: the full 40-character SHAs, a reachable remote for `02abb5b0d`, the diff of
the local verify-rust-std workarounds, and the verbatim command line.

## Files in this directory

### `golden/practicum-autoharness-functions.json.gz`

The per-function output practicum published for this run (41,233 rows), gzip-compressed
deterministically (mtime 0).

- Origin: `wodex1nhaoIeng/practicum`, commit `976c355`, path `ui/public/data/autoharness-functions.json`
- Git blob: `58cc694926baa33598e3505e66e28406ac195dd9`
- sha256 (uncompressed): `d6c47a8ef3369dc4d8b3c4647278734dcf9cfc8c5afba1bba473077dd43358a3`
- Produced by practicum's converter from the original listing. Its `detail` field is Kani's
  "Reason for Skipping" cell, trimmed.
- It is generated **data**, used here as an expected-output oracle. No practicum source
  code is included in this repository.
- Publication: this repository is private. Get the data owner's agreement before making
  this file public.

What it can prove: that this generator's classifier, summary, sharding, and validation
reproduce the baseline's per-function classification and every golden count from the
same (crate, function, reason) rows.

What it cannot prove: that the table **parser** reproduces those rows from the original
raw stdout. That needs `raw/` (below).

### `raw/` (pending)

See `raw/README.md`. Nothing in `raw/` is synthesized; it stays empty until the original
files are located.
