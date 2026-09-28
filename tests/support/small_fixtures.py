"""Definitions of the small synthetic listings in tests/fixtures_small/.

Regenerate with:  python -m support.small_fixtures   (from the tests/ directory)
test_synthetic_listings.py fails if a checked-in file drifts from these definitions.

Reason strings are Kani's formats (kani-driver/src/autoharness/mod.rs), with detail texts
from kani-compiler/src/kani_middle/codegen_units.rs and Kani's own test expectations.
"""

from __future__ import annotations

from pathlib import Path

from support.ascii_full import listing, table

HERE = Path(__file__).resolve().parents[1] / "fixtures_small"

GENERIC_NO_CANDIDATE = (
    "Generic Function: no candidate type (i32, u32, usize, u8, i64, u64, f64, f32, bool, char) "
    "satisfies the function's trait bounds"
)
GENERIC_NO_CANDIDATE_IMPL = (
    "Generic Function: no candidate type (i32, u32, usize, u8, i64, u64, f64, f32, bool, char "
    "and 3 types implementing the required traits) satisfies the function's trait bounds"
)
NON_USIZE_CONST = "Generic Function: non-usize const generic parameters are not supported yet"
CONST_BLOCK = (
    "Generic Function: the function has a `const {}` block that may constrain its const generic "
    "parameter(s), and the value autoharness substitutes (2) is not guaranteed to satisfy it"
)

ALL_VARIANTS_GENERATED = [
    ("core", "num::<impl u8>::checked_add"),
    ("core", "ptr::alignment::Alignment::new"),
    ("alloc", "alloc::Global::allocate"),
    ("std", "<fn(&u8) -> bool as ops::Fn<(&u8,)>>::call"),
]
ALL_VARIANTS_SKIPPED = [
    ("core", "fmt::Formatter::pad", "Missing Arbitrary implementation for argument(s) self: &mut fmt::Formatter<'_>, s: &str"),
    ("core", "iter::zip", "Missing Arbitrary implementation for argument(s) a: collections::HashMap<K, V>, f: impl Fn(u8, u8) -> (u8, u8)"),
    ("core", "<! as fmt::Debug>::fmt", "Missing Arbitrary implementation for argument(s) self: !"),
    ("core", "slice::sort::merge", GENERIC_NO_CANDIDATE),
    ("alloc", "vec::Vec::<T, A>::push", GENERIC_NO_CANDIDATE_IMPL),
    ("core", "core_arch::x86::sse2::_mm_slli_epi16", NON_USIZE_CONST),
    ("core", "array::from_fn_checked", CONST_BLOCK),
    ("core", "str::from_utf8", "Requires --bounded-arguments for argument(s) v: &[u8]"),
    ("std", "ffi::CStr::to_str", "Requires --bounded-arguments for argument(s) self: &ffi::CStr"),
    ("core", "intrinsics::ctpop", "The function does not have a body"),
]

BUILD_NOISE = [
    "Kani Rust Verifier 0.67.0 (standalone)",
    "warning: Found the following unsupported constructs:",
    "  | some line that starts with a pipe but is outside any table |",
    "Compiling core ... done",
]

VERIFY_SUMMARY = ["", "Autoharness Summary:"] + table(
    ["Crate", "Selected Function", "Kind of Automatic Harness", "Verification Result"],
    [["core", "num::<impl u8>::checked_add", "#[kani::proof]", "Success"]],
) + ["Complete - 1 successfully verified functions, 0 failures, 1 total."]


def all_variants() -> str:
    body = listing(ALL_VARIANTS_GENERATED, ALL_VARIANTS_SKIPPED)
    return "\n".join(BUILD_NOISE) + "\n" + body + "\n".join(VERIFY_SUMMARY) + "\n"


def no_selected() -> str:
    return listing([], [("core", "intrinsics::ctpop", "The function does not have a body")])


def no_skipped() -> str:
    return listing([("core", "num::<impl u8>::checked_add")], [])


FIXTURES = {
    "all_variants.stdout.txt": all_variants,
    "no_selected.stdout.txt": no_selected,
    "no_skipped.stdout.txt": no_skipped,
}


def main() -> None:
    HERE.mkdir(exist_ok=True)
    for name, fn in FIXTURES.items():
        (HERE / name).write_text(fn(), encoding="utf-8")
        print(f"wrote {HERE / name}")


if __name__ == "__main__":
    main()
