"""End-to-end: CLI build + verify, exit codes, schema validity, determinism, validation gates."""

import json
import shutil

import jsonschema
import pytest

from autoharness_data.__main__ import main
from autoharness_data.validate import schema_for
from conftest import CONFIG, SCHEMA, SMALL, UPSTREAM
from support.ascii_full import listing


def build(tmp_path, listing_path, meta, out="data", extra=()):
    return main([
        "build", "--listing", str(listing_path), "--run-meta", str(meta), "--config", str(CONFIG),
        "--schema-dir", str(SCHEMA), "--out", str(tmp_path / out), *extra,
    ])


def load_all(root):
    return {p.relative_to(root).as_posix(): json.loads(p.read_text()) for p in root.rglob("*.json")}


def test_build_all_variants_passes_and_verifies(tmp_path, small_run_meta):
    assert build(tmp_path, SMALL / "all_variants.stdout.txt", small_run_meta) == 0
    docs = load_all(tmp_path / "data")
    assert set(docs) == {
        "manifest.json", "run.json", "categories.json", "summary.json", "validation.json",
        "functions/index.json", "functions/core.json", "functions/alloc.json", "functions/std.json",
    }
    assert docs["summary.json"]["totals"] == {"candidates": 14, "generated": 4, "skipped": 10}
    assert {c["id"]: c["count"] for c in docs["summary.json"]["by_category"]} == {
        "missing_arbitrary": 3, "generic_no_candidate": 2, "const_generic_unsupported": 2,
        "requires_bounded_arguments": 2, "no_body": 1,
    }
    assert main(["verify", "--data", str(tmp_path / "data"), "--schema-dir", str(SCHEMA)]) == 0


def test_every_output_matches_its_schema(tmp_path, small_run_meta):
    build(tmp_path, SMALL / "all_variants.stdout.txt", small_run_meta)
    for path, doc in load_all(tmp_path / "data").items():
        schema = json.loads((SCHEMA / schema_for(path)).read_text())
        jsonschema.Draft202012Validator(schema).validate(doc)


def test_schemas_are_valid_json_schema():
    for p in SCHEMA.glob("*.schema.json"):
        jsonschema.Draft202012Validator.check_schema(json.loads(p.read_text()))


def test_byte_identical_rebuilds(tmp_path, small_run_meta):
    build(tmp_path, SMALL / "all_variants.stdout.txt", small_run_meta, "a")
    build(tmp_path, SMALL / "all_variants.stdout.txt", small_run_meta, "b")
    a = {p.relative_to(tmp_path / "a"): p.read_bytes() for p in (tmp_path / "a").rglob("*.json")}
    b = {p.relative_to(tmp_path / "b"): p.read_bytes() for p in (tmp_path / "b").rglob("*.json")}
    assert a == b


def test_output_contains_no_presentation(tmp_path, small_run_meta):
    build(tmp_path, SMALL / "all_variants.stdout.txt", small_run_meta)
    text = (tmp_path / "data" / "summary.json").read_text()
    for forbidden in ("coverage", "share", "percent", "title", "dependencies"):
        assert forbidden not in text


def test_user_filter_listing_fails_validation(tmp_path, small_run_meta):
    # Kani's own include-pattern test output: a filtered run is not a full measurement.
    assert build(tmp_path, UPSTREAM / "cargo_autoharness_include.expected", small_run_meta) == 1
    v = json.loads((tmp_path / "data" / "validation.json").read_text())
    failed = [c for c in v["checks"] if c["status"] == "fail"]
    assert [c["id"] for c in failed] == ["classification.complete"]
    assert "UserFilter" in failed[0]["message"]
    manifest = json.loads((tmp_path / "data" / "manifest.json").read_text())
    assert manifest["status"] == "fail"
    assert main(["verify", "--data", str(tmp_path / "data"), "--schema-dir", str(SCHEMA)]) == 1


def test_row_count_mismatch_with_kani_header_fails(tmp_path, small_run_meta):
    text = listing([("core", "a"), ("core", "b")], []).replace("for 2 function(s):", "for 3 function(s):")
    p = tmp_path / "listing.txt"
    p.write_text(text)
    assert build(tmp_path, p, small_run_meta) == 1
    v = json.loads((tmp_path / "data" / "validation.json").read_text())
    bad = {c["id"]: c for c in v["checks"] if c["status"] == "fail"}
    assert bad["listing.generated_rows_match_header"]["expected"] == 3
    assert bad["listing.generated_rows_match_header"]["actual"] == 2


def test_missing_header_fails(tmp_path, small_run_meta):
    p = tmp_path / "listing.txt"
    p.write_text("build log with no autoharness tables\n")
    assert build(tmp_path, p, small_run_meta) == 1


def test_gzip_listing_and_kani_version(tmp_path, small_run_meta):
    import gzip

    gz = tmp_path / "listing.txt.gz"
    gz.write_bytes(gzip.compress((SMALL / "no_skipped.stdout.txt").read_bytes()))
    kl = tmp_path / "kani-list.json"
    kl.write_text(json.dumps({"kani-version": "0.67.0", "file-version": "0.1"}))
    assert build(tmp_path, gz, small_run_meta, extra=("--kani-list", str(kl))) == 0
    run = json.loads((tmp_path / "data" / "run.json").read_text())
    assert run["kani"]["version"] == "0.67.0"
    assert [f["role"] for f in run["source_files"]] == ["listing", "kani_list"]


def test_tampered_output_fails_verify(tmp_path, small_run_meta):
    build(tmp_path, SMALL / "all_variants.stdout.txt", small_run_meta)
    f = tmp_path / "data" / "summary.json"
    f.write_text(f.read_text().replace('"generated": 4', '"generated": 5'))
    assert main(["verify", "--data", str(tmp_path / "data"), "--schema-dir", str(SCHEMA)]) == 1


def test_bad_run_meta_is_input_error(tmp_path):
    meta = tmp_path / "m.toml"
    meta.write_text('run_id = "x"\nprovenance = "ci"\ntarget = "t"\n[kani]\ncommit = "main"\n'
                    '[library]\ncommit = "abcdef0"\n[flags]\nbounded_arguments = false\n')
    assert build(tmp_path, SMALL / "no_skipped.stdout.txt", meta) == 2


def test_comparability_key_changes_with_flags(tmp_path, small_run_meta):
    build(tmp_path, SMALL / "no_skipped.stdout.txt", small_run_meta, "a")
    bounded = tmp_path / "bounded.toml"
    bounded.write_text(small_run_meta.read_text().replace("bounded_arguments = false", "bounded_arguments = true"))
    build(tmp_path, SMALL / "no_skipped.stdout.txt", bounded, "b")
    ka = json.loads((tmp_path / "a" / "run.json").read_text())["comparability_key"]
    kb = json.loads((tmp_path / "b" / "run.json").read_text())["comparability_key"]
    assert ka != kb
