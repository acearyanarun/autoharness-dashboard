"""The datasets committed for the dashboard must be exactly what the generator produces today.

- web/public/data/            the Sept. 17 baseline the dashboard ships with
- web/src/test/fixtures/data/ the small dataset the frontend tests read

If a generator change alters output, these tests fail until the data is regenerated:
    scripts/build-baseline-data.sh      (and see docs/development.md for the fixture)
"""

import pytest

from autoharness_data.__main__ import main
from conftest import BASELINE, ROOT, SMALL

WEB_DATA = ROOT / "web" / "public" / "data"
WEB_FIXTURE = ROOT / "web" / "src" / "test" / "fixtures" / "data"


def tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def assert_same(fresh, committed, how):
    if not committed.exists():
        pytest.fail(f"{committed} is missing; regenerate with: {how}")
    a, b = tree(fresh), tree(committed)
    assert sorted(a) == sorted(b), f"file sets differ; regenerate with: {how}"
    stale = [p for p in a if a[p] != b[p]]
    assert not stale, f"stale committed files {stale}; regenerate with: {how}"


def test_web_baseline_dataset_is_current(tmp_path):
    out = tmp_path / "data"
    assert main(["build", "--adapter", "per-function-json-v1",
                 "--listing", str(BASELINE / "golden" / "practicum-autoharness-functions.json.gz"),
                 "--run-meta", str(BASELINE / "run-meta.toml"), "--expect", str(BASELINE / "expected.toml"),
                 "--out", str(out)]) == 0
    assert_same(out, WEB_DATA, "scripts/build-baseline-data.sh")


def test_web_test_fixture_is_current(tmp_path):
    out = tmp_path / "data"
    assert main(["build", "--listing", str(SMALL / "all_variants.stdout.txt"),
                 "--run-meta", str(SMALL / "run-meta.toml"), "--out", str(out)]) == 0
    assert_same(out, WEB_FIXTURE, "make web-fixture")
