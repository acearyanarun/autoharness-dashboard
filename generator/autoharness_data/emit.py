"""Deterministic serialization and the manifest. The only module that writes files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import SCHEMA_VERSION, __version__
from .build import CRATE_FILE_NAME
from .validate import schema_for


def serialize(path: str, doc: dict) -> bytes:
    # Function shards are large and machine-read: compact. Everything else: readable.
    if path.startswith("functions/") and path != "functions/index.json":
        text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(doc, ensure_ascii=False, indent=2)
    return (text + "\n").encode("utf-8")


def manifest_doc(run: dict, status: str, blobs: dict[str, bytes]) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "generator": {"name": "autoharness-data", "version": __version__},
        "run_id": run["run_id"],
        # Taken from the run, never from the wall clock, so rebuilds are byte-identical.
        "generated_at": run.get("finished_at"),
        "status": status,
        "files": [
            {
                "path": path,
                "schema": schema_for(path),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for path, data in sorted(blobs.items())
        ],
    }


def write(out_dir: Path, docs: dict[str, dict]) -> dict[str, bytes]:
    """Serialize and write all documents plus manifest.json. Returns the written bytes."""
    out_dir = Path(out_dir)
    blobs: dict[str, bytes] = {}
    for path, doc in docs.items():
        if path.startswith("functions/") and path != "functions/index.json":
            crate = path[len("functions/") : -len(".json")]
            if not CRATE_FILE_NAME.match(crate):
                raise ValueError(f"refusing to write unsafe crate file name {crate!r}")
        blobs[path] = serialize(path, doc)

    manifest = manifest_doc(docs["run.json"], docs["validation.json"]["status"], blobs)
    blobs["manifest.json"] = serialize("manifest.json", manifest)

    for path, data in blobs.items():
        target = out_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return blobs
