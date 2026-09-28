"""Command line: `python -m autoharness_data build|verify ...`.

Exit codes: 0 = data written and validation passed; 1 = validation failed (data is still
written so it can be inspected, and manifest.json says status "fail"); 2 = usage or
input error (nothing trustworthy was produced).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from . import adapters, emit, pipeline, validate

REPO = Path(__file__).resolve().parents[2]


def _build(args) -> int:
    docs = pipeline.run_build(
        listing_path=args.listing,
        run_meta_path=args.run_meta,
        config_dir=args.config,
        kani_list_path=args.kani_list,
        expect=args.expect,
        adapter=args.adapter,
        schema_dir=args.schema_dir,
    )
    emit.write(args.out, docs)
    v = docs["validation.json"]
    t = docs["summary.json"]["totals"]
    print(f"wrote {args.out}: {t['candidates']} candidates, {t['generated']} generated, {t['skipped']} skipped")
    for c in v["checks"]:
        if c["status"] != "pass":
            print(f"  [{c['severity']}:{c['status']}] {c['id']}: {c['message']}")
    print(f"validation: {v['status']} ({v['counts']})")
    return 0 if v["status"] == "pass" else 1


def _verify(args) -> int:
    """Check a published data/ directory: hashes, schemas, and cross-file consistency."""
    root = Path(args.data)
    manifest = json.loads((root / "manifest.json").read_text())
    problems = []
    docs = {}
    for f in manifest["files"]:
        data = (root / f["path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != f["sha256"]:
            problems.append(f"{f['path']}: sha256 does not match manifest")
        docs[f["path"]] = json.loads(data)
    checks = validate.schema_checks({**docs, "manifest.json": manifest}, args.schema_dir)
    problems += [c.message for c in checks if c.status == "fail"]
    if manifest["status"] != "pass":
        problems.append(f"manifest status is {manifest['status']!r}")
    for p in problems:
        print(f"  {p}")
    print("verify: " + ("ok" if not problems else f"{len(problems)} problem(s)"))
    return 0 if not problems else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="autoharness-data")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="parse a Kani listing and write data/")
    b.add_argument("--listing", type=Path, required=True, help="Kani autoharness stdout (.txt or .gz)")
    b.add_argument("--run-meta", type=Path, required=True, help="run metadata TOML")
    b.add_argument("--kani-list", type=Path, help="kani-list.json from the same run (for the Kani version)")
    b.add_argument("--config", type=Path, default=REPO / "config")
    b.add_argument("--schema-dir", type=Path, default=REPO / "schema")
    b.add_argument("--expect", type=Path, help="golden expectations TOML to enforce")
    b.add_argument("--adapter", default=adapters.DEFAULT, choices=sorted(adapters.ADAPTERS))
    b.add_argument("--out", type=Path, required=True)
    b.set_defaults(func=_build)

    v = sub.add_parser("verify", help="check a published data/ directory")
    v.add_argument("--data", type=Path, required=True)
    v.add_argument("--schema-dir", type=Path, default=REPO / "schema")
    v.set_defaults(func=_verify)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
