"""Build the contract documents (pure: no I/O) from classified functions."""

from __future__ import annotations

import re
from collections import Counter

from . import SCHEMA_VERSION
from .config import Config
from .model import Classified

CRATE_FILE_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_-]*$")


def _umbrella(cat) -> dict | None:
    if cat.umbrella_repo is None or cat.umbrella_number is None:
        return None
    return {
        "repo": cat.umbrella_repo,
        "number": cat.umbrella_number,
        "url": f"https://github.com/{cat.umbrella_repo}/issues/{cat.umbrella_number}",
    }


def categories_doc(config: Config) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "categories": [
            {
                "id": c.id,
                "label": c.label,
                "kani_variant": c.kani_variant,
                "axis": c.axis,
                "expected_behavior": c.expected_behavior,
                "umbrella": _umbrella(c),
                "match_prefixes": list(c.prefixes),
            }
            for c in config.categories
        ],
    }


def summary_doc(run_id: str, functions: list[Classified], config: Config) -> dict:
    generated = sum(1 for f in functions if f.status == "generated")
    skipped = len(functions) - generated
    by_cat = Counter(f.category for f in functions if f.status == "skipped")
    per_crate: dict[str, Counter] = {}
    for f in functions:
        per_crate.setdefault(f.crate, Counter())[f.status] += 1
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "totals": {"candidates": len(functions), "generated": generated, "skipped": skipped},
        # Config order, every category present (zero counts included) so consumers
        # never have to guess whether a category is missing or empty.
        "by_category": [{"id": c.id, "count": by_cat.get(c.id, 0)} for c in config.categories],
        "by_crate": [
            {"crate": crate, "generated": c["generated"], "skipped": c["skipped"]}
            for crate, c in sorted(per_crate.items())
        ],
        "not_observable": {
            "kani_impl": "Kani omits KaniImpl skips from its listing tables, so they are not counted here."
        },
    }


def function_docs(run_id: str, functions: list[Classified]) -> tuple[dict, dict[str, dict]]:
    """Return (functions/index.json, {crate: functions/<crate>.json})."""
    by_crate: dict[str, list[Classified]] = {}
    for f in functions:
        by_crate.setdefault(f.crate, []).append(f)

    shards: dict[str, dict] = {}
    index_rows = []
    for crate in sorted(by_crate):
        rows = []
        for f in sorted(by_crate[crate], key=lambda f: f.function):
            rec: dict = {"name": f.function, "status": f.status}
            if f.status == "skipped":
                rec["category"] = f.category
                rec["detail"] = f.detail
                if f.args is not None:
                    rec["args"] = [{"name": n, "type": t} for n, t in f.args]
            rows.append(rec)
        shards[crate] = {"schema_version": SCHEMA_VERSION, "run_id": run_id, "crate": crate, "functions": rows}
        gen = sum(1 for r in rows if r["status"] == "generated")
        index_rows.append(
            {"crate": crate, "path": f"functions/{crate}.json", "generated": gen, "skipped": len(rows) - gen}
        )
    index = {"schema_version": SCHEMA_VERSION, "run_id": run_id, "crates": index_rows}
    return index, shards
