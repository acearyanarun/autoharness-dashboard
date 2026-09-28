# Classification

Kani prints one "Reason for Skipping" string per skipped function. The formats come from
Kani `kani-driver/src/autoharness/mod.rs` (`print_autoharness_metadata`):

| Kani variant | Printed as |
|---|---|
| `MissingArbitraryImpl(args)` | `Missing Arbitrary implementation for argument(s) name: Type, ...` |
| `RequiresBoundedArguments(args)` | `Requires --bounded-arguments for argument(s) name: Type, ...` |
| `GenericFn(detail)` | `Generic Function: <detail>` |
| `NoBody` | `The function does not have a body` |
| `UserFilter` | `Did not match provided filters` |
| `KaniImpl` | not printed |

The `GenericFn` details come from `kani-compiler/src/kani_middle/codegen_units.rs`:
"no candidate type (…) satisfies the function's trait bounds", "non-usize const generic
parameters are not supported yet", "the function has a `const {}` block …" (added in kani#4820,
after the 2026-09-17 baseline), and "not a function definition".

## Mapping (`generator/autoharness_data/config/categories.toml`)

| Category id | Umbrella | Reason prefix(es) |
|---|---|---|
| `missing_arbitrary` | kani#4887 | `Missing Arbitrary implementation for argument(s)` |
| `generic_no_candidate` | kani#4888 | `Generic Function: no candidate type` |
| `const_generic_unsupported` | kani#4889 | `Generic Function: non-usize const generic parameters`, `Generic Function: the function has a \`const {}\` block` |
| `requires_bounded_arguments` | kani#4890 | `Requires --bounded-arguments for argument(s)` |
| `no_body` | kani#4891 | `The function does not have a body` |

**Why `GenericFn` is split in two:** one Kani variant covers two root causes with different fixes:
the instantiation search (#4888) and const-parameter support (#4889).

**Why the const-block message goes to #4889:** #4889 scopes both non-usize const parameters and
usize parameters guarded by `const {}` preconditions. practicum's converter would have put this
message under "Other"; it didn't come up in the 2026-09-17 baseline because the message is newer.

## Fail-closed rules

- A reason matching no category fails validation (`classification.complete`). There is no
  catch-all "Other".
- `Did not match provided filters` fails with a UserFilter explanation: a filtered run is not a
  full-library measurement.
- `Generic Function: not a function definition` fails with its own hint until an umbrella is chosen.
- Category prefixes may not overlap, so the result never depends on rule order.

## Arguments

For the two argument-carrying variants, `args` is split into `(name, type)` pairs. Types can
contain `, ` (`HashMap<K, V>`), so splitting happens only at bracket depth 0, and `->` is treated
as an arrow. If splitting is ambiguous, `args` is left out; the verbatim `detail` is always kept.
On the 2026-09-17 baseline all 7,971 argument lists split unambiguously.
