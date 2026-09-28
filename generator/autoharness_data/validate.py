"""Validation checks. Errors block publication; warnings are reported only."""

from __future__ import annotations

import json
import tomllib
from collections import Counter
from pathlib import Path

from . import SCHEMA_VERSION
from .build import CRATE_FILE_NAME
from .model import Check, Classified, Listing, Unclassified

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schema"


def _check(checks, cid, ok, message, expected=None, actual=None, severity="error"):
    checks.append(Check(cid, severity, "pass" if ok else "fail", message, expected, actual))


def listing_checks(listing: Listing | None, functions: list[Classified]) -> list[Check]:
    checks: list[Check] = []
    if listing is None:
        for cid in ("listing.generated_header", "listing.skipped_header",
                    "listing.generated_rows_match_header", "listing.skipped_rows_match_header"):
            checks.append(Check(cid, "error", "skipped", "no raw listing was parsed for this build"))
        return checks
    # Count the parsed rows themselves, independent of classification, so an unclassified
    # reason is reported once (by classification.complete), not again as a count mismatch.
    gen = sum(1 for e in listing.entries if e.status == "generated")
    skip = len(listing.entries) - gen
    _check(checks, "listing.generated_header", listing.declared_generated is not None,
           "Kani's 'generated automatic harnesses for N' line (or 'Selected Functions: None') is present")
    _check(checks, "listing.skipped_header", listing.declared_skipped is not None,
           "Kani's 'did not generate automatic harnesses for M' line (or 'Skipped Functions: None') is present")
    if listing.declared_generated is not None:
        _check(checks, "listing.generated_rows_match_header", gen == listing.declared_generated,
               "generated table rows equal the count Kani announced", listing.declared_generated, gen)
    if listing.declared_skipped is not None:
        _check(checks, "listing.skipped_rows_match_header", skip == listing.declared_skipped,
               "skipped table rows equal the count Kani announced", listing.declared_skipped, skip)
    for w in listing.warnings:
        checks.append(Check("listing.adapter_warning", "warning", "fail", w))
    return checks


def data_checks(functions: list[Classified], unclassified: list[Unclassified], docs: dict) -> list[Check]:
    checks: list[Check] = []
    keys = Counter((f.crate, f.function) for f in functions)
    keys.update((u.crate, u.function) for u in unclassified)
    dups = sorted(k for k, n in keys.items() if n > 1)
    _check(checks, "functions.unique", not dups, "no (crate, function) pair appears twice",
           0, len(dups))
    empty = [f for f in functions if not f.crate or not f.function]
    _check(checks, "functions.nonempty_names", not empty, "every row has a crate and a function name", 0, len(empty))
    bad_crates = sorted({f.crate for f in functions if not CRATE_FILE_NAME.match(f.crate)})
    _check(checks, "functions.crate_names_safe", not bad_crates,
           f"crate names are safe file names ({CRATE_FILE_NAME.pattern})", [], bad_crates)

    sample = [f"{u.crate}::{u.function}: {u.reason!r}" + (f" ({u.hint})" if u.hint else "") for u in unclassified[:5]]
    _check(checks, "classification.complete", not unclassified,
           "every skipped function maps to exactly one configured category"
           + ("" if not unclassified else "; first unclassified: " + " | ".join(sample)),
           0, len(unclassified))

    s = docs["summary.json"]
    t = s["totals"]
    _check(checks, "summary.partition", t["generated"] + t["skipped"] == t["candidates"],
           "generated + skipped = candidates", t["candidates"], t["generated"] + t["skipped"])
    cat_sum = sum(c["count"] for c in s["by_category"])
    _check(checks, "summary.categories_sum", cat_sum == t["skipped"],
           "category counts add up to skipped", t["skipped"], cat_sum)
    crate_gen = sum(c["generated"] for c in s["by_crate"])
    crate_skip = sum(c["skipped"] for c in s["by_crate"])
    _check(checks, "summary.crates_sum", (crate_gen, crate_skip) == (t["generated"], t["skipped"]),
           "per-crate counts add up to the totals", [t["generated"], t["skipped"]], [crate_gen, crate_skip])
    idx = docs["functions/index.json"]
    shard_total = sum(len(docs[r["path"]]["functions"]) for r in idx["crates"] if r["path"] in docs)
    _check(checks, "functions.shards_match_summary", shard_total == t["candidates"],
           "function shards contain exactly the summary's candidates", t["candidates"], shard_total)
    return checks


def schema_checks(docs: dict, schema_dir: Path = SCHEMA_DIR) -> list[Check]:
    """Validate every document against schema/. Needs the optional jsonschema package."""
    try:
        import jsonschema  # noqa: PLC0415 - optional dependency
    except ImportError:
        return [Check("schema.valid", "warning", "skipped",
                      "jsonschema is not installed; install the 'dev' extra to validate against schema/")]
    checks: list[Check] = []
    for path, doc in sorted(docs.items()):
        schema_name = schema_for(path)
        schema = json.loads((Path(schema_dir) / schema_name).read_text())
        errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(doc), key=lambda e: list(e.path))
        _check(checks, f"schema.valid:{path}", not errors,
               f"{path} matches {schema_name}" + ("" if not errors else f": {errors[0].message} at {list(errors[0].path)}"),
               0, len(errors))
    return checks


def schema_for(path: str) -> str:
    if path.startswith("functions/") and path != "functions/index.json":
        return "functions-crate.schema.json"
    return {
        "manifest.json": "manifest.schema.json",
        "run.json": "run.schema.json",
        "summary.json": "summary.schema.json",
        "categories.json": "categories.schema.json",
        "functions/index.json": "functions-index.schema.json",
        "validation.json": "validation.schema.json",
    }[path]


def expectation_checks(path: Path | None, docs: dict) -> list[Check]:
    """Compare against a golden expectations file (fixtures/<run>/expected.toml)."""
    if path is None:
        return []
    with open(path, "rb") as fh:
        exp = tomllib.load(fh)
    s = docs["summary.json"]
    checks: list[Check] = []
    for key, want in exp.get("totals", {}).items():
        _check(checks, f"expect.totals.{key}", s["totals"].get(key) == want,
               f"total {key} matches {path.name}", want, s["totals"].get(key))
    got_cats = {c["id"]: c["count"] for c in s["by_category"]}
    for cid, want in exp.get("categories", {}).items():
        _check(checks, f"expect.categories.{cid}", got_cats.get(cid) == want,
               f"category {cid} matches {path.name}", want, got_cats.get(cid))
    got_crates = {c["crate"]: c for c in s["by_crate"]}
    for crate, want in exp.get("crates", {}).items():
        got = got_crates.get(crate, {})
        actual = {k: got.get(k) for k in want}
        _check(checks, f"expect.crates.{crate}", actual == want,
               f"crate {crate} matches {path.name}", want, actual)
    return checks


def validation_doc(run_id: str, checks: list[Check]) -> dict:
    failed_errors = [c for c in checks if c.severity == "error" and c.status == "fail"]
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "status": "fail" if failed_errors else "pass",
        "counts": {
            "pass": sum(c.status == "pass" for c in checks),
            "fail": sum(c.status == "fail" for c in checks),
            "skipped": sum(c.status == "skipped" for c in checks),
        },
        "checks": [
            {k: v for k, v in {
                "id": c.id, "severity": c.severity, "status": c.status, "message": c.message,
                "expected": c.expected, "actual": c.actual,
            }.items() if v is not None}
            for c in checks
        ],
    }
