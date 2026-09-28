"""Parser tests: real Kani output, synthetic listings, and malformed input."""

import pytest

from autoharness_data.adapters import kani_list_stdout as adapter
from autoharness_data.adapters.kani_list_stdout import ParseError
from conftest import SMALL, UPSTREAM
from support import small_fixtures
from support.ascii_full import listing, table


def parse_file(path):
    return adapter.parse(path.read_text(encoding="utf-8"))


# --- real Kani output (Kani's own test expectations) ------------------------------------

def test_kani_filter_expected():
    got = parse_file(UPSTREAM / "cargo_autoharness_filter.expected")
    assert (got.declared_generated, got.declared_skipped) == (50, 1)
    gen = [e for e in got.entries if e.status == "generated"]
    skip = [e for e in got.entries if e.status == "skipped"]
    assert len(gen) == 50 and len(skip) == 1
    assert gen[0].function == "no_harness::unsupported_no_arg_name"
    assert skip[0].function == "no_harness::doesnt_implement_arbitrary"
    assert skip[0].reason == "Missing Arbitrary implementation for argument(s) x: DoesntImplementArbitrary<'_>"
    assert all(e.crate == "cargo_autoharness_filter" for e in got.entries)
    assert got.warnings == []


def test_kani_include_expected_ignores_verification_summary():
    got = parse_file(UPSTREAM / "cargo_autoharness_include.expected")
    # The "Autoharness Summary" table also has a "Selected Function" column; it must not be read.
    assert [(e.status, e.function) for e in got.entries] == [
        ("generated", "include::generic::<i32>"),
        ("generated", "include::simple"),
        ("skipped", "excluded::simple"),
    ]
    assert got.entries[-1].reason == "Did not match provided filters"


# --- synthetic listings ------------------------------------------------------------------

def test_all_variants_fixture():
    got = parse_file(SMALL / "all_variants.stdout.txt")
    assert got.declared_generated == len(small_fixtures.ALL_VARIANTS_GENERATED)
    assert got.declared_skipped == len(small_fixtures.ALL_VARIANTS_SKIPPED)
    assert [(e.crate, e.function) for e in got.entries if e.status == "generated"] == small_fixtures.ALL_VARIANTS_GENERATED
    assert [(e.crate, e.function, e.reason) for e in got.entries if e.status == "skipped"] == small_fixtures.ALL_VARIANTS_SKIPPED


def test_line_numbers_point_at_rows():
    text = (SMALL / "all_variants.stdout.txt").read_text(encoding="utf-8")
    lines = text.splitlines()
    for e in parse_file(SMALL / "all_variants.stdout.txt").entries:
        assert e.function in lines[e.line - 1]


@pytest.mark.parametrize("name,gen,skip", [("no_selected.stdout.txt", 0, 1), ("no_skipped.stdout.txt", 1, 0)])
def test_empty_sections(name, gen, skip):
    got = parse_file(SMALL / name)
    assert (got.declared_generated, got.declared_skipped) == (gen, skip)
    assert sum(e.status == "generated" for e in got.entries) == gen
    assert sum(e.status == "skipped" for e in got.entries) == skip


def test_missing_sections_are_reported_not_invented():
    got = adapter.parse("nothing to see here\n")
    assert got.entries == [] and got.declared_generated is None and got.declared_skipped is None


def test_pipe_inside_cell_uses_column_positions():
    text = listing([("core", "f::<{closure@|x| x}>")], [("core", "g", "The function does not have a body")])
    got = adapter.parse(text)
    assert got.entries[0].function == "f::<{closure@|x| x}>"


def test_wide_unicode_falls_back_to_pipe_split():
    # comfy-table pads by display width: each CJK character is two columns wide, so the
    # row carries two fewer spaces than code-point counting predicts.
    lines = listing([("core", "名前")], []).splitlines()
    i = next(n for n, l in enumerate(lines) if "名前" in l)
    lines[i] = lines[i].replace("名前  ", "名前", 1)
    got = adapter.parse("\n".join(lines))
    assert got.entries[0].function == "名前"


def test_crlf_and_ansi_are_tolerated():
    text = listing([("core", "a")], []).replace("\n", "\r\n")
    text = text.replace("Kani generated", "\x1b[1mKani generated").replace("function(s):", "function(s):\x1b[0m")
    assert [e.function for e in adapter.parse(text).entries] == ["a"]


def test_multiline_cell_is_merged_with_warning():
    rows = table(["Crate", "Selected Function"], [["core", "a"]])
    width = len(rows[0])
    cont = "|" + " " * 7 + "|" + " tail".ljust(width - 10) + "|"
    assert len(cont) == width
    text = "Kani generated automatic harnesses for 1 function(s):\n" + "\n".join(rows[:4] + [cont] + rows[4:]) + "\n"
    got = adapter.parse(text)
    assert got.entries[0].function == "a\ntail"
    assert len(got.warnings) == 1


# --- malformed input fails loudly ----------------------------------------------------------

def test_unterminated_table():
    # Output cut off mid-table (e.g. a killed job): must fail, not return partial rows.
    lines = listing([("core", "a"), ("core", "b")], []).splitlines()
    bottom = max(i for i, l in enumerate(lines) if l.startswith("+-"))
    with pytest.raises(ParseError, match="not terminated"):
        adapter.parse("\n".join(lines[:bottom]) + "\n")


def test_blank_line_inside_table():
    lines = listing([("core", "a"), ("core", "b")], []).splitlines()
    bottom = max(i for i, l in enumerate(lines) if l.startswith("+-"))
    del lines[bottom]
    with pytest.raises(ParseError, match="column layout"):
        adapter.parse("\n".join(lines) + "\n")


def test_wrong_header():
    text = listing([("core", "a")], []).replace("Selected Function", "Selected Harness ")
    with pytest.raises(ParseError, match="unexpected table header"):
        adapter.parse(text)


def test_garbage_inside_table():
    lines = listing([("core", "a"), ("core", "b")], []).splitlines()
    lines.insert(6, "warning: interleaved output from another thread")
    with pytest.raises(ParseError, match="line 7"):
        adapter.parse("\n".join(lines))


def test_duplicate_section():
    text = listing([("core", "a")], [])
    with pytest.raises(ParseError, match="second generated section"):
        adapter.parse(text + text)
