"""The ingestion pipeline: listing -> classify -> build -> validate -> documents."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from . import SCHEMA_VERSION, adapters, build, classify, config as config_mod, resources, runmeta, validate
from .model import Classified, Listing, Unclassified


def read_text(path: Path) -> str:
    raw = Path(path).read_bytes()
    if str(path).endswith(".gz"):
        raw = gzip.decompress(raw)
    return raw.decode("utf-8")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def kani_version_from_list(path: Path | None) -> str | None:
    if path is None:
        return None
    doc = json.loads(read_text(path))
    return doc.get("kani-version")


def assemble(
    *,
    listing: Listing | None,
    functions: list[Classified],
    unclassified: list[Unclassified],
    cfg: config_mod.Config,
    run: dict,
    expect: Path | None = None,
    schema_dir: resources.Dir | None = None,
) -> dict[str, dict]:
    """Build every document including validation.json (manifest is added by emit)."""
    run_id = run["run_id"]
    docs: dict[str, dict] = {
        "run.json": {"schema_version": SCHEMA_VERSION, **run},
        "categories.json": build.categories_doc(cfg),
        "summary.json": build.summary_doc(run_id, functions, cfg),
    }
    index, shards = build.function_docs(run_id, functions)
    docs["functions/index.json"] = index
    for crate, shard in shards.items():
        docs[f"functions/{crate}.json"] = shard

    checks = (
        validate.listing_checks(listing, functions)
        + validate.data_checks(functions, unclassified, docs)
        + validate.expectation_checks(expect, docs)
        + validate.schema_checks(docs, schema_dir)
    )
    docs["validation.json"] = validate.validation_doc(run_id, checks)
    return docs


def run_build(
    *,
    listing_path: Path,
    run_meta_path: Path,
    config_dir: resources.Dir | None = None,
    kani_list_path: Path | None = None,
    expect: Path | None = None,
    adapter: str = adapters.DEFAULT,
    schema_dir: resources.Dir | None = None,
) -> dict[str, dict]:
    # Fail before any work if schema validation would be impossible.
    resources.require_validator()
    cfg = config_mod.load(config_dir if config_dir is not None else resources.config_dir())
    meta = runmeta.load(run_meta_path)
    listing = adapters.ADAPTERS[adapter](read_text(listing_path))
    functions, unclassified = classify.classify(listing.entries, cfg)

    source_files = [{"role": "listing", "name": Path(listing_path).name, "sha256": _sha256_file(listing_path)}]
    if kani_list_path is not None:
        source_files.append(
            {"role": "kani_list", "name": Path(kani_list_path).name, "sha256": _sha256_file(kani_list_path)}
        )
    run = runmeta.build_run(meta, kani_version_from_list(kani_list_path), source_files, listing.adapter)
    return assemble(
        listing=listing, functions=functions, unclassified=unclassified, cfg=cfg, run=run,
        expect=expect, schema_dir=schema_dir,
    )
