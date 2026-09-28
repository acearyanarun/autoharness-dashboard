"""The 2026-09-17 baseline, checked against practicum's published per-function output.

What this proves: from the baseline's own (crate, function, reason) rows, this generator
reproduces every golden count and the baseline's classification of every function.

What it does not prove: that the parser reproduces those rows from the original raw
stdout. That is test_raw_baseline_reproduction.py, pending the original files.

The last test renders the golden rows as a Kani-format listing and parses them back. It is
a synthetic, large-scale parser round trip, not a reproduction of the original listing.
"""

import tomllib

import pytest

from autoharness_data import classify, pipeline, runmeta
from autoharness_data.adapters import kani_list_stdout as adapter
from autoharness_data.model import RawEntry
from conftest import BASELINE, PRACTICUM_LABEL_TO_ID, SCHEMA
from support.ascii_full import listing

EXPECTED = BASELINE / "expected.toml"


def rows_to_entries(rows):
    return [RawEntry(r["crate"], r["function"], r["status"], r.get("detail")) for r in rows]


@pytest.fixture(scope="module")
def golden_build(golden_rows, cfg):
    functions, unclassified = classify.classify(rows_to_entries(golden_rows), cfg)
    meta = runmeta.load(BASELINE / "run-meta.toml")
    run = runmeta.build_run(meta, None, [], "practicum-functions-json (test oracle)")
    docs = pipeline.assemble(
        listing=None, functions=functions, unclassified=unclassified, cfg=cfg, run=run,
        expect=EXPECTED, schema_dir=SCHEMA,
    )
    return functions, unclassified, docs


def test_every_function_classified(golden_build):
    _, unclassified, _ = golden_build
    assert unclassified == []


def test_totals_and_categories_match_r1(golden_build):
    _, _, docs = golden_build
    s = docs["summary.json"]
    assert s["totals"] == {"candidates": 41233, "generated": 26975, "skipped": 14258}
    assert {c["id"]: c["count"] for c in s["by_category"]} == {
        "missing_arbitrary": 6869,
        "generic_no_candidate": 4511,
        "const_generic_unsupported": 1581,
        "requires_bounded_arguments": 1102,
        "no_body": 195,
    }


def test_per_crate_and_other_crates_rollup(golden_build):
    _, _, docs = golden_build
    exp = tomllib.loads(EXPECTED.read_text(encoding="utf-8"))
    crates = {c["crate"]: c for c in docs["summary.json"]["by_crate"]}
    for name, want in exp["crates"].items():
        assert {k: crates[name][k] for k in want} == want
    others = [c for n, c in crates.items() if n not in exp["crates"]]
    assert {"generated": sum(c["generated"] for c in others),
            "skipped": sum(c["skipped"] for c in others)} == exp["other_crates_total"]


def test_every_function_matches_baseline_classification(golden_build, golden_rows):
    functions, _, _ = golden_build
    ours = {(f.crate, f.function): (f.status, f.category, f.detail) for f in functions}
    theirs = {
        (r["crate"], r["function"]): (r["status"], PRACTICUM_LABEL_TO_ID.get(r["reason"]), r.get("detail"))
        for r in golden_rows
    }
    assert len(ours) == len(theirs) == 41233
    mismatches = [k for k in theirs if ours.get(k) != theirs[k]]
    assert mismatches == []


def test_validation_passes_except_pending_listing_checks(golden_build):
    _, _, docs = golden_build
    v = docs["validation.json"]
    assert v["status"] == "pass"
    skipped = {c["id"] for c in v["checks"] if c["status"] == "skipped"}
    assert skipped == {
        "listing.generated_header", "listing.skipped_header",
        "listing.generated_rows_match_header", "listing.skipped_rows_match_header",
    }
    assert all(c["status"] == "pass" for c in v["checks"] if c["id"].startswith(("expect.", "schema.")))


def test_synthetic_round_trip_at_baseline_scale(golden_rows, cfg):
    gen = [(r["crate"], r["function"]) for r in golden_rows if r["status"] == "generated"]
    skip = [(r["crate"], r["function"], r["detail"]) for r in golden_rows if r["status"] == "skipped"]
    parsed = adapter.parse(listing(gen, skip))
    assert (parsed.declared_generated, parsed.declared_skipped) == (26975, 14258)
    assert [(e.crate, e.function) for e in parsed.entries if e.status == "generated"] == gen
    assert [(e.crate, e.function, e.reason) for e in parsed.entries if e.status == "skipped"] == skip
