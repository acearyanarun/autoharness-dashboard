"""Adapter for per-function JSON: {"functions": [{"crate", "function", "status", "detail"?}]}.

This is the shape practicum published for the 2026-09-17 baseline
(fixtures/baseline-2026-09-17-x86_64/golden/). It is used to rebuild that baseline's dataset
while the original raw Kani stdout is unavailable. `detail` must be Kani's "Reason for
Skipping" text verbatim. Any `reason` or label field in the input is ignored: classification
is always redone from `detail` by this project's own rules.

It has no Kani header counts, so the listing header checks are reported as skipped.
Prefer kani-list-stdout-v1 whenever the raw listing exists.
"""

from __future__ import annotations

import json

from ..model import Listing, RawEntry

NAME = "per-function-json-v1"


class InputError(ValueError):
    pass


def parse(text: str) -> Listing:
    doc = json.loads(text)
    rows = doc.get("functions") if isinstance(doc, dict) else None
    if not isinstance(rows, list):
        raise InputError("per-function JSON must be an object with a 'functions' array")
    entries = []
    for i, r in enumerate(rows):
        where = f"functions[{i}]"
        if not isinstance(r, dict):
            raise InputError(f"{where} is not an object")
        crate, fn, status = r.get("crate"), r.get("function"), r.get("status")
        if not isinstance(crate, str) or not isinstance(fn, str):
            raise InputError(f"{where}: 'crate' and 'function' must be strings")
        if status == "generated":
            entries.append(RawEntry(crate, fn, "generated", None, None))
        elif status == "skipped":
            detail = r.get("detail")
            if not isinstance(detail, str):
                raise InputError(f"{where}: a skipped function needs Kani's reason text in 'detail'")
            entries.append(RawEntry(crate, fn, "skipped", detail, None))
        else:
            raise InputError(f"{where}: status must be 'generated' or 'skipped', got {status!r}")
    return Listing(entries=entries, declared_generated=None, declared_skipped=None,
                   adapter=NAME, has_kani_headers=False)
