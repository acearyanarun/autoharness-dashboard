# Fixtures copied from Kani's own test suite

These are expected-output files from `model-checking/kani` (MIT OR Apache-2.0), copied
unmodified from commit `cab1b1506e8dbb28dfb09c6998285d0cce81f9ba`:

| File here | Kani path |
|---|---|
| `cargo_autoharness_filter.expected` | `tests/script-based-pre/cargo_autoharness_filter/filter.expected` |
| `cargo_autoharness_include.expected` | `tests/script-based-pre/cargo_autoharness_include/include.expected` |
| `cargo_autoharness_generics.expected` | `tests/script-based-pre/cargo_autoharness_generics/generics.expected` |

Kani compares these line-by-line as substrings, so some are partial:
`cargo_autoharness_generics.expected` has only row fragments (used for reason strings, not
table structure). The filter and include files contain complete tables.

They show the real table format (comfy-table ASCII_FULL) and real reason strings,
including the const-block `GenericFn` message added in kani#4820 and the `UserFilter`
reason. The include file also carries a verification summary table that has the same
"Selected Function" column, which the parser must ignore.
