"""The per-function JSON adapter, and the CLI path that rebuilds the baseline dataset with it."""

import json

import pytest

from autoharness_data.__main__ import main
from autoharness_data.adapters import functions_json
from conftest import BASELINE

GOLDEN = BASELINE / "golden" / "practicum-autoharness-functions.json.gz"


def test_parses_rows_and_ignores_input_labels():
    got = functions_json.parse(json.dumps({"functions": [
        {"crate": "core", "function": "a", "status": "generated", "reason": None},
        {"crate": "core", "function": "b", "status": "skipped", "reason": "WRONG LABEL",
         "detail": "The function does not have a body"},
    ]}))
    assert [(e.status, e.reason) for e in got.entries] == [
        ("generated", None), ("skipped", "The function does not have a body")]
    assert got.has_kani_headers is False and got.declared_generated is None


@pytest.mark.parametrize("doc,match", [
    ([], "must be an object"),
    ({"functions": [{"crate": "c", "function": "f", "status": "maybe"}]}, "status must be"),
    ({"functions": [{"crate": "c", "function": "f", "status": "skipped"}]}, "needs Kani's reason"),
    ({"functions": [{"crate": 1, "function": "f", "status": "generated"}]}, "must be strings"),
])
def test_rejects_malformed_input(doc, match):
    with pytest.raises(functions_json.InputError, match=match):
        functions_json.parse(json.dumps(doc))


def test_cli_rebuilds_baseline_dataset(tmp_path):
    out = tmp_path / "data"
    rc = main(["build", "--adapter", "per-function-json-v1", "--listing", str(GOLDEN),
               "--run-meta", str(BASELINE / "run-meta.toml"), "--expect", str(BASELINE / "expected.toml"),
               "--out", str(out)])
    assert rc == 0
    v = json.loads((out / "validation.json").read_text(encoding="utf-8"))
    skipped = {c["id"]: c["message"] for c in v["checks"] if c["status"] == "skipped"}
    assert len(skipped) == 4 and all("no Kani header counts" in m for m in skipped.values())
    run = json.loads((out / "run.json").read_text(encoding="utf-8"))
    assert run["adapter"] == "per-function-json-v1"
    assert [f["role"] for f in run["source_files"]] == ["per_function_json"]
    s = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert s["totals"] == {"candidates": 41233, "generated": 26975, "skipped": 14258}
