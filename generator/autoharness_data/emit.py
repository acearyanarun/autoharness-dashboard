"""Deterministic serialization and the manifest. The only module that writes files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import SCHEMA_VERSION, __version__
from .build import CRATE_FILE_NAME
from . import resources
from .validate import schema_checks, schema_for


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


def write(out_dir: Path, docs: dict[str, dict], schema_dir: resources.Dir | None = None) -> dict[str, bytes]:
    """Serialize and write all documents plus manifest.json. Returns the written bytes.

    Every other document was schema-checked during assembly, and the result is recorded in
    validation.json. validation.json and manifest.json can't check themselves, so they are
    checked here before anything is written. If either fails, that is a generator bug: raise.
    """
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

    self_checks = schema_checks({"validation.json": docs["validation.json"], "manifest.json": manifest}, schema_dir)
    broken = [c.message for c in self_checks if c.status != "pass"]
    if broken:
        raise RuntimeError("internal error, refusing to write: " + "; ".join(broken))

    for path, data in blobs.items():
        target = out_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return blobs
