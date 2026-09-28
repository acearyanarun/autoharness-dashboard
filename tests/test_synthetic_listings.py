"""Keep synthetic fixtures honest: the renderer must match Kani byte for byte, and the
checked-in small fixtures must match their definitions."""

import pytest

from autoharness_data.adapters import kani_list_stdout as adapter
from conftest import SMALL, UPSTREAM
from support import small_fixtures
from support.ascii_full import listing


@pytest.mark.parametrize("name", ["cargo_autoharness_filter.expected", "cargo_autoharness_include.expected"])
def test_renderer_matches_kani_output_exactly(name):
    text = (UPSTREAM / name).read_text()
    parsed = adapter.parse(text)
    gen = [(e.crate, e.function) for e in parsed.entries if e.status == "generated"]
    skip = [(e.crate, e.function, e.reason) for e in parsed.entries if e.status == "skipped"]
    rendered = listing(gen, skip).splitlines()[1:]  # renderer starts with Kani's blank line
    lines = text.splitlines()
    start = lines.index(rendered[0])
    assert lines[start : start + len(rendered)] == rendered


@pytest.mark.parametrize("name", sorted(small_fixtures.FIXTURES))
def test_checked_in_fixture_is_current(name):
    assert (SMALL / name).read_text() == small_fixtures.FIXTURES[name](), (
        "regenerate with: cd tests && python -m support.small_fixtures"
    )
