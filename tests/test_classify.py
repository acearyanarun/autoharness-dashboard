"""Classifier tests: every known Kani reason form, fail-closed behaviour, argument splitting."""

import pytest

from autoharness_data import config as config_mod
from autoharness_data.classify import classify, split_args
from autoharness_data.model import RawEntry
from conftest import CONFIG, UPSTREAM
from support import small_fixtures as sf


def one(reason, cfg):
    got, unc = classify([RawEntry("core", "f", "skipped", reason)], cfg)
    return (got[0].category if got else None), unc


@pytest.mark.parametrize(
    "reason,category",
    [
        ("Missing Arbitrary implementation for argument(s) x: Foo", "missing_arbitrary"),
        (sf.GENERIC_NO_CANDIDATE, "generic_no_candidate"),
        (sf.GENERIC_NO_CANDIDATE_IMPL, "generic_no_candidate"),
        (sf.NON_USIZE_CONST, "const_generic_unsupported"),
        (sf.CONST_BLOCK, "const_generic_unsupported"),  # kani#4820, scoped to #4889
        ("Requires --bounded-arguments for argument(s) s: &str", "requires_bounded_arguments"),
        ("The function does not have a body", "no_body"),
    ],
)
def test_known_reasons(reason, category, cfg):
    assert one(reason, cfg) == (category, [])


def test_reasons_from_kani_test_suite(cfg):
    # Row fragments from Kani's generics test: the reason is the third cell.
    rows = [l.split(" | ", 2) for l in (UPSTREAM / "cargo_autoharness_generics.expected").read_text(encoding="utf-8").splitlines()
            if "Generic Function:" in l]
    assert len(rows) == 6
    for _, fn, reason in rows:
        cat, unc = one(reason.strip(), cfg)
        assert unc == [] and cat in {"generic_no_candidate", "const_generic_unsupported"}, fn


@pytest.mark.parametrize(
    "reason,hint_fragment",
    [
        ("Did not match provided filters", "UserFilter"),
        ("Generic Function: not a function definition", "not a function definition"),
        ("Some future Kani reason", None),
        ("Generic Function: something new", None),
        ("", None),
    ],
)
def test_unknown_or_excluded_reasons_fail_closed(reason, hint_fragment, cfg):
    cat, unc = one(reason, cfg)
    assert cat is None and len(unc) == 1
    if hint_fragment:
        assert hint_fragment in unc[0].hint
    else:
        assert unc[0].hint is None


def test_generated_passthrough(cfg):
    got, unc = classify([RawEntry("core", "f", "generated")], cfg)
    assert got[0].category is None and got[0].detail is None and unc == []


def test_args_extracted_for_arg_categories(cfg):
    got, _ = classify([RawEntry("core", "f", "skipped", sf.ALL_VARIANTS_SKIPPED[1][2])], cfg)
    assert got[0].args == (("a", "collections::HashMap<K, V>"), ("f", "impl Fn(u8, u8) -> (u8, u8)"))


@pytest.mark.parametrize(
    "text,expected",
    [
        ("x: u8", (("x", "u8"),)),
        ("self: &mut fmt::Formatter<'_>, s: &str", (("self", "&mut fmt::Formatter<'_>"), ("s", "&str"))),
        ("m: HashMap<K, V>, n: [u8; 4]", (("m", "HashMap<K, V>"), ("n", "[u8; 4]"))),
        ("f: fn(&T) -> bool, g: Box<dyn Fn(u8, u8) -> u8>", (("f", "fn(&T) -> bool"), ("g", "Box<dyn Fn(u8, u8) -> u8>"))),
        ("self: !", (("self", "!"),)),
        ("_: {closure@src/lib.rs:1:2}", (("_", "{closure@src/lib.rs:1:2}"),)),
        # ambiguous or malformed -> None (verbatim detail is still kept)
        ("self", None),
        ("x: Foo<", None),
        ("(a, b): (u8, u8)", None),
    ],
)
def test_split_args(text, expected):
    assert split_args(text) == expected


def test_config_rejects_overlapping_prefixes(tmp_path):
    (tmp_path / "categories.toml").write_text(
        (CONFIG / "categories.toml").read_text(encoding="utf-8")
        + '\n[[category]]\nid = "shadow"\nlabel = "x"\nkani_variant = "GenericFn"\nprefixes = ["Generic Function: no"]\n',
        encoding="utf-8",
    )
    with pytest.raises(config_mod.ConfigError, match="overlaps"):
        config_mod.load(tmp_path)


def test_config_umbrellas_match_issue_4879(cfg):
    assert {c.id: c.umbrella_number for c in cfg.categories} == {
        "missing_arbitrary": 4887,
        "generic_no_candidate": 4888,
        "const_generic_unsupported": 4889,
        "requires_bounded_arguments": 4890,
        "no_body": 4891,
    }
