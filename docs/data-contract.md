# Data contract (schema v1)

A frontend needs only this document and `schema/`. It must not parse Kani output.

## Rules for consumers

1. Read `manifest.json` first. Only use data whose `status` is `"pass"`.
2. Accept any `schema_version` of `1.x.y`. Minor versions only add optional fields.
3. Resolve every path relative to the directory holding `manifest.json`. No absolute paths
   appear anywhere, so the data can be hosted under any URL prefix.
4. Compute percentages, ordering and labels yourself. Category labels are in `categories.json`.
5. Compare two runs only when their `run.json` `comparability_key` values are equal.

## Files

| File | Purpose | Size (2026-09-17 baseline) |
|---|---|---|
| `manifest.json` | Run id, status, generator version, and every file with bytes + sha256 | < 2 KB |
| `run.json` | What was measured: Kani/library repo, ref, commit, toolchain, target, flags, host, command, workflow URL, source-file hashes, `comparability_key` | < 2 KB |
| `categories.json` | Category ids, labels, Kani variant, axis, umbrella issue, `expected_behavior`, match prefixes | 2 KB |
| `summary.json` | Totals, count per category (all categories, zeros included), count per crate | 2 KB |
| `functions/index.json` | One entry per crate shard, with counts | 2 KB |
| `functions/<crate>.json` | Every listed function of the crate: `name`, `status`; if skipped, `category`, verbatim `detail`, and `args` when they parse unambiguously | core 3.2 MB (≈150 KB gzipped) |
| `validation.json` | Every check with id, severity, status, expected and actual | < 10 KB |

## Guarantees the validator enforces

- The generated and skipped row counts equal the counts Kani printed in its own headers.
- generated + skipped = candidates, and the category and crate counts add up to the totals.
- Every skipped function is in exactly one configured category. Unknown Kani wording fails.
- No duplicate `(crate, function)` pairs, and crate names are safe file names.
- Every file validates against its schema, and `verify` re-checks the hashes after publishing.
- Rebuilding from the same inputs produces byte-identical output: no wall-clock timestamps,
  and ordering is stable.

## Not observable from Kani's listing

`KaniImpl` skips (Kani's own instrumentation, harnesses and trait impls) are left out of Kani's
tables, so they don't appear in `candidates`. The 2026-09-17 run had 4,563 of them, per practicum's notes.
`summary.json` `not_observable` says this explicitly.

## Planned additions (later phases, additive)

`issues.json` (Phase 3: curated category/umbrella/child map plus fetched issue and PR state),
`history.json` and `delta.json` (runs grouped by `comparability_key`).
