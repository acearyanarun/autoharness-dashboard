"""Schema validation is mandatory: it must never be skipped silently (audit finding I1).

Matrix (build):
    valid output   + validator available   -> exit 0
    invalid output + validator available   -> exit 1 (schema check fails, data marked "fail")
    invalid output + validator unavailable -> exit 2 (nothing written)
    valid output   + validator unavailable -> exit 2 (nothing written)
verify behaves the same way. "Unavailable" is simulated in-process here, and for real in a
separate interpreter in test_install.py.
"""

import json
import sys

import pytest

from autoharness_data import emit, resources
from autoharness_data.__main__ import main
from conftest import SMALL

LISTING = SMALL / "all_variants.stdout.txt"


@pytest.fixture
def invalid_meta(small_run_meta, tmp_path):
    # Accepted by run-meta loading, rejected by run.schema.json (duration_seconds minimum 0).
    p = tmp_path / "invalid-meta.toml"
    p.write_text(
        small_run_meta.read_text(encoding="utf-8").replace(
            'finished_at = "2026-01-01"', 'finished_at = "2026-01-01"\nduration_seconds = -5'
        ),
        encoding="utf-8",
    )
    return p


@pytest.fixture
def no_validator(monkeypatch):
    # A None entry in sys.modules makes `import jsonschema` raise ImportError.
    monkeypatch.setitem(sys.modules, "jsonschema", None)


def build(listing, meta, out):
    return main(["build", "--listing", str(listing), "--run-meta", str(meta), "--out", str(out)])


def test_valid_output_with_validator_passes(tmp_path, small_run_meta):
    assert build(LISTING, small_run_meta, tmp_path / "out") == 0


def test_invalid_output_with_validator_fails(tmp_path, invalid_meta, capsys):
    assert build(LISTING, invalid_meta, tmp_path / "out") == 1
    out = capsys.readouterr().out
    assert "schema.valid:run.json" in out and "duration_seconds" in out
    assert json.loads((tmp_path / "out" / "manifest.json").read_text(encoding="utf-8"))["status"] == "fail"


def test_invalid_output_without_validator_fails_and_writes_nothing(tmp_path, invalid_meta, no_validator, capsys):
    assert build(LISTING, invalid_meta, tmp_path / "out") == 2
    assert not (tmp_path / "out").exists()
    err = capsys.readouterr().err
    assert "'jsonschema' package is required" in err and "never skipped" in err


def test_valid_output_without_validator_still_refuses(tmp_path, small_run_meta, no_validator):
    # Even good data is not written unchecked.
    assert build(LISTING, small_run_meta, tmp_path / "out") == 2
    assert not (tmp_path / "out").exists()


def test_verify_without_validator_refuses(tmp_path, small_run_meta, monkeypatch, capsys):
    assert build(LISTING, small_run_meta, tmp_path / "out") == 0
    monkeypatch.setitem(sys.modules, "jsonschema", None)
    assert main(["verify", "--data", str(tmp_path / "out")]) == 2
    assert "'jsonschema' package is required" in capsys.readouterr().err


def test_verify_catches_schema_invalid_data(tmp_path, small_run_meta):
    assert build(LISTING, small_run_meta, tmp_path / "out") == 0
    # Edit run.json by hand and fix up the manifest hash, so only the schema can catch it.
    import hashlib

    run_path = tmp_path / "out" / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["duration_seconds"] = -5
    data = (json.dumps(run, indent=2) + "\n").encode("utf-8")
    run_path.write_bytes(data)
    man_path = tmp_path / "out" / "manifest.json"
    man = json.loads(man_path.read_text(encoding="utf-8"))
    for f in man["files"]:
        if f["path"] == "run.json":
            f["sha256"], f["bytes"] = hashlib.sha256(data).hexdigest(), len(data)
    man_path.write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    assert main(["verify", "--data", str(tmp_path / "out")]) == 1


def test_require_validator_raises_not_warns(no_validator):
    with pytest.raises(resources.ValidatorUnavailable):
        resources.require_validator()


def test_emit_refuses_malformed_validation_doc(tmp_path, small_run_meta):
    from autoharness_data import pipeline

    docs = pipeline.run_build(listing_path=LISTING, run_meta_path=small_run_meta)
    docs["validation.json"]["status"] = "maybe"  # not in the schema's enum
    with pytest.raises(RuntimeError, match="refusing to write"):
        emit.write(tmp_path / "out", docs)
    assert not (tmp_path / "out").exists()
