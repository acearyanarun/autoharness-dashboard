from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
SCHEMA = ROOT / "schema"
SMALL = ROOT / "tests" / "fixtures_small"
UPSTREAM = ROOT / "fixtures" / "kani-upstream"
BASELINE = ROOT / "fixtures" / "baseline-2026-09-17-x86_64"

# practicum's display labels -> this project's stable category ids
PRACTICUM_LABEL_TO_ID = {
    "Missing Arbitrary": "missing_arbitrary",
    "Generic: no candidate type": "generic_no_candidate",
    "Non-usize const generic": "const_generic_unsupported",
    "Requires bounded arguments": "requires_bounded_arguments",
    "No function body": "no_body",
}


@pytest.fixture(scope="session")
def cfg():
    from autoharness_data import config

    return config.load(CONFIG)


@pytest.fixture(scope="session")
def golden_rows():
    """Practicum's published per-function output for the 2026-09-17 baseline (oracle)."""
    data = gzip.decompress((BASELINE / "golden" / "practicum-autoharness-functions.json.gz").read_bytes())
    doc = json.loads(data)
    assert doc["generatedAt"] == "2026-09-17"
    return doc["functions"]


@pytest.fixture
def small_run_meta(tmp_path):
    p = tmp_path / "run-meta.toml"
    p.write_text(
        'run_id = "synthetic"\nprovenance = "manual"\nfinished_at = "2026-01-01"\n'
        'target = "x86_64-unknown-linux-gnu"\n'
        '[kani]\ncommit = "0000000"\n[library]\ncommit = "1111111"\n'
        "[flags]\nbounded_arguments = false\n"
    )
    return p
