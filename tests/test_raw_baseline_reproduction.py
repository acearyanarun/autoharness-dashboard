"""PENDING: reproduce the 2026-09-17 baseline from the ORIGINAL raw Kani listing.

Skipped until fixtures/baseline-2026-09-17-x86_64/raw/ holds the original, unmodified
listFile and kaniListFile (see raw/README.md). Never synthesize these files.
"""

import gzip
import json

import pytest

from autoharness_data import pipeline
from conftest import BASELINE, CONFIG, PRACTICUM_LABEL_TO_ID, SCHEMA

RAW = BASELINE / "raw"


def _find(stem):
    for suffix in ("", ".gz"):
        p = RAW / f"{stem}{suffix}"
        if p.exists():
            return p
    return None


LISTING = _find("autoharness-list.stdout.txt")
KANI_LIST = _find("kani-list.json")

pytestmark = pytest.mark.skipif(
    LISTING is None or KANI_LIST is None,
    reason="PENDING: original 2026-09-17 listFile/kaniListFile not yet located (see fixtures/.../raw/README.md)",
)


def test_reproduces_baseline_from_raw_listing(golden_rows):
    docs = pipeline.run_build(
        listing_path=LISTING, run_meta_path=BASELINE / "run-meta.toml", config_dir=CONFIG,
        kani_list_path=KANI_LIST, expect=BASELINE / "expected.toml", schema_dir=SCHEMA,
    )
    v = docs["validation.json"]
    assert v["status"] == "pass", [c for c in v["checks"] if c["status"] == "fail"]
    assert all(c["status"] == "pass" for c in v["checks"] if c["id"].startswith("listing."))

    ours = {}
    for path, doc in docs.items():
        if path.startswith("functions/") and path != "functions/index.json":
            for f in doc["functions"]:
                ours[(doc["crate"], f["name"])] = (f["status"], f.get("category"), f.get("detail"))
    theirs = {(r["crate"], r["function"]): (r["status"], PRACTICUM_LABEL_TO_ID.get(r["reason"]), r.get("detail"))
              for r in golden_rows}
    assert ours == theirs
